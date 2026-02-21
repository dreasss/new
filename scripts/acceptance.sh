#!/usr/bin/env bash
set -euo pipefail
set -x

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

LOG_TAIL_LINES="${ACCEPTANCE_LOG_TAIL_LINES:-120}"
POLL_ATTEMPTS="${ACCEPTANCE_POLL_ATTEMPTS:-60}"
POLL_SLEEP_SECONDS="${ACCEPTANCE_POLL_SLEEP_SECONDS:-2}"

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

read_env_var() {
  local key="$1"
  local default_value="$2"
  local value=""

  if value=$(grep -E "^${key}=" .env | tail -n1 | cut -d'=' -f2-); then
    :
  else
    value=""
  fi

  if [[ -z "$value" ]]; then
    echo "$default_value"
  else
    echo "$value"
  fi
}

POSTGRES_USER="$(read_env_var POSTGRES_USER support)"
POSTGRES_DB="$(read_env_var POSTGRES_DB support)"

step() {
  echo
  echo "==> $*"
}

run() {
  echo "+ $*"
  "$@"
}

run_capture() {
  echo "+ $*" >&2
  local out
  out="$({ "$@"; } 2>&1 | tee /dev/stderr)"
  printf '%s' "$out"
}

print_logs_on_fail() {
  echo
  echo "[acceptance] FAILED"
  if command -v docker >/dev/null 2>&1; then
    echo "[acceptance] docker compose ps"
    docker compose ps || true
    echo "[acceptance] last ${LOG_TAIL_LINES} lines: core-api telephony-bot asterisk postgres redis web-portal"
    docker compose logs --tail "$LOG_TAIL_LINES" core-api telephony-bot asterisk postgres redis web-portal || true
  else
    echo "[acceptance] docker is not available; logs are unavailable"
  fi
}

cleanup() {
  if command -v docker >/dev/null 2>&1; then
    echo "+ docker compose down -v"
    docker compose down -v || true
  fi
}

on_exit() {
  local code=$?
  if [[ $code -ne 0 ]]; then
    print_logs_on_fail || true
  fi
  cleanup
  exit $code
}

trap on_exit EXIT

step "Sanity checks"
# codex/define-architecture-for-support-system-j19u82
=======
if ! command -v docker >/dev/null 2>&1; then
  echo "docker binary is required for runtime acceptance" >&2
  exit 127
fi
# main
if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required for runtime acceptance" >&2
  exit 127
fi

# codex/define-architecture-for-support-system-j19u82
if ! command -v docker >/dev/null 2>&1; then
  step "Docker is unavailable; proving runtime via GitHub Actions"
  run ./scripts/runtime_proof_actions.sh
  exit 0
fi

# main
step "Bring up compose stack"
run docker compose up -d --build

wait_http_ok() {
  local name="$1"
  local url="$2"
  local attempt=1

  while (( attempt <= POLL_ATTEMPTS )); do
    if body=$(curl -fsS "$url" 2>/dev/null); then
      echo "[health] service=${name} attempt=${attempt}/${POLL_ATTEMPTS} body=${body}"
      return 0
    fi
    echo "[health] service=${name} attempt=${attempt}/${POLL_ATTEMPTS} body=unavailable"
    sleep "$POLL_SLEEP_SECONDS"
    ((attempt++))
  done

  echo "service ${name} did not become healthy in time via ${url}" >&2
  return 1
}

wait_web_ok() {
  local attempt=1

  while (( attempt <= POLL_ATTEMPTS )); do
    if status=$(curl -fsS -o /dev/null -w "%{http_code}" http://localhost:3000); then
      echo "[health] service=web-portal attempt=${attempt}/${POLL_ATTEMPTS} status=${status}"
      if [[ "$status" == "200" || "$status" == "302" || "$status" == "307" ]]; then
        return 0
      fi
    else
      echo "[health] service=web-portal attempt=${attempt}/${POLL_ATTEMPTS} status=unavailable"
    fi
    sleep "$POLL_SLEEP_SECONDS"
    ((attempt++))
  done

  echo "service web-portal did not become ready in time" >&2
  return 1
}

wait_postgres_ready() {
  local attempt=1

  while (( attempt <= POLL_ATTEMPTS )); do
    if out=$(docker compose exec -T postgres pg_isready -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" 2>&1); then
      echo "[health] service=postgres attempt=${attempt}/${POLL_ATTEMPTS} pg_isready=${out}"
      if [[ "$out" == *"accepting connections"* ]]; then
        return 0
      fi
    else
      echo "[health] service=postgres attempt=${attempt}/${POLL_ATTEMPTS} pg_isready=unavailable"
    fi
    sleep "$POLL_SLEEP_SECONDS"
    ((attempt++))
  done

  echo "postgres did not become ready in time" >&2
  return 1
}

step "Wait for service health"
wait_postgres_ready
wait_http_ok core-api http://localhost:8000/health
wait_http_ok telephony-bot http://localhost:8010/health
wait_web_ok

step "Apply migrations and seed data"
run docker compose exec -T core-api alembic upgrade head
run docker compose exec -T core-api python -m app.seed

step "Check health endpoints"
CORE_HEALTH="$(run_capture curl -fsS http://localhost:8000/health)"
BOT_HEALTH="$(run_capture curl -fsS http://localhost:8010/health)"
WEB_HEALTH_CODE="$(run_capture curl -fsS -o /dev/null -w "%{http_code}" http://localhost:3000)"
echo "core-api /health => ${CORE_HEALTH}"
echo "telephony-bot /health => ${BOT_HEALTH}"
echo "web-portal HTTP code => ${WEB_HEALTH_CODE}"

step "Run telephony test call"
BASELINE_COUNT="$(run_capture docker compose exec -T postgres psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -tAc "SELECT COUNT(*) FROM tickets WHERE channel='voice';" | tr -d '[:space:]')"
TEST_CALL_RESPONSE="$(run_capture curl -fsS -X POST http://localhost:8010/test-call)"
echo "baseline voice ticket count => ${BASELINE_COUNT}"
echo "telephony /test-call => ${TEST_CALL_RESPONSE}"

step "Wait for voice ticket in database (polling)"
LATEST_VOICE_TICKET_ID=""
for ((i = 1; i <= POLL_ATTEMPTS; i++)); do
  CURRENT_COUNT="$(run_capture docker compose exec -T postgres psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -tAc "SELECT COUNT(*) FROM tickets WHERE channel='voice';" | tr -d '[:space:]')"
  LATEST_VOICE_TICKET_ID="$(run_capture docker compose exec -T postgres psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -tAc "SELECT COALESCE(MAX(id),0) FROM tickets WHERE channel='voice';" | tr -d '[:space:]')"

  echo "[ticket-poll] attempt=${i}/${POLL_ATTEMPTS} count=${CURRENT_COUNT} latest_voice_ticket_id=${LATEST_VOICE_TICKET_ID}"

  if (( CURRENT_COUNT > BASELINE_COUNT )); then
    break
  fi

  if (( i == POLL_ATTEMPTS )); then
    echo "voice ticket was not created within timeout" >&2
    exit 1
  fi
  sleep "$POLL_SLEEP_SECONDS"
done

step "Login support and verify queue contains telephony ticket"
SUPPORT_LOGIN_RESPONSE="$(run_capture curl -fsS -X POST http://localhost:8000/api/v1/auth/login -H 'Content-Type: application/json' -d '{"email":"support@example.com","password":"support123"}')"
SUPPORT_TOKEN="$(printf '%s' "$SUPPORT_LOGIN_RESPONSE" | python -c 'import json,sys;print(json.load(sys.stdin)["access_token"])')"
echo "support login => ${SUPPORT_LOGIN_RESPONSE}"

QUEUE_RESPONSE="$(run_capture curl -fsS "http://localhost:8000/api/v1/support/tickets?channel=voice" -H "Authorization: Bearer ${SUPPORT_TOKEN}")"
echo "support queue (channel=voice) => ${QUEUE_RESPONSE}"

printf '%s' "$QUEUE_RESPONSE" | python -c 'import json,sys;ticket_id=int(sys.argv[1]);items=json.load(sys.stdin).get("items",[]);assert any(int(i.get("id",-1))==ticket_id for i in items),f"ticket id {ticket_id} not found in support queue";print(f"verified: ticket id {ticket_id} found in support queue")' "$LATEST_VOICE_TICKET_ID"

step "Runtime acceptance passed"
echo "ACCEPTANCE_OK"
