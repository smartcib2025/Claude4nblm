# 24/7 deployment on a VPS (Hostinger)

Running the bridge on a VPS lets you message your bot any time without leaving a home
computer on. This guide targets a **Hostinger VPS** (Ubuntu 22.04/24.04, KVM) but applies
to any Ubuntu/Debian server. With `notebooklm-py` the NotebookLM session is a saved token
file, so **no browser has to run on the server** — that's the whole trick to going headless.

## Quick install (one command)

The repo ships an interactive installer that does steps 1–5 below for you — installs
dependencies, creates the venv, prompts for your tokens, writes `.env`, checks NotebookLM
auth, and sets up the systemd service. It supports **Ubuntu/Debian (`apt`)** and
**AlmaLinux/Rocky/CentOS/Fedora (`dnf`/`yum`)** — on RHEL-family systems whose default
Python is older than 3.10 (e.g. AlmaLinux 8/9) it installs `python3.12` automatically.

```bash
# Install git first (Ubuntu/Debian):   sudo apt update && sudo apt install -y git
# Install git first (AlmaLinux/RHEL):  sudo dnf install -y git
sudo git clone https://github.com/smartcib2025/Claude4nblm.git /opt/claude4nblm
sudo chown -R "$USER:$USER" /opt/claude4nblm
cd /opt/claude4nblm && git checkout claude/notebooklm-telegram-mobile-waoecu
bash scripts/setup_vps.sh
```

> Not sure which distro you're on? Run `cat /etc/os-release` first. Ubuntu/Debian → `apt`;
> AlmaLinux/Rocky/CentOS/Fedora → `dnf`.

You'll still need to log in to NotebookLM once on your laptop (`notebooklm login`) and
either copy `storage_state.json` to the server or paste it when the script asks — see
step 2. The rest of this page explains what the script does, and the fully manual path.

## 1. Install on the VPS

SSH into your Hostinger VPS (Hostinger panel → VPS → *SSH access* / browser terminal), then:

```bash
sudo apt update && sudo apt install -y python3 python3-venv git
git clone https://github.com/smartcib2025/Claude4nblm.git /opt/claude4nblm
cd /opt/claude4nblm && git checkout claude/notebooklm-telegram-mobile-waoecu
python3 -m venv .venv
.venv/bin/pip install -e .
cp .env.example .env   # then edit: TELEGRAM_BOT_TOKEN, ANTHROPIC_API_KEY
```

No Node.js or Chrome is needed on the server — `notebooklm-py` talks to NotebookLM's
endpoints directly using a saved session (below).

## 2. NotebookLM authentication on a headless server

The login itself needs a browser, so do it **once on your laptop**, then move the saved
session to the VPS. Two equivalent ways:

**Option A — copy the session file (simplest):**
```bash
# On your laptop:
pip install "notebooklm-py[browser]"
notebooklm login          # sign into Google in the browser that opens
notebooklm list           # confirm it works
cat ~/.notebooklm/profiles/default/storage_state.json   # copy this file's contents/path

# Copy it to the VPS (scp or paste), landing at the same path:
scp ~/.notebooklm/profiles/default/storage_state.json \
    root@YOUR_VPS_IP:~/.notebooklm/profiles/default/storage_state.json
```

**Option B — paste the session into `.env` (no file to manage):**
Put the entire JSON on one line in the VPS `.env`:
```env
NOTEBOOKLM_AUTH_JSON={"cookies":[...],"origins":[...]}
```
When `NOTEBOOKLM_AUTH_JSON` is set, the CLI uses it directly with no browser.

Verify on the VPS:
```bash
cd /opt/claude4nblm && .venv/bin/notebooklm list
```

### Keeping the session alive (self-healing)
Google sessions expire periodically. `notebooklm-py` can refresh them unattended via a
refresh command — set `NOTEBOOKLM_REFRESH_CMD` in `.env` (see `notebooklm auth --help` and
`notebooklm auth refresh`). If answers ever start failing, re-run the laptop login and copy
the new session over.

## 3. Pre-authorize your chat (no terminal pairing)

Under `systemd` there is no interactive terminal to type the pairing code into. Pre-author­ize
your phone instead: message the bot once and read the logged
`Pairing requested by chat <id>` line (`journalctl -u claude4nblm`), or use a tool like
`@userinfobot`, then set it in `.env`:

```env
ALLOWED_CHAT_IDS=123456789
```

## 4. systemd unit

Create `/etc/systemd/system/claude4nblm.service`:

```ini
[Unit]
Description=claude4nblm Telegram <-> Claude Code + NotebookLM bridge
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/claude4nblm
ExecStart=/opt/claude4nblm/.venv/bin/python -m claude4nblm
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now claude4nblm
sudo journalctl -u claude4nblm -f   # follow logs
```

## 5. Operating notes

- **Logs:** `journalctl -u claude4nblm -f`.
- **Updates:** `git pull && .venv/bin/pip install -e . && sudo systemctl restart claude4nblm`.
- **Secrets:** keep `.env` readable only by the service user (`chmod 600 .env`).
- **Re-auth:** if NotebookLM answers start failing, the Google session likely expired —
  redo the laptop login (step 2) and copy the fresh session over.
- **Hostinger sizing:** the bridge itself is light; a small KVM plan (1–2 vCPU, 2–4 GB RAM)
  is plenty. Most memory goes to whatever Claude does per task.
