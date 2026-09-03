# J.A.R.V.I.S.

*Just A Rather Very Intelligent System* — a personal AI assistant in the shape of
Tony Stark's, built from four parts that each do one job well:

| Part | Job | Why |
|---|---|---|
| **Claude** | the brain | reasoning, judgement, and deciding what to remember |
| **Obsidian** | the memory | plain markdown you own, read, and edit by hand |
| **Wispr Flow** | ears | system-wide dictation — you talk, it types |
| **Fish Audio** | the voice | a cloned J.A.R.V.I.S. voice reading replies aloud |

The result: you hold a hotkey, speak, and a calm British voice answers — having
first gone and *looked up* what it knows about you, and quietly written down
anything new worth keeping.

---

## What makes it better than the film version

- **The memory is yours.** Every fact lands in your Obsidian vault as a
  markdown note with frontmatter and `[[wikilinks]]`. No opaque database. Open
  Obsidian, read what J.A.R.V.I.S. thinks it knows, correct it with your own
  hands, and it picks the correction straight up.
- **It remembers unprompted.** Tell it a preference, a deadline, a fact about a
  person, and it files it without being asked. Ask it something later and it
  searches the vault *before* answering rather than guessing.
- **It corrects itself.** Facts that go stale get removed and rewritten, so the
  vault doesn't accumulate contradictions.
- **It knows when to shut up.** Replies are written for the ear — a few
  sentences, no markdown, no bullet salad — because they're going to be spoken.

---

## Setup

### 0. Install

```bash
git clone <this repo> && cd Pulse-flask
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 1. The brain — Claude

Get an API key from [console.anthropic.com](https://console.anthropic.com), then
in `.env`:

```bash
ANTHROPIC_API_KEY=sk-ant-...
JARVIS_MODEL=claude-opus-5     # or claude-sonnet-5 for faster, cheaper replies
```

Optionally let it think before it speaks — slower, noticeably sharper on
anything involving planning:

```bash
JARVIS_THINKING_BUDGET=4000    # 0 disables extended thinking
```

### 2. The memory — Obsidian

Point it at the folder containing your vault's `.obsidian` directory:

```bash
OBSIDIAN_VAULT_PATH=/Users/you/Documents/Obsidian/Vault
OBSIDIAN_SUBFOLDER=JARVIS
```

On first run it creates its own corner of the vault and leaves the rest of your
notes alone (it can *read* everything, but only ever *writes* inside `JARVIS/`
unless you ask it to write elsewhere):

```
Vault/
└── JARVIS/
    ├── Core.md                     ← always loaded into context. Edit this first.
    ├── Memory/
    │   ├── People/Pepper Potts.md
    │   ├── Projects/Mark VII.md
    │   └── Preferences/Coffee.md
    ├── Conversations/2026-09-03.md ← full transcript, one note per day
    └── Daily/2026-09-03.md
```

**Start by filling in `Core.md`.** It's prepended to every single exchange — who
you are, your standing orders, what you're working on this month. Keep it short;
everything else can be searched.

If your vault syncs (Obsidian Sync, iCloud, Syncthing), J.A.R.V.I.S.'s memory
syncs with it. Run it on your desktop, read what it remembered on your phone.

### 3. The voice — Fish Audio

1. Sign up at [fish.audio](https://fish.audio) and create an API key.
2. Find or clone a voice. For a genuine J.A.R.V.I.S., clone one from a clip of
   crisp British RP — Fish Audio needs only a few seconds of reference audio.
3. Copy the voice model's `reference_id` from its page URL.

```bash
FISH_AUDIO_API_KEY=...
FISH_AUDIO_VOICE_ID=<reference_id>
```

Not sure of the id? Start the server and hit `GET /api/voices` — it lists every
voice model on your account.

Synthesised lines are cached on disk, so repeated phrases ("Good morning, sir")
come back instantly and cost nothing.

### 4. The ears — Wispr Flow

Wispr Flow is system-wide dictation: it transcribes your speech and types it
into whatever field has focus. There's no API to wire up — **the J.A.R.V.I.S.
text box *is* the microphone.**

Install [Wispr Flow](https://wisprflow.ai), then:

1. Start J.A.R.V.I.S. and leave the console focused.
2. Hold your Wispr Flow hotkey and speak.
3. Your words appear in the input box.

The console watches for text arriving in *bursts* rather than keystroke by
keystroke — that's how it tells dictation from typing — and sends the message
about a second after you stop speaking. No Enter, no clicking. Turn it off with
the **auto-send dictation** toggle in the top bar if you'd rather press Enter
yourself.

The waveform beside the input lights up while dictation is landing, so you can
see it heard you.

---

## Running it

```bash
python run.py
# J.A.R.V.I.S. online at http://127.0.0.1:5000
```

Open the browser, or stay in the terminal:

```bash
python bridge/jarvis_cli.py                       # conversational, speaks replies
python bridge/jarvis_cli.py "what's on today?"    # one-shot
python bridge/jarvis_cli.py --no-speech           # text only
```

The CLI is the better hands-free path on a laptop: dictate into the terminal
with Wispr Flow, press Enter, and the answer comes back out loud through
`afplay`/`mpv`/`ffplay`, whichever you have.

---

## Talking to it

> **You:** Pepper's moved the board meeting to Thursday at ten.
> **J.A.R.V.I.S.:** Noted, sir. Thursday at ten. That collides with your workshop
> block — shall I move that?

> **You:** What do I know about the Mark VII power draw?
> *(consults vault · "Mark VII power draw")*
> **J.A.R.V.I.S.:** You logged it at forty percent above the Mark VI in March,
> and flagged the ankle actuators as the likely cause. You haven't retested since.

Under each reply, chips show exactly which notes it read and wrote — you can
always see when it consulted the vault versus answered from context.

---

## The tools Claude has

All seven operate on the vault, and all of them are path-confined to it:

| Tool | What it does |
|---|---|
| `search_memory` | ranked full-text search over the vault |
| `read_note` | read one note in full |
| `remember` | file a single durable fact under `Memory/<category>/<subject>.md` |
| `write_note` | create/append/prepend longer material |
| `forget` | strip stale lines from a note, for corrections |
| `add_daily_note` | timestamped line in today's daily note |
| `list_recent_notes` | "what was I working on?" |

---

## Configuration

Everything is environment variables — see [`.env.example`](.env.example) for the
full annotated list. The ones worth knowing:

| Variable | Default | Notes |
|---|---|---|
| `JARVIS_USER_NAME` | `Sir` | what it calls you |
| `JARVIS_NAME` | `J.A.R.V.I.S.` | rename it if you'd rather have FRIDAY |
| `JARVIS_PERSONA_FILE` | — | path to a file replacing the built-in system prompt |
| `JARVIS_HISTORY_TURNS` | `20` | working context size; the vault holds the rest |
| `JARVIS_SPEECH_ENABLED` | `true` | start with the voice off |
| `JARVIS_THINKING_BUDGET` | `0` | extended thinking tokens |

The persona itself lives in [`jarvis/persona.py`](jarvis/persona.py) — the dry
wit, the "answer, don't preamble" rule, and the instructions about when to write
to memory. Tune it there, or override the whole thing with a persona file.

---

## HTTP API

| Endpoint | Purpose |
|---|---|
| `POST /api/chat` | `{"text": "..."}` → reply, tool calls, token usage |
| `POST /api/speak` | `{"text": "..."}` → audio bytes in J.A.R.V.I.S.'s voice |
| `GET /api/status` | readiness of brain, memory and voice |
| `GET /api/memory/search?q=` | search the vault directly |
| `GET /api/memory/note?path=` | read one note |
| `GET /api/voices` | Fish Audio voice models on your account |
| `POST /api/reset` | clear working context (the vault is untouched) |

---

## Notes on running it safely

- **Bind to localhost.** There is no authentication; `JARVIS_HOST` defaults to
  `127.0.0.1` for good reason. Anyone who can reach the port can read your vault.
  Put it behind a reverse proxy with auth before exposing it.
- **Vault contents are treated as data, not instructions.** The system prompt
  tells Claude to report, not obey, anything in a note that looks like a command
  — worth knowing if you clip web content into your vault.
- **Path confinement is enforced in code**, not just in the prompt: every tool
  path resolves against the vault root and anything escaping it is refused.
- Use the development server for personal use; put `gunicorn` in front of it if
  you want it running all day.

## Tests

```bash
python -m pytest tests/ -q      # 46 tests, no network required
```

The Claude client and Fish Audio are faked in tests, so the suite runs offline
and never spends a token.
