#!/usr/bin/env bash
# Deploy merged `main` to the Recover runtime on hermes-vcn-0.
#
# Run from any host after a PR merges. It never edits the host's clone by hand:
# it refuses a dirty tree, fast-forwards `main`, installs, runs the suite,
# restarts the user service, and requires a healthy /health response.
#
#   bash scripts/deploy.sh                 # deploy origin/main
#   TEXT_BACK_DEPLOY_HOST=user@host bash scripts/deploy.sh
set -euo pipefail

HOST="${TEXT_BACK_DEPLOY_HOST:-ubuntu@100.124.192.46}"
KEY="${TEXT_BACK_DEPLOY_KEY:-$HOME/.ssh/oracle}"
SSH_OPTS=(-o BatchMode=yes -o ConnectTimeout=15)
[[ -f "$KEY" ]] && SSH_OPTS+=(-i "$KEY")

ssh "${SSH_OPTS[@]}" "$HOST" 'bash -s' <<'REMOTE'
set -euo pipefail
cd "$HOME/projects/text_back"
if [[ -n "$(git status --porcelain)" ]]; then
  echo "DEPLOY REFUSED: hermes-cloud checkout has uncommitted changes:" >&2
  git status --short >&2
  exit 3
fi
git fetch --quiet origin main
git switch --quiet main 2>/dev/null || git switch --quiet -c main --track origin/main
git merge --ff-only --quiet origin/main
.venv/bin/pip install --quiet -e '.[dev]'
.venv/bin/python -m pytest -q -p no:cacheprovider | tail -1
if ! cmp -s deploy/systemd/text-back.service "$HOME/.config/systemd/user/text-back.service"; then
  echo "unit template differs from the installed unit; leaving the installed unit unchanged" >&2
fi
systemctl --user restart text-back.service
for _ in $(seq 1 30); do
  if health="$(curl -fsS -m 5 http://127.0.0.1:8000/health 2>/dev/null)"; then break; fi
  sleep 1
done
sleep 6  # let the lifespan worker complete a pass before judging health
health="$(curl -fsS -m 5 http://127.0.0.1:8000/health)"
python3 - "$health" <<'PY'
import json, sys
h = json.loads(sys.argv[1])
bad = [k for k in ("worker_running", "persistent_database") if not h.get(k)]
if h.get("status") != "ok" or bad or h.get("worker_errors"):
    sys.exit(f"DEPLOY UNHEALTHY: status={h.get('status')} missing={bad} worker_errors={h.get('worker_errors')}")
print("healthy:", {k: h.get(k) for k in ("telecom", "calendar", "calendar_credentials", "pilot_recipient_count")})
PY
echo "DEPLOYED $(git rev-parse --short HEAD) on $(hostname)"
REMOTE
