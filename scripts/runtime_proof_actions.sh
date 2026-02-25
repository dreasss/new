#!/usr/bin/env bash
set -euo pipefail
set -x

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

TOKEN="${GH_TOKEN:-${GITHUB_API_TOKEN:-}}"
if [[ -z "$TOKEN" ]]; then
  echo "RUNTIME=FAIL (not proven): set GH_TOKEN or GITHUB_API_TOKEN for GitHub Actions API access" >&2
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "RUNTIME=FAIL (not proven): curl is required" >&2
  exit 1
fi
if ! command -v python >/dev/null 2>&1; then
  echo "RUNTIME=FAIL (not proven): python is required" >&2
  exit 1
fi
if ! command -v unzip >/dev/null 2>&1; then
  echo "RUNTIME=FAIL (not proven): unzip is required" >&2
  exit 1
fi

ORIGIN_URL="$(git remote get-url origin 2>/dev/null || true)"
if [[ -z "$ORIGIN_URL" ]]; then
  echo "RUNTIME=FAIL (not proven): origin remote not found" >&2
  exit 1
fi

REPO_SLUG="$(python - "$ORIGIN_URL" <<'PY'
import re
import sys
url = sys.argv[1].strip()
slug = ""
if url.startswith("git@github.com:"):
    slug = url.split(":", 1)[1]
elif "github.com/" in url:
    slug = url.split("github.com/", 1)[1]
if slug.endswith(".git"):
    slug = slug[:-4]
slug = slug.strip("/")
if not re.match(r"^[^/]+/[^/]+$", slug):
    sys.exit(1)
print(slug)
PY
)"

API_BASE="https://api.github.com/repos/${REPO_SLUG}"
AUTH_HEADER="Authorization: Bearer ${TOKEN}"
ACCEPT_HEADER="Accept: application/vnd.github+json"

api_get() {
  local url="$1"
  curl -fsSL -H "$AUTH_HEADER" -H "$ACCEPT_HEADER" "$url"
}

WORKFLOWS_JSON="$(api_get "${API_BASE}/actions/workflows?per_page=100")"
WORKFLOW_ID="$(printf '%s' "$WORKFLOWS_JSON" | python - <<'PY'
import json
import sys
obj = json.load(sys.stdin)
for wf in obj.get("workflows", []):
    if wf.get("path") == ".github/workflows/e2e-compose.yml" or wf.get("name") == "e2e-compose":
        print(wf["id"])
        raise SystemExit(0)
raise SystemExit(1)
PY
)"

CURRENT_BRANCH="$(git branch --show-current)"
RUNS_BRANCH_JSON="$(api_get "${API_BASE}/actions/workflows/${WORKFLOW_ID}/runs?status=completed&branch=${CURRENT_BRANCH}&per_page=20")"
RUN_ID="$(printf '%s' "$RUNS_BRANCH_JSON" | python - <<'PY'
import json
import sys
obj = json.load(sys.stdin)
runs = obj.get("workflow_runs", [])
if runs:
    print(runs[0]["id"])
PY
)"

if [[ -z "$RUN_ID" ]]; then
  RUNS_JSON="$(api_get "${API_BASE}/actions/workflows/${WORKFLOW_ID}/runs?status=completed&per_page=20")"
  RUN_ID="$(printf '%s' "$RUNS_JSON" | python - <<'PY'
import json
import sys
obj = json.load(sys.stdin)
runs = obj.get("workflow_runs", [])
if runs:
    print(runs[0]["id"])
PY
)"
fi

if [[ -z "$RUN_ID" ]]; then
  echo "RUNTIME=FAIL (not proven): no completed workflow runs found for e2e-compose" >&2
  exit 1
fi

RUN_JSON="$(api_get "${API_BASE}/actions/runs/${RUN_ID}")"
RUN_CONCLUSION="$(printf '%s' "$RUN_JSON" | python - <<'PY'
import json
import sys
obj = json.load(sys.stdin)
print(obj.get("conclusion", ""))
PY
)"
RUN_URL="$(printf '%s' "$RUN_JSON" | python - <<'PY'
import json
import sys
obj = json.load(sys.stdin)
print(obj.get("html_url", ""))
PY
)"

if [[ "$RUN_CONCLUSION" != "success" ]]; then
  echo "RUNTIME=FAIL (not proven): run_id=${RUN_ID} conclusion=${RUN_CONCLUSION} url=${RUN_URL}" >&2
  exit 1
fi

echo "runtime proof run_id=${RUN_ID} conclusion=${RUN_CONCLUSION} url=${RUN_URL}"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

LOGS_ZIP="${TMP_DIR}/run-logs.zip"
curl -fsSL -H "$AUTH_HEADER" -H "$ACCEPT_HEADER" -L "${API_BASE}/actions/runs/${RUN_ID}/logs" -o "$LOGS_ZIP"

LOGS_DIR="${TMP_DIR}/run-logs"
mkdir -p "$LOGS_DIR"
unzip -q "$LOGS_ZIP" -d "$LOGS_DIR"

while IFS= read -r file; do
  echo "===== BEGIN RUN LOG: ${file} ====="
  cat "$file"
  echo "===== END RUN LOG: ${file} ====="
done < <(find "$LOGS_DIR" -type f | sort)

ARTIFACTS_JSON="$(api_get "${API_BASE}/actions/runs/${RUN_ID}/artifacts?per_page=100")"
ARTIFACT_ID="$(printf '%s' "$ARTIFACTS_JSON" | python - <<'PY'
import json
import sys
obj = json.load(sys.stdin)
for art in obj.get("artifacts", []):
    if art.get("name") == "compose-runtime-logs":
        print(art["id"])
        raise SystemExit(0)
print("")
PY
)"

if [[ -z "$ARTIFACT_ID" ]]; then
  echo "artifact not found: compose-runtime-logs"
else
  ART_ZIP="${TMP_DIR}/compose-runtime-logs.zip"
  curl -fsSL -H "$AUTH_HEADER" -H "$ACCEPT_HEADER" -L "${API_BASE}/actions/artifacts/${ARTIFACT_ID}/zip" -o "$ART_ZIP"
  ART_DIR="${TMP_DIR}/compose-runtime-logs"
  mkdir -p "$ART_DIR"
  unzip -q "$ART_ZIP" -d "$ART_DIR"
  while IFS= read -r file; do
    echo "===== BEGIN ARTIFACT LOG: ${file} ====="
    cat "$file"
    echo "===== END ARTIFACT LOG: ${file} ====="
  done < <(find "$ART_DIR" -type f -name '*.log' | sort)
fi

echo "RUNTIME=PASS (proven by GitHub Actions logs)"
