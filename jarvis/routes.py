"""HTTP surface: the web console, the chat endpoint, and the speech endpoint."""

from __future__ import annotations

import datetime as dt
import logging

from flask import Blueprint, Response, current_app, jsonify, render_template, request, session

from .brain import BrainError
from .memory import MemoryError_
from .voice import VoiceError, speakable

log = logging.getLogger("jarvis.routes")
bp = Blueprint("jarvis", __name__)


def cfg():
    return current_app.config["JARVIS"]


def _session_id() -> str:
    store = current_app.extensions["conversations"]
    if "sid" not in session:
        session["sid"] = store.new_id()
    return session["sid"]


def _greeting() -> str:
    hour = dt.datetime.now().hour
    if hour < 12:
        return "morning"
    return "afternoon" if hour < 18 else "evening"


@bp.get("/")
def index():
    c = cfg()
    return render_template(
        "index.html",
        assistant_name=c.assistant_name,
        user_name=c.user_name,
        speech_enabled=c.speech_enabled,
        greeting=_greeting(),
    )


@bp.get("/api/status")
def status():
    c = cfg()
    memory = current_app.extensions["memory"]
    voice = current_app.extensions["voice"]
    brain = current_app.extensions["brain"]
    return jsonify(
        {
            "assistant": c.assistant_name,
            "user": c.user_name,
            "brain": {"ready": brain.ready, "model": c.model},
            "memory": memory.stats(),
            "voice": {"ready": voice.ready, "voice_id": bool(c.fish_voice_id), "model": c.fish_model},
            "speech_enabled": c.speech_enabled,
        }
    )


@bp.post("/api/chat")
def chat():
    """One turn: dictation (or typing) in, J.A.R.V.I.S.'s reply out."""
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Nothing was said."}), 400

    brain = current_app.extensions["brain"]
    memory = current_app.extensions["memory"]
    store = current_app.extensions["conversations"]
    sid = _session_id()

    history = store.get(sid)
    try:
        reply = brain.respond(text, history)
    except BrainError as exc:
        log.error("brain failure: %s", exc)
        return jsonify({"error": str(exc)}), 502

    history.append({"role": "user", "content": text})
    history.append({"role": "assistant", "content": reply.text})
    store.set(sid, history)

    logged = None
    if memory.available and data.get("log", True):
        try:
            logged = memory.log_exchange(text, reply.text)
        except (MemoryError_, OSError) as exc:  # a logging failure must not eat the reply
            log.warning("could not log exchange: %s", exc)

    payload = reply.to_dict()
    payload["source"] = data.get("source", "text")
    payload["logged_to"] = logged
    payload["speakable"] = speakable(reply.text)
    return jsonify(payload)


@bp.post("/api/speak")
def speak():
    """Render text as J.A.R.V.I.S.'s Fish Audio voice."""
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Nothing to say."}), 400
    voice = current_app.extensions["voice"]
    try:
        audio = voice.synthesize(text)
    except VoiceError as exc:
        log.error("voice failure: %s", exc)
        return jsonify({"error": str(exc)}), 502
    return Response(
        audio,
        mimetype=voice.mimetype,
        headers={"Cache-Control": "private, max-age=3600", "Content-Length": str(len(audio))},
    )


@bp.get("/api/voices")
def voices():
    """List the Fish Audio voice models on the account, to find a reference_id."""
    try:
        return jsonify({"voices": current_app.extensions["voice"].list_voices()})
    except VoiceError as exc:
        return jsonify({"error": str(exc)}), 502


@bp.get("/api/memory/search")
def memory_search():
    query = (request.args.get("q") or "").strip()
    if not query:
        return jsonify({"error": "Pass ?q="}), 400
    memory = current_app.extensions["memory"]
    try:
        limit = min(int(request.args.get("limit", 8)), 25)
        hits = memory.search(query, limit)
    except (MemoryError_, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"query": query, "hits": [h.to_dict() for h in hits]})


@bp.get("/api/memory/note")
def memory_note():
    path = (request.args.get("path") or "").strip()
    memory = current_app.extensions["memory"]
    try:
        return jsonify({"path": path, "content": memory.read_note(path)})
    except MemoryError_ as exc:
        return jsonify({"error": str(exc)}), 404


@bp.post("/api/reset")
def reset():
    """Forget the working context. The vault keeps everything that matters."""
    current_app.extensions["conversations"].clear(_session_id())
    session.pop("sid", None)
    return jsonify({"ok": True})


@bp.get("/healthz")
def healthz():
    return jsonify({"ok": True})
