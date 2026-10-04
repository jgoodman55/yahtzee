#!/usr/bin/env bash
# Ad hoc rebuild on the droplet. Install as ~/bin/yahtzee-rebuild:
#   mkdir -p "$HOME/bin"
#   ln -sfn "$HOME/yahtzee/scripts/yahtzee-rebuild.sh" "$HOME/bin/yahtzee-rebuild"
#
# Same sequence as .github/workflows/deploy-vps.yml: fetch origin/main,
# stop DAC, trap a restart, bruin run, export sidecars. Do not run this
# while that workflow is in progress (both take /tmp/yahtzee-rebuild.lock).
set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=${XDG_RUNTIME_DIR}/bus}"

DEPLOY_PATH="${DEPLOY_PATH:-$HOME/yahtzee}"
BRUIN_CONFIG_FILE="${BRUIN_CONFIG_FILE:-$DEPLOY_PATH/.bruin.yml}"

if [ -x "$HOME/.venvs/yahtzee/bin/python" ]; then
  PYTHON="$HOME/.venvs/yahtzee/bin/python"
else
  PYTHON=python3
fi

cd "$DEPLOY_PATH"

exec 9>/tmp/yahtzee-rebuild.lock
if ! flock -n 9; then
  echo "yahtzee-rebuild: another rebuild holds /tmp/yahtzee-rebuild.lock (deploy workflow or ~/bin/yahtzee-rebuild)." >&2
  exit 1
fi

git fetch origin
git reset --hard origin/main

# DuckDB is single-writer. Restart on the way out even if bruin or an export fails.
if systemctl --user is-enabled yahtzee-dac.service >/dev/null 2>&1; then
  systemctl --user stop yahtzee-dac.service
fi
trap 'systemctl --user start yahtzee-dac.service || true' EXIT

bruin run --workers 1 --config-file "$BRUIN_CONFIG_FILE"

"$PYTHON" dashboard/scripts/export_scorecards.py
"$PYTHON" dashboard/scripts/export_pub_map.py
# preview.jpg on the Top tab is a checked-in screenshot. Refresh it with
# dashboard/scripts/export_map_preview.py on a machine that has Chrome.
# This rebuild does not launch a browser.
