#!/usr/bin/env bash
# Unregister and stop the user-sandbox self-hosted runner.
set -euo pipefail
REPO="${1:-populous/sandbox}"
DIR="${2:-$HOME/actions-runner-user-sandbox}"
cd "$DIR"
if [ -f ./svc.sh ] && [ -f ./.service ]; then sudo ./svc.sh stop || true; sudo ./svc.sh uninstall || true; fi
TOKEN="$(gh api -X POST "repos/${REPO}/actions/runners/remove-token" --jq .token)"
./config.sh remove --token "$TOKEN"
