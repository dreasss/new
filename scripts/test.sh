#!/usr/bin/env bash
set -euo pipefail
(cd core-api && PYTHONPATH=. pytest -q tests/test_ticket_rules.py tests/test_sso_config.py tests/test_speaker.py tests/test_portal_flow.py)
(cd telephony-bot && PYTHONPATH=. pytest -q tests_fsm.py tests_providers.py)
