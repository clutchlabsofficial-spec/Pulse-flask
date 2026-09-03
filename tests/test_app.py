import json

import pytest

from jarvis import create_app
from jarvis.brain import Reply, trim_history
from jarvis.config import Config
from jarvis.tools import ToolRunner
from jarvis.voice import speakable


@pytest.fixture
def app(tmp_path):
    cfg = Config(
        anthropic_api_key="test-key",
        vault_path=tmp_path / "vault",
        fish_api_key="",
    )
    (tmp_path / "vault").mkdir()
    application = create_app(cfg)
    application.config["TESTING"] = True
    return application


@pytest.fixture
def client(app):
    return app.test_client()


class FakeBrain:
    """Stands in for Claude so tests never touch the network."""

    ready = True

    def __init__(self, reply="Calibrated and ready, sir."):
        self.reply = reply
        self.seen = []

    def respond(self, text, history=None):
        self.seen.append((text, list(history or [])))
        return Reply(text=self.reply, tool_calls=[{"tool": "search_memory", "input": {"query": text}, "ok": True}])


def test_status_reports_subsystems(client):
    data = client.get("/api/status").get_json()
    assert data["brain"]["ready"] is True
    assert data["memory"]["available"] is True
    assert data["voice"]["ready"] is False  # no Fish key in this fixture


def test_index_renders(client):
    body = client.get("/").get_data(as_text=True)
    assert "J.A.R.V.I.S." in body
    assert "Wispr" in body


def test_chat_returns_reply_and_logs_to_vault(app, client, tmp_path):
    app.extensions["brain"] = FakeBrain()
    res = client.post("/api/chat", json={"text": "Are the repulsors ready?"})
    data = res.get_json()
    assert res.status_code == 200
    assert data["text"] == "Calibrated and ready, sir."
    assert data["tool_calls"][0]["tool"] == "search_memory"
    conversations = list((tmp_path / "vault" / "JARVIS" / "Conversations").glob("*.md"))
    assert conversations and "repulsors" in conversations[0].read_text()


def test_chat_can_skip_logging(app, client, tmp_path):
    app.extensions["brain"] = FakeBrain()
    client.post("/api/chat", json={"text": "off the record", "log": False})
    assert not list((tmp_path / "vault" / "JARVIS" / "Conversations").glob("*.md"))


def test_chat_rejects_empty_input(client):
    assert client.post("/api/chat", json={"text": "   "}).status_code == 400


def test_chat_keeps_history_between_turns(app, client):
    brain = FakeBrain()
    app.extensions["brain"] = brain
    client.post("/api/chat", json={"text": "first"})
    client.post("/api/chat", json={"text": "second"})
    _, history = brain.seen[1]
    assert [m["content"] for m in history] == ["first", "Calibrated and ready, sir."]


def test_reset_clears_history(app, client):
    brain = FakeBrain()
    app.extensions["brain"] = brain
    client.post("/api/chat", json={"text": "first"})
    client.post("/api/reset")
    client.post("/api/chat", json={"text": "second"})
    assert brain.seen[1][1] == []


def test_brain_failure_is_reported_not_crashed(app, client):
    from jarvis.brain import BrainError

    class Broken(FakeBrain):
        def respond(self, text, history=None):
            raise BrainError("Claude could not be reached: boom")

    app.extensions["brain"] = Broken()
    res = client.post("/api/chat", json={"text": "hello"})
    assert res.status_code == 502
    assert "boom" in res.get_json()["error"]


def test_speak_without_key_returns_502(client):
    res = client.post("/api/speak", json={"text": "hello"})
    assert res.status_code == 502
    assert "FISH_AUDIO_API_KEY" in res.get_json()["error"]


def test_memory_search_endpoint(app, client):
    app.extensions["memory"].remember("Mark VII", "Repulsor output up twelve percent.", "Projects")
    hits = client.get("/api/memory/search?q=repulsor").get_json()["hits"]
    assert hits and hits[0]["title"] == "Mark VII"


def test_memory_note_endpoint_refuses_escape(client):
    assert client.get("/api/memory/note?path=../../etc/passwd").status_code == 404


def test_healthz(client):
    assert client.get("/healthz").get_json() == {"ok": True}


# ---- unit level ---------------------------------------------------------
def test_tool_runner_search_and_remember(tmp_path):
    from jarvis.memory import ObsidianMemory

    mem = ObsidianMemory(tmp_path, "JARVIS")
    mem.ensure_vault()
    runner = ToolRunner(mem)

    out, err = runner.run("remember", {"subject": "Pepper", "fact": "Runs the company.", "category": "People"})
    assert not err and "Remembered" in out

    out, err = runner.run("search_memory", {"query": "runs the company"})
    assert not err and json.loads(out)[0]["title"] == "Pepper"

    out, err = runner.run("read_note", {"path": "JARVIS/Memory/People/Pepper.md"})
    assert not err and "Runs the company." in out


def test_tool_runner_reports_errors_to_the_model(tmp_path):
    from jarvis.memory import ObsidianMemory

    runner = ToolRunner(ObsidianMemory(tmp_path, "JARVIS"))
    out, err = runner.run("read_note", {"path": "../../etc/passwd"})
    assert err and out.startswith("Error")
    out, err = runner.run("nonexistent_tool", {})
    assert err


def test_speakable_strips_markdown_for_tts():
    spoken = speakable("## Status\n\n- **Repulsors** are `ready`\n\n```py\nx=1\n```\nSee [docs](http://x) 🚀")
    assert "**" not in spoken and "##" not in spoken and "`" not in spoken
    assert "🚀" not in spoken
    assert "docs" in spoken and "code omitted" in spoken


def test_trim_history_never_splits_a_tool_pair():
    history = []
    for i in range(30):
        history.append({"role": "user", "content": f"q{i}"})
        history.append({"role": "assistant", "content": f"a{i}"})
    trimmed = trim_history(history, 5)
    assert len(trimmed) == 10
    assert trimmed[0]["role"] == "user"


def test_trim_history_skips_tool_result_boundary():
    history = [
        {"role": "user", "content": "old"},
        {"role": "assistant", "content": "blocks"},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "x", "content": "r"}]},
        {"role": "assistant", "content": "done"},
        {"role": "user", "content": "new"},
        {"role": "assistant", "content": "reply"},
    ]
    trimmed = trim_history(history, 1)
    # Cut lands on a plain user message, never on the tool_result turn.
    assert all(isinstance(m["content"], str) or m["role"] == "assistant" for m in trimmed[:1])
    assert trimmed[0]["content"] == "new"
