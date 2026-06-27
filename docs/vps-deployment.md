# 24/7 deployment on a VPS

Running the bridge on a VPS lets you message your bot any time without leaving a home
computer on. This guide covers a `systemd` service and the headless-Chrome caveats for
the NotebookLM MCP server.

## 1. Install on the VPS

```bash
sudo apt update && sudo apt install -y python3 python3-venv nodejs npm chromium-browser xvfb
git clone <your-fork-url> /opt/claude4nblm
cd /opt/claude4nblm
python3 -m venv .venv
.venv/bin/pip install -e .
cp .env.example .env   # then edit: TELEGRAM_BOT_TOKEN, ANTHROPIC_API_KEY
```

## 2. NotebookLM authentication on a headless server

The NotebookLM MCP server logs into Google through a **visible** Chrome the first time.
On a headless VPS you have two options:

- **Recommended:** do the one-time `setup_auth` login on your laptop, then copy the
  persisted Chrome profile directory to the VPS so cookies carry over.
- **Alternative:** run the login under a virtual display with `xvfb-run` (combine with an
  SSH X-forwarding session or a VNC view to complete the Google login):

  ```bash
  xvfb-run -a npx notebooklm-mcp@latest
  ```

Google sessions expire periodically; expect to re-authenticate occasionally (the server
exposes a `re_auth` tool for this).

## 3. Pre-authorize your chat (no terminal pairing)

Under `systemd` there is no interactive terminal to type the pairing code into. Pre-author­ize
your phone instead: find your chat ID (message the bot once and read the logged
`Pairing requested by chat <id>` line, or use a tool like `@userinfobot`), then set it in
`.env`:

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
# Provide a virtual display so the MCP server's Chrome can start if needed.
Environment=DISPLAY=:99
ExecStartPre=/usr/bin/bash -c 'Xvfb :99 -screen 0 1280x1024x24 >/dev/null 2>&1 &'

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
  re-run the login (step 2) or have Claude invoke the `re_auth` tool.
