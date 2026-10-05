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
# Caddy stays on 127.0.0.1:8321. DAC moves to 8322 and the new-tab proxy
# listens on 8321 so the pub-map preview can open in a new tab. If the proxy
# cannot start, DAC is put back on 8321 so the site is not left down.
DAC_UNIT="${HOME}/.config/systemd/user/yahtzee-dac.service"
PROXY_UNIT="${HOME}/.config/systemd/user/yahtzee-newtab-proxy.service"

install_newtab_proxy() {
  if [ ! -f "$DAC_UNIT" ]; then
    return 0
  fi
  if grep -q -- '--port 8321' "$DAC_UNIT"; then
    sed -i 's/--port 8321/--port 8322/' "$DAC_UNIT"
  fi
  cat > "$PROXY_UNIT" <<EOF
[Unit]
Description=Yahtzee pub-map new-tab proxy
After=network.target

[Service]
Type=simple
WorkingDirectory=${DEPLOY_PATH}
ExecStart=${PYTHON} ${DEPLOY_PATH}/dashboard/scripts/newtab_proxy.py --listen 127.0.0.1:8321 --upstream 127.0.0.1:8322
Restart=on-failure

[Install]
WantedBy=default.target
EOF
  systemctl --user daemon-reload
  systemctl --user enable yahtzee-newtab-proxy.service >/dev/null
}

start_site() {
  systemctl --user start yahtzee-dac.service || true
  if [ ! -f "$PROXY_UNIT" ]; then
    return 0
  fi
  if systemctl --user start yahtzee-newtab-proxy.service; then
    return 0
  fi
  echo "yahtzee-newtab-proxy failed to start; putting DAC back on 8321" >&2
  if [ -f "$DAC_UNIT" ] && grep -q -- '--port 8322' "$DAC_UNIT"; then
    systemctl --user stop yahtzee-dac.service || true
    sed -i 's/--port 8322/--port 8321/' "$DAC_UNIT"
    systemctl --user daemon-reload || true
    systemctl --user start yahtzee-dac.service || true
  fi
}

if systemctl --user is-enabled yahtzee-dac.service >/dev/null 2>&1; then
  systemctl --user stop yahtzee-dac.service
fi
if systemctl --user is-enabled yahtzee-newtab-proxy.service >/dev/null 2>&1; then
  systemctl --user stop yahtzee-newtab-proxy.service
fi
install_newtab_proxy
trap start_site EXIT

bruin run --workers 1 --config-file "$BRUIN_CONFIG_FILE"

"$PYTHON" dashboard/scripts/export_scorecards.py
"$PYTHON" dashboard/scripts/export_pub_map.py
# preview.svg on the Top tab is a checked-in screenshot. Refresh it with
# dashboard/scripts/export_map_preview.py on a machine that has Chrome.
# This rebuild does not launch a browser.
