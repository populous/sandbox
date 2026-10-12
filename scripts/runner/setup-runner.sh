#!/usr/bin/env bash
# Register this WSL2/Linux machine as the self-hosted runner for user-sandbox.
# Requirements: gh (logged in as repo admin), curl, tar, python3.
# Usage:
#   bash scripts/runner/setup-runner.sh [--repo OWNER/REPO] [--dir DIR] [--name NAME] [--service]
set -euo pipefail

REPO="populous/sandbox"
DIR="$HOME/actions-runner-user-sandbox"
NAME="$(hostname)-user-sandbox"
LABELS="user-sandbox"
SERVICE=0

while [ $# -gt 0 ]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    --dir) DIR="$2"; shift 2 ;;
    --name) NAME="$2"; shift 2 ;;
    --service) SERVICE=1; shift ;;
    -h|--help) sed -n '2,6p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

case "$(uname -m)" in
  x86_64) ARCH=x64 ;;
  aarch64|arm64) ARCH=arm64 ;;
  *) echo "unsupported arch: $(uname -m)" >&2; exit 1 ;;
esac

VERSION="$(gh api repos/actions/runner/releases/latest --jq .tag_name | sed 's/^v//')"
PKG="actions-runner-linux-${ARCH}-${VERSION}.tar.gz"
echo "runner v${VERSION} (${ARCH}) -> ${DIR}"

mkdir -p "$DIR" && cd "$DIR"
if [ ! -f ./config.sh ]; then
  curl -fsSL -o "$PKG" "https://github.com/actions/runner/releases/download/v${VERSION}/${PKG}"
  tar xzf "$PKG" && rm -f "$PKG"
fi

TOKEN="$(gh api -X POST "repos/${REPO}/actions/runners/registration-token" --jq .token)"
./config.sh --unattended --replace \
  --url "https://github.com/${REPO}" \
  --token "$TOKEN" \
  --name "$NAME" \
  --labels "$LABELS" \
  --work _work

if [ "$SERVICE" = 1 ]; then
  sudo ./svc.sh install "$USER" && sudo ./svc.sh start
  echo "installed as service (requires systemd in WSL2: /etc/wsl.conf [boot] systemd=true)"
else
  echo "start interactively with: cd $DIR && ./run.sh"
fi
