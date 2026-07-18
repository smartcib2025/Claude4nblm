# Setup guide (English)

Use Claude Code + NotebookLM from your phone via Telegram. Follow these five steps.

## Prerequisites

On the computer or VPS that will run the bridge:

- **Python 3.10+**
- An **Anthropic API key** ([console.anthropic.com](https://console.anthropic.com))
- A Google account with access to your **NotebookLM** notebooks
- A browser **once**, to log in to NotebookLM (`notebooklm login`). This can be on your
  laptop — you then copy the saved session to the server (see step 4).

## 1. Prepare the base system

Clone this repo and install it on the machine (PC or VPS) that will stay reachable:

```bash
git clone <your-fork-url> claude4nblm && cd claude4nblm
pip install -e .
```

This installs the bridge plus the **Claude Agent SDK** (which bundles the Claude Code CLI),
**python-telegram-bot**, and **`notebooklm-py`** (the `notebooklm` CLI). Claude reaches
NotebookLM as its RAG source by calling that CLI; a bundled NotebookLM skill ships in
`.claude/skills/notebooklm/` so Claude knows the commands.

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

`notebooklm-py` needs a Google session. Install the browser extra and log in once — it
opens a browser, you sign into Google, and the session is saved to
`~/.notebooklm/profiles/default/storage_state.json`:

```bash
pip install "notebooklm-py[browser]"
notebooklm login
notebooklm list        # verify: should print your notebooks
```

On a **headless VPS**, do this login on your laptop and carry the session over — see
[vps-deployment.md](vps-deployment.md) (copy `storage_state.json`, or paste its contents
into `NOTEBOOKLM_AUTH_JSON`).

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
