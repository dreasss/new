#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PATTERN='fake_wav|coming soon|return \[\]|sample wav'

MATCHES="$(rg -n -i \
  --glob '!**/.git/**' \
  --glob '!**/node_modules/**' \
  --glob '!**/package-lock.json' \
  --glob '!**/yarn.lock' \
  --glob '!**/pnpm-lock.yaml' \
  --glob '!**/*.lock' \
  --glob '!scripts/no_stubs_check.sh' \
  --glob '!scripts/no_stubs_allowlist.txt' \
  "$PATTERN" || true)"

if [[ -n "$MATCHES" ]]; then
  echo "FAIL: forbidden stub markers found:" >&2
  printf '%s\n' "$MATCHES" >&2
  exit 1
fi

echo "PASS: no forbidden stub markers found"
