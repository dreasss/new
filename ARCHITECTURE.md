# Production-ready support system blueprint (SIP bot + Core API + Web portal + SSO + DB + queues)

## 1) Architecture

### 1.1 Fixed technology choices
- **Backend**: Python + FastAPI.
- **Database**: PostgreSQL 16.
- **Queues**: **Redis + RQ** (chosen over Celery for leaner operational footprint and simpler worker model for MVP while keeping clear job boundaries).
- **Telephony**: **Asterisk ARI** (chosen over AGI because ARI provides event-driven call control over HTTP/WebSocket and better fits asynchronous FSM orchestration).
- **Web**: Next.js (React + TypeScript).
- **SSO**: Unified auth provider interface with concrete OIDC and SAML adapters.

### 1.2 Services and responsibilities
1. **asterisk**
   - Terminates SIP calls.
   - Publishes call lifecycle events via ARI to core-api.
   - Streams/records audio according to configured dialplan.

2. **core-api (FastAPI)**
   - Single business entrypoint for bot flows, tickets, users, comments, ratings, auth, history.
   - Hosts bot FSM orchestrator (state transitions for call script).
   - Hosts adapters:
     - TelephonyAdapter (ARI implementation).
     - STT/TTS providers (external or local test-mode fallback).
     - SpeakerRecognizer provider.
     - SSO provider.
   - Persists domain entities to PostgreSQL.
   - Emits async jobs to Redis/RQ.

3. **worker (RQ worker)**
   - Executes long-running jobs:
     - Audio post-processing.
     - STT transcription requests.
     - TTS synthesis cache prebuild.
     - Speaker embedding/enrollment and matching.
     - Notification delivery.

4. **postgres**
   - Source of truth for users, tickets, comments, call sessions, transcripts, speaker profiles, consent, ratings, audit trails.

5. **redis**
   - Queue broker for RQ.
   - Optional short-lived cache for call-session hot state (authoritative state still persisted in PostgreSQL).

6. **web-portal (Next.js)**
   - Agent portal: ticket list/detail, history, comments, rating review.
   - Auth via SSO (OIDC/SAML adapter through core-api).
   - No dead UI elements: all actions call real API and persist results.

### 1.3 End-to-end data flow (call → STT → FSM → TTS → ticket → portal)
1. **Incoming SIP call** arrives to Asterisk.
2. Asterisk notifies core-api via ARI webhook/event stream: `call.started`.
3. Core-api creates `call_session` with `correlation_id` and initial FSM state (`GREETING`).
4. Bot prompts caller:
   - In production: TTS provider synthesizes phrase.
   - In test-mode: local deterministic audio assets are selected by phrase key.
5. Caller utterance is captured and sent to STT:
   - Production: external STT provider.
   - Test-mode: local recognizer pipeline (e.g., Vosk/Whisper local model) with explicit `provider=test_local` marker in logs.
6. FSM consumes recognized intent/entities (e.g., full name, account id, issue summary, urgency).
7. Once required fields are collected and validated, core-api creates `ticket` + initial `comment` in PostgreSQL.
8. Bot confirms ticket number to caller via TTS/local-audio.
9. Core-api emits async jobs (e.g., enrichment, notification) to RQ.
10. Web portal fetches `/tickets` and immediately shows created ticket with history trail.
11. Agent can add comments/update status; changes are persisted and visible in history.

### 1.4 Honest test-mode (without fabricated success)
- Test-mode is **feature-flagged** and only for integrations requiring external credentials.
- Allowed local replacements:
  - STT: local on-box recognizer.
  - TTS: pre-generated local wav assets by phrase key.
  - SSO: local OIDC provider container (e.g., Keycloak) instead of bypass login.
- If provider call fails, API returns explicit failure and records integration error; no silent “success”.

---

## 2) Core API contracts

### 2.1 REST endpoints table

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/auth/login` | Public | Username/password login for local admin bootstrap (disabled when `AUTH_LOCAL_DISABLED=true`). |
| GET | `/api/v1/auth/me` | Bearer | Returns current user profile/roles/tenant. |
| POST | `/api/v1/auth/refresh` | Refresh token | Rotates access token. |
| GET | `/api/v1/auth/sso/providers` | Public | Lists enabled SSO providers and metadata needed for redirect. |
| GET | `/api/v1/auth/sso/{provider}/start` | Public | Starts OIDC/SAML flow, returns redirect URL/state. |
| GET | `/api/v1/auth/sso/{provider}/callback` | Public | Handles IdP callback, validates assertion/token, creates session. |
| POST | `/api/v1/auth/logout` | Bearer | Revokes session/token. |
| GET | `/api/v1/users` | Bearer (agent/admin) | Paginated users query with filters (role/status). |
| POST | `/api/v1/users` | Bearer (admin) | Creates user in local directory or links external identity. |
| GET | `/api/v1/users/{user_id}` | Bearer | User detail. |
| PATCH | `/api/v1/users/{user_id}` | Bearer (admin) | Updates profile/roles/status. |
| GET | `/api/v1/tickets` | Bearer (agent/admin) | List tickets by status/priority/date/assignee/caller. |
| POST | `/api/v1/tickets` | Bearer or Service | Creates ticket (bot/service/agent). Persists mandatory fields. |
| GET | `/api/v1/tickets/{ticket_id}` | Bearer | Ticket detail with latest state. |
| PATCH | `/api/v1/tickets/{ticket_id}` | Bearer (agent/admin) | Updates status/priority/assignee/resolution fields. |
| POST | `/api/v1/tickets/{ticket_id}/comments` | Bearer | Adds comment linked to actor and timestamp. |
| GET | `/api/v1/tickets/{ticket_id}/comments` | Bearer | Returns ordered comment thread. |
| GET | `/api/v1/history/tickets/{ticket_id}` | Bearer | Full immutable audit history for ticket lifecycle changes. |
| GET | `/api/v1/history/calls/{call_id}` | Bearer (agent/admin) | Call events timeline + transcript references + bot decisions. |
| POST | `/api/v1/ratings` | Bearer or Service | Creates post-call rating (1-5 + optional feedback). |
| GET | `/api/v1/ratings/{ticket_id}` | Bearer | Fetches rating tied to ticket/call. |
| POST | `/api/v1/bot/calls/incoming` | Service (Asterisk) | ARI event ingress to start/continue call FSM. |
| POST | `/api/v1/bot/calls/{call_id}/events` | Service | Receives telephony events (DTMF, hangup, playback finished). |
| POST | `/api/v1/bot/calls/{call_id}/utterances` | Service | Submits recognized utterance chunk for FSM transition. |
| GET | `/api/v1/bot/calls/{call_id}` | Bearer (agent/admin) | Returns current call session state and collected slots. |
| POST | `/api/v1/speaker-id/enroll` | Bearer or Service | Enrolls speaker voiceprint after explicit consent. |
| POST | `/api/v1/speaker-id/verify` | Service | Verifies caller voice against enrolled profile; returns score/decision. |
| GET | `/api/v1/speaker-id/profiles/{profile_id}` | Bearer (agent/admin) | Returns profile metadata and consent status (no raw biometric export). |
| DELETE | `/api/v1/speaker-id/profiles/{profile_id}` | Bearer (admin) | Deletes profile and linked embeddings per retention policy. |

### 2.2 Domain notes (critical behavior)
- Each write endpoint stores an audit record (`who`, `when`, `before`, `after`, `correlation_id`).
- `bot` endpoints are authenticated by service credentials/JWT audience distinct from user tokens.
- Ticket creation requires non-empty `subject`, `channel`, `requester_contact`, `description`; validation failure returns 422 with field errors.

---

## 3) Interface definitions (pseudocode signatures)

```python
from typing import Protocol, Iterable, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class TelephonyCallContext:
    call_id: str
    channel_id: str
    from_number: str
    to_number: str
    started_at: datetime
    correlation_id: str

@dataclass
class PlaybackHandle:
    playback_id: str
    call_id: str

class TelephonyAdapter(Protocol):
    async def answer_call(self, ctx: TelephonyCallContext) -> None: ...
    async def hangup_call(self, call_id: str, reason: str) -> None: ...
    async def play_audio(self, call_id: str, audio_uri: str, interruptible: bool) -> PlaybackHandle: ...
    async def stop_playback(self, playback_id: str) -> None: ...
    async def start_recording(self, call_id: str, max_seconds: int) -> str: ...  # returns recording_id
    async def stop_recording(self, recording_id: str) -> str: ...  # returns file_uri
    async def collect_dtmf(self, call_id: str, digits: int, timeout_ms: int) -> str: ...
    async def subscribe_events(self) -> Iterable[dict]: ...
    async def transfer_call(self, call_id: str, target_extension: str) -> None: ...

@dataclass
class SpeakerSample:
    audio_uri: str
    codec: str
    sample_rate_hz: int
    duration_ms: int

@dataclass
class VerificationResult:
    matched: bool
    score: float
    threshold: float
    reason: str

class SpeakerRecognizer(Protocol):
    async def enroll(self, user_id: str, sample: SpeakerSample, consent_id: str) -> str: ...  # profile_id
    async def verify(self, profile_id: str, sample: SpeakerSample) -> VerificationResult: ...
    async def delete_profile(self, profile_id: str) -> None: ...
    async def healthcheck(self) -> dict: ...
```

---

## 4) Runnable MVP vertical slice

### 4.1 Scope (must run end-to-end)
- Incoming call via Asterisk ARI.
- Bot collects: caller name, contact number, issue summary.
- Core-api validates collected fields and creates ticket in PostgreSQL.
- Portal shows ticket in list and ticket detail page.

### 4.2 MVP components
- `docker-compose` services: `asterisk`, `core-api`, `worker`, `postgres`, `redis`, `web-portal`, optional `keycloak` for local OIDC test-mode.
- DB migrations define tables: `users`, `tickets`, `ticket_comments`, `call_sessions`, `call_events`, `transcripts`, `ratings`, `speaker_profiles`, `consents`, `audit_log`.
- Core API exposes endpoints listed above with real persistence and auth checks.
- Bot FSM states for MVP:
  1. `GREETING`
  2. `COLLECT_NAME`
  3. `COLLECT_CONTACT`
  4. `COLLECT_ISSUE`
  5. `CONFIRM`
  6. `CREATE_TICKET`
  7. `END_CALL`
- On `CREATE_TICKET`, transaction writes `ticket` + first `comment` + `history` atomically.

### 4.3 Acceptance checks (no placeholder handlers)
1. Place SIP call → bot greeting is played.
2. Provide required data via speech/DTMF fallback.
3. Ticket row appears in PostgreSQL with non-null required fields.
4. `/api/v1/tickets` returns new ticket for authenticated agent.
5. Portal ticket list shows same ticket id/status.
6. Changing status in portal updates DB and audit trail.

---

## 5) Environment variables and configuration

### 5.1 Core mandatory `.env`
- `APP_ENV=local|staging|prod`
- `APP_HOST=0.0.0.0`
- `APP_PORT=8000`
- `DATABASE_URL=postgresql+psycopg://support:support@postgres:5432/support`
- `REDIS_URL=redis://redis:6379/0`
- `RQ_DEFAULT_QUEUE=support-default`
- `JWT_PRIVATE_KEY_PATH=/run/secrets/jwt_private.pem`
- `JWT_PUBLIC_KEY_PATH=/run/secrets/jwt_public.pem`
- `JWT_ISSUER=support-core`
- `JWT_AUDIENCE=support-web`
- `SERVICE_JWT_AUDIENCE=support-bot`
- `API_CORS_ORIGINS=http://localhost:3000`

### 5.2 Telephony / bot
- `TELEPHONY_PROVIDER=asterisk_ari`
- `ASTERISK_ARI_BASE_URL=http://asterisk:8088/ari`
- `ASTERISK_ARI_USERNAME=ari_user`
- `ASTERISK_ARI_PASSWORD=...`
- `ASTERISK_APP_NAME=support_bot`
- `BOT_LANGUAGE=ru-RU`
- `BOT_MAX_RETRIES_PER_SLOT=2`
- `BOT_RECORDINGS_DIR=/var/lib/support/recordings`

### 5.3 STT/TTS and test-mode flags
- `STT_PROVIDER=speechkit|local`
- `STT_SPEECHKIT_API_KEY=...` (required when provider is `speechkit`)
- `TTS_PROVIDER=speechkit|local_assets`
- `TTS_SPEECHKIT_API_KEY=...` (required when provider is `speechkit`)
- `LOCAL_TTS_ASSETS_DIR=/opt/app/audio/ru`
- `INTEGRATIONS_TEST_MODE=false|true`

Rules:
- If `INTEGRATIONS_TEST_MODE=true`, only providers marked as local are allowed unless explicit credentials are present.
- If external provider selected without required keys, startup fails fast with configuration error.

### 5.4 SSO
- `SSO_ENABLED=true`
- `SSO_DEFAULT_PROVIDER=oidc_main`
- `OIDC_MAIN_ISSUER_URL=http://keycloak:8080/realms/support`
- `OIDC_MAIN_CLIENT_ID=support-web`
- `OIDC_MAIN_CLIENT_SECRET=...`
- `OIDC_MAIN_SCOPES=openid,profile,email`
- `SAML_CORP_IDP_METADATA_URL=https://idp.example.com/metadata`
- `SAML_CORP_SP_ENTITY_ID=support-portal`
- `SAML_CORP_SP_ACS_URL=https://portal.example.com/api/auth/saml/callback`

### 5.5 Speaker ID / consent
- `SPEAKER_ID_PROVIDER=local|vendor_x`
- `SPEAKER_ID_THRESHOLD=0.78`
- `VOICE_BIOMETRY_RETENTION_DAYS=365`
- `VOICE_BIOMETRY_ENCRYPTION_KEY=...`

---

## 6) Logging, correlation, and voice-id consent policies

### 6.1 Logging and tracing
- Generate `correlation_id` at first ingress:
  - SIP call start (from ARI event), or
  - HTTP request from portal/API client.
- Propagate `correlation_id` through:
  - HTTP headers (`X-Correlation-ID`),
  - queue job metadata,
  - DB audit rows,
  - telephony event logs.
- Structured JSON logs mandatory fields:
  - `timestamp`, `level`, `service`, `env`, `correlation_id`, `actor_type`, `actor_id`, `event`, `entity_type`, `entity_id`, `result`, `error_code`.
- No sensitive payload in logs (raw audio, auth secrets, full biometric vectors).

### 6.2 Consent policy for speaker identification
- Voice-ID enrollment is **opt-in only**:
  - explicit consent captured (DTMF “1” or authenticated portal action),
  - consent record stored with versioned policy text hash and timestamp.
- Verification without consent is forbidden and must return business error.
- Provide revocation endpoint/process:
  - deleting profile removes embeddings and future verification eligibility.
- Retention enforcement:
  - periodic worker job purges expired voice biometrics and logs deletion audit.

---

## 7) Risks and mitigation via adapters

1. **Vendor lock-in (STT/TTS/SSO/Speaker ID)**
   - Mitigation: strict provider interfaces + config-based adapter selection.

2. **Telephony event ordering/race conditions**
   - Mitigation: ARI event idempotency keys, per-call FSM versioning, optimistic locking.

3. **Speech recognition quality variance**
   - Mitigation: slot confirmation prompts, DTMF fallback, retry budget, transfer-to-agent path.

4. **Biometric compliance risk**
   - Mitigation: explicit consent ledger, encryption at rest, retention and deletion workflows.

5. **Queue backlog impacting latency**
   - Mitigation: isolate real-time call-critical path from async enrichment, queue metrics/alerts.

6. **SSO provider downtime**
   - Mitigation: multi-provider strategy via adapter registry; local admin break-glass account controlled by policy.

---

## 8) Report: done vs next

### Done in this deliverable
- Fixed stack decisions and rationale (FastAPI/PostgreSQL/Redis+RQ/Asterisk ARI/Next.js/SSO adapters).
- Defined full target architecture and end-to-end call-to-ticket data flow.
- Specified concrete REST contracts for core domains and bot/speaker-id paths.
- Defined TelephonyAdapter and SpeakerRecognizer interfaces.
- Defined runnable MVP vertical slice with objective acceptance checks.
- Defined `.env` and config policy including honest test-mode behavior.
- Defined correlation logging and voice-id consent governance.

### Next implementation steps
1. Scaffold monorepo services and docker-compose with all runtime dependencies.
2. Implement DB schema + migrations + audit triggers/services.
3. Implement ARI adapter and MVP FSM states with transactional ticket creation.
4. Implement portal pages wired to real auth and ticket APIs.
5. Add integration tests:
   - call event ingestion,
   - ticket creation transaction,
   - SSO login,
   - speaker consent and verification guardrails.
