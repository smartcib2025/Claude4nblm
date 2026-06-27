# Setup guide (English)

Use Claude Code + NotebookLM from your phone via Telegram. Follow these five steps.

## Prerequisites

On the computer or VPS that will run the bridge:

- **Python 3.10+**
- **Node.js** (for `npx notebooklm-mcp`)
- **Google Chrome / Chromium** (the NotebookLM MCP server drives a real browser)
- An **Anthropic API key** ([console.anthropic.com](https://console.anthropic.com))
- A Google account with access to your **NotebookLM** notebooks

## 1. Prepare the base system

Clone this repo and install it on the machine (PC or VPS) that will stay reachable:

```bash
git clone <your-fork-url> claude4nblm && cd claude4nblm
pip install -e .
```

This installs the bridge plus the **Claude Agent SDK** (which bundles the Claude Code CLI)
and **python-telegram-bot**. The NotebookLM connection is provided by the community
`notebooklm-mcp` server, launched automatically via `npx`.

## 2. Create a bot in Telegram (@BotFather)

1. Open Telegram and search for **@BotFather** (note the official blue checkmark).
2. Send `/newbot`.
3. Choose a **Name**, then a **Username** — the username **must end in `bot`**
   (e.g. `my_research_bot`).
4. BotFather replies with an **API token**. Copy it and keep it safe.

## 3. Configure the bridge

```bash
cp .env.example .env
```

Edit `.env`:

- `TELEGRAM_BOT_TOKEN=` → paste the token from BotFather
- `ANTHROPIC_API_KEY=` → paste your Anthropic key

Optionally set `WORKDIR`, `NOTEBOOKLM_NOTEBOOK`, or pre-authorize chats with
`ALLOWED_CHAT_IDS`.

### One-time NotebookLM login

The NotebookLM MCP server needs a Google session. Run it once interactively and use its
`setup_auth` tool — it opens a visible Chrome where you log into Google once; the cookies
are then persisted in a per-user Chrome profile for future runs:

```bash
npx notebooklm-mcp@latest
```

## 4. Run and pair

Start the bridge:

```bash
python -m claude4nblm
```

You'll see **"Listening for channel messages…"**. Now, on your phone:

1. Open your new bot in Telegram and send a greeting, e.g. `hi`.
2. The bot replies with a **pairing code**.
3. Type that code into the **terminal** where the bridge is running and press Enter.
4. The bot confirms: *"This chat is now authorized."*

Because authorization requires entering the code on the machine itself, only you — the
person controlling that machine — can authorize a chat. To pre-authorize without pairing,
put your chat ID in `ALLOWED_CHAT_IDS`.

## 5. Start working from your phone

Send tasks straight into the chat, for example:

- *"List my NotebookLM notebooks."*
- *"In my 'Thesis' notebook, summarize the main arguments with citations."*
- *"Read report.md in the working directory and cross-check it against my notebook."*

Claude will use the NotebookLM tools to fetch grounded, citation-backed answers and reply
in your Telegram chat. Use `/reset` to start a fresh conversation.

For always-on use, see **[vps-deployment.md](vps-deployment.md)**.
