# Hosting Yahtzee on a small VPS

After merge, GitHub Actions **SSHs to a VPS and runs Bruin on the box**.
Grok stays the OCR step; CI score-rule tests are the validation alert.

Do **not** provision a VPS from this repo. This is a runbook for a box you
create by hand (~£5/mo).

| Workflow | File | When |
|---|---|---|
| PR validation | [`.github/workflows/scorecard-validation.yml`](../.github/workflows/scorecard-validation.yml) | PRs that touch seeds / audit / tests (or manual `workflow_dispatch`) |
| Deploy | [`.github/workflows/deploy-vps.yml`](../.github/workflows/deploy-vps.yml) | `push` to `main`, or Actions → **Deploy VPS** → Run workflow |

## 1. Create a ~£5 Ubuntu VPS

Any small Ubuntu 24.04 box is enough (1 vCPU, 1–2 GB RAM, 20 GB disk):

- [Hetzner Cloud](https://www.hetzner.com/cloud/) — CX22 / CAX11
- [DigitalOcean](https://www.digitalocean.com/pricing/droplets) — Basic droplet

Add your personal SSH key at create time. Open 22 (SSH). For the dashboard,
either open 8321 + 8765 or put nginx on 80/443 in front (step 5).

## 2. Install tools

SSH in as the deploy user (often `ubuntu`):

```bash
sudo apt-get update
sudo apt-get install -y git python3 python3-pip python3-venv

# Bruin + DAC CLIs land in ~/.local/bin
curl -LsSf https://getbruin.com/install/cli | sh
curl -LsSf https://getbruin.com/install/dac | sh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.profile
export PATH="$HOME/.local/bin:$PATH"

python3 -m pip install --user -U pip
# duckdb is required by dashboard/scripts/export_pub_map.py;
# pandas/requests are required by Bruin Python assets.
```

Confirm `bruin version` and `dac version`.

## 3. Clone the repo and copy `.bruin.yml` with **absolute** DuckDB paths

```bash
git clone https://github.com/jgoodman55/yahtzee.git "$HOME/yahtzee"
cd "$HOME/yahtzee"
cp .bruin.yml.example .bruin.yml
python3 -m pip install --user -r assets/python/requirements.txt
```

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

Replace `/home/ubuntu/yahtzee` with the real clone path.

## 4. One-time `bruin run` and `dac serve` as a systemd user service

DuckDB allows one writer. Until seed-only pubs land on `main`
([PR #25](https://github.com/jgoodman55/yahtzee/pull/25)), skip live
Nominatim / Google Places so the box needs **no geocoding keys**:

```bash
cd "$HOME/yahtzee"
OFFLINE_TEST=1 bruin run --workers 1 --config-file "$HOME/yahtzee/.bruin.yml"
```

`--config-file` is the Bruin flag for `.bruin.yml` (connections). After #25
merges, drop `OFFLINE_TEST=1`; still no Places / Nominatim keys.

Enable lingering so user units survive logout, then install DAC:

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
ExecStart=/home/ubuntu/.local/bin/dac serve --dir dashboard --template yahtzee-dark --host 0.0.0.0 --port 8321 --config /home/ubuntu/yahtzee/.bruin.yml
Restart=on-failure

[Install]
WantedBy=default.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable --now yahtzee-dac.service
# http://<vps-ip>:8321
```

Stop `dac serve` before a manual `bruin run` (DuckDB cannot mix a writer with
open readers). The deploy workflow does this automatically.

## 5. Sidecar for pub map / scorecards

DAC 0.15 does not publish `dashboard/pub_map.html` or
`dashboard/scorecards/`. Export, then serve the `dashboard/` directory.

```bash
python3 dashboard/scripts/export_scorecards.py
python3 dashboard/scripts/export_pub_map.py
```

### Option A — second systemd unit (`python -m http.server`)

`~/.config/systemd/user/yahtzee-sidecar.service`:

```ini
[Unit]
Description=Yahtzee pub map / scorecards static files
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/ubuntu/yahtzee
ExecStart=/usr/bin/python3 -m http.server 8765 --directory dashboard
Restart=on-failure

[Install]
WantedBy=default.target
```

```bash
systemctl --user enable --now yahtzee-sidecar.service
# http://<vps-ip>:8765/pub_map.html
# http://<vps-ip>:8765/scorecards/viewer.html?game=1
```

The sidecar reads files from disk; a deploy that only regenerates GeoJSON /
`games.js` does **not** need a sidecar restart.

### Option B — nginx

Point a `server` at `dashboard/` (port 80/443, optional TLS via certbot).
No extra process; still run the two `export_*.py` scripts after each
`bruin run`. Restart nginx only if you change the site config.

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
   scorecards + pub map, starts DAC again.

## 8. Adhoc rebuild

GitHub → **Actions** → **Deploy VPS** → **Run workflow**.

That always deploys `origin/main`, even if you started the run from another
branch. Use it after a manual fix on the box, a failed run, or a first-time
secrets check.

## 9. `dac serve` / `dac check` need `--config`

DAC auto-discovers `.bruin.yml` by walking upward from `--dir dashboard`.
On a laptop that failed when the working tree layout or cwd did not match
(Jordan's lesson), pass the file explicitly:

```bash
dac check --dir dashboard --config /home/ubuntu/yahtzee/.bruin.yml
dac serve --dir dashboard --template yahtzee-dark --config /home/ubuntu/yahtzee/.bruin.yml
```

Bruin's equivalent flag is `--config-file` (or `BRUIN_CONFIG_FILE`). The
systemd unit and the deploy workflow both pass the absolute path.

## 10. Pubs / geocoding keys

On current `main`, `mart_pub_locations` can still call Nominatim / Google
Places unless `OFFLINE_TEST=1`. The deploy workflow sets that env var, so
the VPS does **not** need `GOOGLE_PLACES_API_KEY`.

If [PR #25](https://github.com/jgoodman55/yahtzee/pull/25) (seed-only pubs)
has merged, you can drop `OFFLINE_TEST=1`; locations and photos are seed-only
and still need no geocoding keys. Leaflet tiles load in the **browser**, not
during `bruin run`.
