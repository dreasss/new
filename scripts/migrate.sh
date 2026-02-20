#!/usr/bin/env bash
set -euo pipefail
cd core-api
alembic upgrade head
