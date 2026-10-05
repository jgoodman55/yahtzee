# Hosting Yahtzee on the DigitalOcean droplet

The live site is [https://yahtzee.jginfo.xyz](https://yahtzee.jginfo.xyz).
After merge, GitHub Actions **SSHs to the droplet and runs Bruin on the box**.
Grok stays the OCR step; CI score-rule tests are the validation alert.

Do **not** provision a VPS from this repo. This is the runbook for the box
that is already running.

| Workflow | File | When |
|---|---|---|
| PR validation | [`.github/workflows/scorecard-validation.yml`](../.github/workflows/scorecard-validation.yml) | PRs that touch seeds / audit / tests (or manual `workflow_dispatch`) |
| Deploy | [`.github/workflows/deploy-vps.yml`](../.github/workflows/deploy-vps.yml) | `push` to `main`, or Actions → **Deploy VPS** → Run workflow |

## What is running

Ubuntu 24.04 droplet, SSH user `ubuntu`. The app checkout is
`/home/ubuntu/yahtzee`.

**ufw** allows only 22, 80, and 443. The new-tab proxy listens on
`127.0.0.1:8321` and forwards to `dac serve` on `127.0.0.1:8322`. Nothing
listens on 8765. Neither port is open to the internet, and there is no
`python -m http.server` sidecar.

**Caddy** (official apt repo) terminates HTTPS for `yahtzee.jginfo.xyz` and
also answers plain HTTP on the droplet IP (`46.101.81.198`). It serves
`/pub_map.html`, `/pub_map/*`, `/scorecards`, and `/scorecards/*` from
`/home/ubuntu/yahtzee/dashboard` on disk. Every other path is reverse-proxied
to `127.0.0.1:8321`. `/yahtzee.yml`, `/.bruin.yml`, and `/data/*` are 404s.

**DAC 0.21.0** is a systemd **user** unit (`yahtzee-dac.service`) with linger,
so it stays up after logout. It is bound to `--host 127.0.0.1 --port 8322`
and `--config` points at the absolute `.bruin.yml`. DAC 0.21 escapes HTML in
text widgets, so the Top-tab pub map link cannot set `target=_blank` itself.
`yahtzee-newtab-proxy.service` listens on `127.0.0.1:8321` (the address Caddy
already proxies to), forwards to DAC, and injects `dashboard/pub_map/newtab.js`
into HTML. That script sets `target=_blank` and `rel=noopener` only on the
preview image.

A **2 GB swapfile** is on so `bruin run` has headroom on a small droplet.

Python dependencies live in a virtualenv at `~/.venvs/yahtzee`. Ubuntu 24.04
marks the system interpreter as externally managed (PEP 668), so
`pip install --user` fails.

## 1. Droplet, firewall, swap

Any small Ubuntu 24.04 droplet is enough (1 vCPU, 1–2 GB RAM). Add your
personal SSH key at create time.

```bash
sudo apt-get update
sudo apt-get install -y git python3 python3-pip python3-venv ufw

sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status

sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

Do not open 8321 or 8765.

## 2. Install Bruin, DAC 0.21.0, and the venv

```bash
# Bruin + DAC CLIs land in ~/.local/bin
curl -LsSf https://getbruin.com/install/cli | sh
# Pin DAC so this box matches the laptop (do not install floating latest).
curl -LsSf https://getbruin.com/install/dac | sh -s -- v0.21.0
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.profile
export PATH="$HOME/.local/bin:$PATH"

python3 -m venv "$HOME/.venvs/yahtzee"
"$HOME/.venvs/yahtzee/bin/pip" install -U pip
```

Confirm `bruin version` and `dac version` (`dac version` must print `0.21.0`).

## 3. Clone the repo and copy `.bruin.yml` with **absolute** DuckDB paths

```bash
git clone https://github.com/jgoodman55/yahtzee.git "$HOME/yahtzee"
cd "$HOME/yahtzee"
cp .bruin.yml.example .bruin.yml
"$HOME/.venvs/yahtzee/bin/pip" install -r assets/python/requirements.txt
```

`assets/python/requirements.txt` is what Bruin's Python assets import
(`pandas`, `duckdb`, `bruin-sdk`). `dashboard/scripts/export_pub_map.py`
imports `duckdb` from the same venv. The deploy workflow and
`scripts/yahtzee-rebuild.sh` pick `$HOME/.venvs/yahtzee/bin/python` when it
exists, and fall back to `python3`.

Edit `.bruin.yml` so both DuckDB connections use an **absolute** path.
Relative `yahtzee.duckdb` breaks when systemd starts DAC from another cwd,
and it is the usual reason `dac serve` / `dac check` cannot see marts.

```yaml
# $HOME/yahtzee/.bruin.yml  (gitignored — do not commit)
default_environment: default
environments:
  default:
    connections:
      duckdb:
        - name: duckdb-default
          path: /home/ubuntu/yahtzee/yahtzee.duckdb   # <-- absolute
          max_concurrent_assets: 1
        - name: local_duckdb
          path: /home/ubuntu/yahtzee/yahtzee.duckdb   # <-- same file
          read_only: true
```

## 4. One-time `bruin run` and `dac serve` as a systemd user service

The pipeline is seed-only: games, commentary, and pub locations come from
CSVs. No Nominatim, no Google Places, no API key.

```bash
cd "$HOME/yahtzee"
bruin run --workers 1 --config-file "$HOME/yahtzee/.bruin.yml"
"$HOME/.venvs/yahtzee/bin/python" dashboard/scripts/export_scorecards.py
"$HOME/.venvs/yahtzee/bin/python" dashboard/scripts/export_pub_map.py
```

`--config-file` is the Bruin flag for `.bruin.yml` (connections).

Enable lingering so the user unit survives logout, then install DAC:

```bash
sudo loginctl enable-linger "$USER"
mkdir -p ~/.config/systemd/user
```

`~/.config/systemd/user/yahtzee-dac.service`:

```ini
[Unit]
Description=Yahtzee DAC dashboard
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/ubuntu/yahtzee
Environment=HOME=/home/ubuntu
Environment=PATH=/home/ubuntu/.local/bin:/usr/bin
# --config must point at .bruin.yml (Jordan's laptop lesson). Same file as bruin --config-file.
# Bound to loopback. Caddy is the only public listener.
ExecStart=/home/ubuntu/.local/bin/dac serve --dir dashboard --template yahtzee-dark --host 127.0.0.1 --port 8322 --config /home/ubuntu/yahtzee/.bruin.yml
Restart=on-failure

[Install]
WantedBy=default.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable --now yahtzee-dac.service
```

`~/.config/systemd/user/yahtzee-newtab-proxy.service` (Caddy keeps using 8321):

```ini
[Unit]
Description=Yahtzee pub-map new-tab proxy
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/ubuntu/yahtzee
ExecStart=/home/ubuntu/.venvs/yahtzee/bin/python /home/ubuntu/yahtzee/dashboard/scripts/newtab_proxy.py --listen 127.0.0.1:8321 --upstream 127.0.0.1:8322
Restart=on-failure

[Install]
WantedBy=default.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable --now yahtzee-newtab-proxy.service
```

The next deploy rewrites that proxy unit and, if the DAC unit still says
`--port 8321`, changes it to `8322`. Caddy's `reverse_proxy` line stays
`127.0.0.1:8321`.

Stop `dac serve` before a manual `bruin run` (DuckDB cannot mix a writer with
open readers). The deploy workflow and `~/bin/yahtzee-rebuild` do this, and
restart DAC and the proxy on the way out even when `bruin run` or an export
fails. If the proxy fails to bind, the trap puts DAC back on 8321.

## 5. Caddy

Caddy comes from the [official apt repo](https://caddyserver.com/docs/install#debian-ubuntu-raspbian),
not Ubuntu's older package.

```bash
sudo apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt-get update
sudo apt-get install -y caddy
```

Caddy runs as the `caddy` user. `/home/ubuntu` is typically mode `750`, so
the service cannot traverse it into the checkout. Others need execute on the
home directory (not read). Files under the repo stay world-readable, which
a normal `git clone` already is.

```bash
sudo chmod o+x /home/ubuntu
```

`/etc/caddy/Caddyfile`:

```caddyfile
(yahtzee) {
	handle /yahtzee.yml {
		respond "Not found" 404
	}
	handle /.bruin.yml {
		respond "Not found" 404
	}
	handle /data {
		respond "Not found" 404
	}
	handle /data/* {
		respond "Not found" 404
	}

	handle /pub_map.html {
		root * /home/ubuntu/yahtzee/dashboard
		file_server
	}
	handle /pub_map/* {
		root * /home/ubuntu/yahtzee/dashboard
		file_server
	}
	handle /scorecards {
		root * /home/ubuntu/yahtzee/dashboard
		file_server
	}
	handle /scorecards/* {
		root * /home/ubuntu/yahtzee/dashboard
		file_server
	}

	handle {
		# The new-tab proxy. It forwards to DAC on 127.0.0.1:8322.
		reverse_proxy 127.0.0.1:8321
	}
}

# Automatic HTTPS (certificate for this hostname).
yahtzee.jginfo.xyz {
	import yahtzee
}

# Plain HTTP when someone hits the droplet IP. No certificate.
http://46.101.81.198 {
	import yahtzee
}
```

```bash
sudo systemctl reload caddy
```

`/scorecards` redirects to `/scorecards/` and serves `index.html`. Nested
files such as `/scorecards/samples/game_1.png` match `/scorecards/*`.
Dashboard links are root-relative (`/scorecards/...`, `/pub_map.html`), so
they hit this site block rather than DAC.

Caddy reads those files from disk. A deploy that only regenerates GeoJSON
or `games.js` does not need a Caddy reload.

## 6. Deploy SSH key → GitHub Actions secrets

On a trusted machine (not the VPS), create a **dedicated** key (no passphrase,
so Actions can use it):

```bash
ssh-keygen -t ed25519 -C "github-actions-yahtzee-deploy" -f yahtzee-deploy -N ""
```

On the VPS, append the **public** key:

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
cat >> ~/.ssh/authorized_keys <<'EOF'
ssh-ed25519 AAAA... github-actions-yahtzee-deploy
EOF
chmod 600 ~/.ssh/authorized_keys
```

In the GitHub repo: **Settings → Secrets and variables → Actions**.

**Secrets**

| Name | Required | Value |
|---|---|---|
| `VPS_HOST` | yes | hostname or IP |
| `VPS_USER` | yes | SSH user (`ubuntu`, …) |
| `VPS_SSH_KEY` | yes | full private key (`-----BEGIN … PRIVATE KEY-----`) |
| `VPS_PORT` | no | SSH port (default 22) |

**Variables**

| Name | Required | Value |
|---|---|---|
| `DEPLOY_PATH` | no | clone path (default `$HOME/yahtzee` on the box) |
| `BRUIN_CONFIG_FILE` | no | absolute `.bruin.yml` (default `$DEPLOY_PATH/.bruin.yml`) |

The deploy job **skips (success)** when `VPS_HOST` / `VPS_USER` / `VPS_SSH_KEY`
are missing — forks, and this repo before you add a box. It does not run on
pull requests.

Keep the private key out of git. Delete the local `yahtzee-deploy` files after
the secret is stored, or lock them down.

## 7. Day-to-day

1. Upload the scorecard photo to **Grok** → propose `raw_games` (and related seed) updates.
2. Open a PR. CI [`.github/workflows/scorecard-validation.yml`](../.github/workflows/scorecard-validation.yml)
   runs `python tests/test_raw_games_score_rules.py` and pytest. Failures list
   impossible scores — that is the review queue (fix the seed, or allowlist a
   leftover after photo review).
3. Merge to `main`.
4. [`.github/workflows/deploy-vps.yml`](../.github/workflows/deploy-vps.yml)
   SSHs in, `git fetch` + `reset --hard origin/main`, stops DAC, runs
   `bruin run --workers 1 --config-file "$BRUIN_CONFIG_FILE"`, exports
   scorecards + pub map with the venv Python, and starts DAC and the new-tab
   proxy again from an `EXIT` trap so a failed `bruin run` or export does not
   leave the site down.

The workflow's `concurrency` group is `deploy-vps` (`cancel-in-progress: false`),
so two Actions deploys never overlap. See also the lock in the next section.

## 8. Ad hoc rebuild

GitHub → **Actions** → **Deploy VPS** → **Run workflow**.

That always deploys `origin/main`, even if you started the run from another
branch. Use it after a manual fix on the box, a failed run, or a first-time
secrets check.

On the droplet, the same sequence is `~/bin/yahtzee-rebuild`, committed as
[`scripts/yahtzee-rebuild.sh`](../scripts/yahtzee-rebuild.sh):

```bash
mkdir -p "$HOME/bin"
ln -sfn "$HOME/yahtzee/scripts/yahtzee-rebuild.sh" "$HOME/bin/yahtzee-rebuild"
# ~/.profile should have $HOME/bin on PATH
~/bin/yahtzee-rebuild
```

The script `git fetch`es, `git reset --hard origin/main`, stops DAC, runs
`bruin run --workers 1 --config-file`, runs both `dashboard/scripts/export_*.py`,
and restarts DAC and the new-tab proxy from an `EXIT` trap.

Do not run `~/bin/yahtzee-rebuild` while the deploy workflow is in progress,
and do not start a second manual rebuild over the first. Both take
`flock` on `/tmp/yahtzee-rebuild.lock` and the second one exits before it
stops DAC. DuckDB still allows only one writer.

## 9. `dac serve` / `dac check` need `--config`

DAC auto-discovers `.bruin.yml` by walking upward from `--dir dashboard`.
On a laptop that failed when the working tree layout or cwd did not match
(Jordan's lesson), pass the file explicitly:

```bash
dac check --dir dashboard --config /home/ubuntu/yahtzee/.bruin.yml
dac serve --dir dashboard --template yahtzee-dark --host 127.0.0.1 --port 8322 --config /home/ubuntu/yahtzee/.bruin.yml
```

Bruin's equivalent flag is `--config-file` (or `BRUIN_CONFIG_FILE`). The
systemd unit and the deploy workflow both pass the absolute path.

## 10. Local proxy (laptop)

`dac serve` does not publish `pub_map.html` or `scorecards/`. Root-relative
links in the dashboard only resolve when something in front of DAC serves
those paths from `dashboard/`, the way Caddy does on the droplet.

From the repo root, with DAC on loopback. Point DAC at 8322 and put the
new-tab proxy on 8321 so Caddy's upstream matches production. Without the
proxy the preview still opens, in the same tab.

```bash
dac serve --dir dashboard --template yahtzee-dark --host 127.0.0.1 --port 8322
python3 dashboard/scripts/newtab_proxy.py --listen 127.0.0.1:8321 --upstream 127.0.0.1:8322
caddy run --config scripts/Caddyfile.local
# http://127.0.0.1:8080/
# http://127.0.0.1:8080/scorecards/viewer.html?game=1
# http://127.0.0.1:8080/pub_map.html
```

[`scripts/Caddyfile.local`](../scripts/Caddyfile.local) is the same routes as
the production snippet, rooted at `./dashboard` and listening on `:8080`.

## 11. Map tiles

Leaflet tiles (Esri World Light Gray / OSM) load in the **browser** when you
open `/pub_map.html`. They are not part of `bruin run`, and the pipeline does
not call Nominatim or Google Places.
