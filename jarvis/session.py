"""In-memory conversation store.

Transcripts live in the Obsidian vault; this only holds the working context
for the current session so Claude keeps its train of thought between turns.
"""

from __future__ import annotations

import threading
import time
import uuid

from .brain import trim_history

SESSION_TTL_SECONDS = 12 * 60 * 60
MAX_SESSIONS = 200


class ConversationStore:
    def __init__(self, max_turns: int = 20):
        self.max_turns = max_turns
        self._lock = threading.Lock()
        self._data: dict[str, dict] = {}

    def new_id(self) -> str:
        return uuid.uuid4().hex

    def get(self, session_id: str) -> list[dict]:
        with self._lock:
            entry = self._data.get(session_id)
            if not entry:
                return []
            entry["seen"] = time.time()
            return list(entry["messages"])

    def set(self, session_id: str, messages: list[dict]) -> None:
        with self._lock:
            self._prune_locked()
            self._data[session_id] = {
                "messages": trim_history(messages, self.max_turns),
                "seen": time.time(),
            }

    def clear(self, session_id: str) -> None:
        with self._lock:
            self._data.pop(session_id, None)

    def _prune_locked(self) -> None:
        now = time.time()
        stale = [k for k, v in self._data.items() if now - v["seen"] > SESSION_TTL_SECONDS]
        for key in stale:
            self._data.pop(key, None)
        if len(self._data) > MAX_SESSIONS:
            oldest = sorted(self._data.items(), key=lambda kv: kv[1]["seen"])
            for key, _ in oldest[: len(self._data) - MAX_SESSIONS]:
                self._data.pop(key, None)
