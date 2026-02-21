# Support Platform Monorepo

Состав:
- `core-api` (FastAPI + PostgreSQL + Alembic)
- `telephony-bot` (Asterisk ARI + FSM)
- `web-portal` (Next.js role-based portal)
- `infra` (Asterisk конфиги)

## 1) Запуск “одной командой”

```bash
cp .env.example .env
./scripts/up.sh
```

Миграции:

```bash
./scripts/migrate.sh
```

Seed demo-data:

```bash
cd core-api
PYTHONPATH=. python -m app.seed
```

Health checks:

```bash
curl http://localhost:8000/health
curl http://localhost:8010/health
curl http://localhost:3000
```

## 2) Настройка env

Ключевые параметры:
- DB/Redis: `POSTGRES_*`, `DATABASE_URL`, `REDIS_URL`
- Auth: `JWT_*`, `AUTH_LOCAL_DISABLED`
- SSO: `SSO_ENABLED`, `SSO_PROVIDER`, `OIDC_*`, `SAML_*`
- Telephony: `ASTERISK_ARI_*`, `ASTERISK_APP_NAME`
- Bot mode: `INTEGRATIONS_TEST_MODE`, `BOT_HANDOFF_ON_INCOMPLETE`
- Speech: `STT_PROVIDER`, `TTS_PROVIDER`, `SPEECHKIT_*`

## 3) Как включить SpeechKit

### Обязательные env

```bash
TTS_PROVIDER=speechkit
STT_PROVIDER=speechkit
SPEECHKIT_API_KEY=<ваш_api_key>
SPEECHKIT_FOLDER_ID=<ваш_folder_id>
BOT_SOUNDS_DIR=/shared/sounds/custom_tts
INTEGRATIONS_TEST_MODE=false
```

> Если `TTS_PROVIDER=speechkit` или `STT_PROVIDER=speechkit`, но отсутствуют `SPEECHKIT_API_KEY`/`SPEECHKIT_FOLDER_ID`, telephony-bot завершится ошибкой старта (без фейкового "успеха").

### Test-mode (честный)

```bash
TTS_PROVIDER=asterisk_assets
STT_PROVIDER=test_dtmf
INTEGRATIONS_TEST_MODE=true
```

- TTS: используются локальные WAV ассеты (`sound:custom_tts/...`) через Asterisk `/play`.
- STT: SpeechKit не имитируется; управление идёт через DTMF (или пустой STT-результат с последующим DTMF-flow).

### Проверка SpeechKit-mode

1. Поднять сервисы и сделать тестовый звонок:
```bash
./scripts/up.sh
curl -X POST http://localhost:8010/test-call
```
2. Проверить логи telephony-bot (без утечки секрета):
```bash
docker compose logs telephony-bot | rg "speechkit_(tts|stt)_request|tts_error|stt_error"
```
3. Убедиться, что создаются WAV в `BOT_SOUNDS_DIR` и в `call_logs` есть реальные `audio_path/audio_size_bytes`.

## 4) Как включить SSO (OIDC/SAML)

### OIDC (Keycloak/Entra)
- `SSO_ENABLED=true`
- `SSO_PROVIDER=OIDC`
- `OIDC_ISSUER`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_REDIRECT_URI`
- prod-рекомендация: `AUTH_LOCAL_DISABLED=true`

### SAML (ADFS/Entra SAML)
- `SSO_ENABLED=true`
- `SSO_PROVIDER=SAML`
- Либо metadata-mode: `SAML_METADATA_XML` + `SAML_SP_ENTITY_ID` + `SAML_ACS_URL`
- Либо manual-mode: `SAML_SP_ENTITY_ID`, `SAML_ACS_URL`, `SAML_IDP_ENTITY_ID`, `SAML_IDP_SSO_URL`, `SAML_IDP_X509CERT`

Проверка:
- `GET /api/v1/auth/sso/login`
- callback: `GET /api/v1/auth/sso/callback`

## 5) Как сделать тестовый SIP звонок

```bash
curl -X POST http://localhost:8010/test-call
```

В test-mode вводите DTMF и завершайте каждое поле символом `#`.
FSM: приветствие → ФИО → отдел → кабинет → проблема → доп.инфо → подтверждение.

Для реального trunk:
- добавить trunk endpoint/auth/aor в `infra/asterisk/pjsip.conf`
- inbound dialplan должен вызывать `Stasis(support_bot)` в `extensions.conf`.

### Записи аудио по шагам

- Bot пишет записи в `BOT_RECORDINGS_DIR` (по умолчанию `/shared/recordings`).
- Путь детерминирован по шаблону: `<BOT_RECORDINGS_DIR>/<call_id>/<step>/<timestamp>.wav`.
- На каждый `RecordingFinished` в `call_logs` пишутся `audio_path`, `audio_size_bytes`, `step`, `audio_valid`.
- Посмотреть записи в контейнере:

```bash
docker compose exec telephony-bot sh -lc 'find /shared/recordings -type f | sort | tail -n 30'
```

## 6) Портал (role-based)

- `/` Login: локальный JWT + SSO кнопка
- `/dashboard`:
  - user: мои заявки + создание
  - support/admin: очередь, фильтры, assign-self, смена статуса
  - admin: wizard секции `telephony/speechkit/sso/branding/phrases` с реальным сохранением в БД
- `/tickets/[id]`: детали, комментарии, закрытие, оценка после CLOSED

## 7) Примеры curl

Login:
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@example.com","password":"user12345"}'
```

Создать тикет:
```bash
curl -X POST http://localhost:8000/api/v1/tickets \
  -H 'Authorization: Bearer <TOKEN>' \
  -H 'Content-Type: application/json' \
  -d '{"subject":"Нет интернета","description":"Оборвалась связь","channel":"web"}'
```

Support queue:
```bash
curl -H 'Authorization: Bearer <SUPPORT_TOKEN>' \
  'http://localhost:8000/api/v1/support/tickets?status_filter=NEW&channel=web'
```

Admin wizard settings:
```bash
curl -X POST http://localhost:8000/api/v1/admin/settings/branding \
  -H 'Authorization: Bearer <ADMIN_TOKEN>' \
  -H 'Content-Type: application/json' \
  -d '{"config":{"title":"Support Portal","primaryColor":"#0f62fe"}}'
```

## 8) Чек-лист приёмки

- [ ] `docker compose up` поднимает postgres/redis/core-api/web-portal/asterisk/telephony-bot.
- [ ] `core-api /health` возвращает `db: 1`.
- [ ] Тестовый звонок создаёт запись в `call_logs` и тикет в БД.
- [ ] Созданный тикет виден в support dashboard (очередь).
- [ ] user видит только свои тикеты (`/api/v1/tickets`).
- [ ] Admin wizard сохраняет настройки и после перезагрузки выдаёт сохранённые значения.

## 9) Edge cases и обработка

- Тишина/непонятно: 2 попытки на обязательных шагах FSM, затем `INCOMPLETE` + handoff/завершение по `BOT_HANDOFF_ON_INCOMPLETE`.
- Низкая уверенность speaker-id: identify возвращает `user_id=null` / reason `no_match` или `phone_match_but_voice_low`.
- Нет consent: `consent_required=true`, enrollment запрещён без consent.
- Ошибка SpeechKit: при невалидных/отсутствующих ключах работа в test-mode без ложного "успеха" провайдера.
- Ошибка БД/API: endpoint возвращает ошибку, correlation_id сохраняется, события попадают в `call_logs` при доступности API.

## 10) Lint/Test

```bash
./scripts/lint.sh
./scripts/test.sh
```

## 11) CI E2E (GitHub Actions)

Workflow: `.github/workflows/e2e-compose.yml`.

Что запускается на каждый `push` и `pull_request`:

```bash
chmod +x scripts/*.sh
./scripts/lint.sh
./scripts/test.sh
./scripts/acceptance.sh
```

Что проверяет runtime (`scripts/acceptance.sh`):
- `docker compose up -d --build`
- `alembic upgrade head`
- `python -m app.seed`
- health-check сервисов (`core-api`, `telephony-bot`, `web-portal`)
- login support пользователя
- создание/проверка тикетов в support queue
- `POST /test-call` у `telephony-bot` и проверка появления `voice` тикета в БД

Где смотреть результат:
- GitHub → вкладка **Actions** → workflow **e2e-compose**.
- При падении workflow выводит:
  - `docker compose ps`
  - tail логов `core-api`, `telephony-bot`, `asterisk`
- Эти логи также публикуются как artifact: `compose-runtime-logs`.

## 12) Остановка

```bash
./scripts/down.sh
```
