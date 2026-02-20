#!/usr/bin/env bash
set -euo pipefail
ruff check core-api telephony-bot
black --check core-api telephony-bot
(cd core-api && mypy app)
(cd telephony-bot && mypy app)
cd web-portal
npm run lint
