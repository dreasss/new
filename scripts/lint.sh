#!/usr/bin/env bash
set -euo pipefail
# codex/define-architecture-for-support-system-e3u2rv
./scripts/no_stubs_check.sh

# main
ruff check core-api telephony-bot
black --check core-api telephony-bot
(cd core-api && mypy app)
(cd telephony-bot && mypy app)
cd web-portal
npm run lint
