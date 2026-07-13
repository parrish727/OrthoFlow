#!/bin/bash
set -e

# OrthoFlow — Manual Deploy with CAB-style Change Notification
# Usage: ./scripts/deploy.sh [service]
# Example: ./scripts/deploy.sh frontend
#          ./scripts/deploy.sh backend
#          ./scripts/deploy.sh (deploys all)

SERVICE="${1:-all}"
COMPOSE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SLACK_CHANNEL="${SLACK_CHANNEL_ID:-}"
SLACK_TOKEN="${SLACK_BOT_TOKEN:-}"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S %Z')
DEPLOYER=$(whoami)

# ── Slack Notification Function ───────────────────────────────────────────────
notify_slack() {
  local message="$1"
  if [ -n "$SLACK_TOKEN" ] && [ -n "$SLACK_CHANNEL" ]; then
    curl -sf -X POST "https://slack.com/api/chat.postMessage" \
      -H "Authorization: Bearer $SLACK_TOKEN" \
      -H "Content-Type: application/json" \
      -d "{\"channel\":\"$SLACK_CHANNEL\",\"text\":\"$message\",\"unfurl_links\":false}" > /dev/null 2>&1 || true
  fi
}

# ── Load env for Slack credentials ────────────────────────────────────────────
if [ -f "$COMPOSE_DIR/../../../Kiro/Projects/kiro-agents/.env" ]; then
  export $(grep -E "^SLACK_" "$COMPOSE_DIR/../../../Kiro/Projects/kiro-agents/.env" | xargs)
fi

echo "╔══════════════════════════════════════════════════════╗"
echo "║  OrthoFlow — Manual Deploy (CAB Change Window)      ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║  Service: $SERVICE"
echo "║  Time:    $TIMESTAMP"
echo "║  By:      $DEPLOYER"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── 1. Pre-Deploy Notification ────────────────────────────────────────────────
notify_slack "🟡 *CHANGE WINDOW OPEN* — OrthoFlow Manual Deploy\n*Service:* \`$SERVICE\`\n*Time:* $TIMESTAMP\n*Deployer:* $DEPLOYER\n*Status:* Maintenance in progress — brief interruption expected"

# Register with SRE (orchestrator tracks the window)
WINDOW_ID=$(curl -sf -X POST "http://localhost:9090/webhook/change-window/open" \
  -H "Content-Type: application/json" \
  -d "{\"service\":\"$SERVICE\",\"deployer\":\"$DEPLOYER\"}" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('window_id',-1))" 2>/dev/null || echo "-1")

echo "[1/5] Slack notified: change window #$WINDOW_ID open"

# ── 2. Pause Watchtower (prevent conflicts) ───────────────────────────────────
echo "[2/5] Pausing Watchtower..."
cd "$COMPOSE_DIR"
docker compose stop watchtower 2>/dev/null || true

# ── 3. Rebuild + Deploy ───────────────────────────────────────────────────────
echo "[3/5] Building and deploying: $SERVICE"
if [ "$SERVICE" = "all" ]; then
  docker compose up -d --build --force-recreate frontend backend worker
else
  docker compose up -d --build --force-recreate "$SERVICE"
fi

# ── 4. Health Check ───────────────────────────────────────────────────────────
echo "[4/5] Waiting for health check..."
sleep 8
HEALTH=$(curl -sf http://localhost:8000/health/deep 2>&1 || echo '{"status":"unhealthy"}')
if echo "$HEALTH" | grep -q "healthy"; then
  echo "  ✅ Backend healthy"
  STATUS="✅ SUCCESS"
else
  echo "  ❌ Backend unhealthy: $HEALTH"
  STATUS="❌ FAILED — manual review required"
fi

# ── 5. Resume Watchtower + Notify ─────────────────────────────────────────────
echo "[5/5] Resuming Watchtower..."
docker compose start watchtower 2>/dev/null || true

# Close the change window with SRE
curl -sf -X POST "http://localhost:9090/webhook/change-window/close" \
  -H "Content-Type: application/json" \
  -d "{\"window_id\":$WINDOW_ID,\"health_result\":\"$STATUS\",\"notes\":\"Service: $SERVICE\"}" 2>/dev/null || true

notify_slack "🟢 *CHANGE WINDOW CLOSED* — OrthoFlow Deploy Complete\n*Service:* \`$SERVICE\`\n*Result:* $STATUS\n*Health:* $(echo $HEALTH | grep -o '"status":"[^"]*"')"

echo ""
echo "Deploy complete: $STATUS"
