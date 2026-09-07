#!/usr/bin/env bash
# Docker-based Playwright E2E runner for OrthoFlow.
#
# Runs the official Playwright image (browsers pre-installed) on the docker_agent-net
# network, targeting the live frontend container. This is the STANDARD way OrthoFlow runs
# automated frontend tests — it avoids host browser-launch issues and matches CI.
#
# Usage:
#   ./e2e/run-e2e.sh                    # run all specs
#   ./e2e/run-e2e.sh insurance-roster   # run specs matching a filter
set -euo pipefail

FILTER="${1:-}"
E2E_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NETWORK="docker_agent-net"
PW_IMAGE="mcr.microsoft.com/playwright:v1.45.0-jammy"

echo "▶ Running Playwright E2E via Docker (${PW_IMAGE}) on ${NETWORK}"
docker run --rm \
  --network "${NETWORK}" \
  -v "${E2E_DIR}:/e2e" \
  -w /e2e \
  -e E2E_BASE_URL="${E2E_BASE_URL:-http://orthoflow-frontend-1:3000}" \
  "${PW_IMAGE}" \
  sh -c "npm install --no-audit --no-fund >/dev/null 2>&1 && npx playwright test ${FILTER} --config=playwright.docker.config.ts"
