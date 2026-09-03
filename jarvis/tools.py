"""The tools J.A.R.V.I.S. can call — all of them operate on the Obsidian vault."""

from __future__ import annotations

import json
from typing import Any

from .memory import MemoryError_, ObsidianMemory

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "search_memory",
        "description": (
            "Search the Obsidian vault for notes relevant to a query. Use this before "
            "answering anything about the user, their people, projects, plans, "
            "preferences, or past conversations. Returns ranked notes with excerpts; "
            "follow up with read_note when an excerpt looks promising."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Keywords or a natural-language question."},
                "limit": {"type": "integer", "description": "Max notes to return (default 6).", "minimum": 1, "maximum": 20},
                "folder": {"type": "string", "description": "Optional vault-relative folder to restrict the search to."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "read_note",
        "description": "Read the full markdown of one note, given its vault-relative path.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Vault-relative path, e.g. 'JARVIS/Memory/People/Pepper Potts.md'."}},
            "required": ["path"],
        },
    },
    {
        "name": "remember",
        "description": (
            "Store one durable fact in long-term memory. Use it whenever the user "
            "states a preference, decision, deadline, or fact about a person or "
            "project that should survive this conversation. One call per fact."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "subject": {"type": "string", "description": "Who or what this is about, e.g. 'Pepper Potts' or 'Mark VII'. Becomes the note name."},
                "fact": {"type": "string", "description": "The fact itself, one clean sentence written for a human to reread later."},
                "category": {
                    "type": "string",
                    "description": "Folder to file it under: People, Projects, Preferences, or Facts.",
                },
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Optional extra Obsidian tags."},
            },
            "required": ["subject", "fact"],
        },
    },
    {
        "name": "write_note",
        "description": (
            "Create or update an arbitrary note in the vault. Use for longer material "
            "than a single fact — meeting notes, a plan, a draft. Prefer 'remember' "
            "for one-line facts."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Vault-relative path ending in .md."},
                "content": {"type": "string", "description": "Markdown to write."},
                "mode": {"type": "string", "enum": ["append", "prepend", "overwrite"], "description": "Default append."},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "forget",
        "description": (
            "Remove lines containing a phrase from a note — used to correct memory "
            "that has gone stale. Follow with 'remember' to store the new version."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Vault-relative path of the note to edit."},
                "matching": {"type": "string", "description": "Text identifying the lines to remove. Be specific."},
            },
            "required": ["path", "matching"],
        },
    },
    {
        "name": "add_daily_note",
        "description": "Append a timestamped line to today's daily note — reminders, log entries, things noticed.",
        "input_schema": {
            "type": "object",
            "properties": {"content": {"type": "string", "description": "The line to add."}},
            "required": ["content"],
        },
    },
    {
        "name": "list_recent_notes",
        "description": "List the most recently modified notes in the vault. Useful for 'what was I working on'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": 30},
                "folder": {"type": "string", "description": "Optional vault-relative folder."},
            },
        },
    },
]


class ToolRunner:
    """Executes tool calls from Claude against the vault."""

    def __init__(self, memory: ObsidianMemory):
        self.memory = memory
        self.calls: list[dict[str, Any]] = []

    def run(self, name: str, payload: dict[str, Any]) -> tuple[str, bool]:
        """Return (result_text, is_error)."""
        try:
            result = self._dispatch(name, payload or {})
            self.calls.append({"tool": name, "input": payload, "ok": True})
            return result, False
        except MemoryError_ as exc:
            self.calls.append({"tool": name, "input": payload, "ok": False, "error": str(exc)})
            return f"Error: {exc}", True
        except Exception as exc:  # noqa: BLE001 - surface anything back to the model
            self.calls.append({"tool": name, "input": payload, "ok": False, "error": str(exc)})
            return f"Error running {name}: {exc}", True

    def _dispatch(self, name: str, p: dict[str, Any]) -> str:
        if name == "search_memory":
            hits = self.memory.search(p["query"], int(p.get("limit", 6) or 6), p.get("folder", ""))
            if not hits:
                return "No matching notes in the vault."
            return json.dumps([h.to_dict() for h in hits], ensure_ascii=False, indent=1)

        if name == "read_note":
            text = self.memory.read_note(p["path"])
            return text[:20000] if len(text) > 20000 else text

        if name == "remember":
            path = self.memory.remember(
                subject=p["subject"],
                fact=p["fact"],
                category=p.get("category") or "Facts",
                tags=p.get("tags") or [],
            )
            return f"Remembered in {path}"

        if name == "write_note":
            path = self.memory.write_note(
                p["path"], p["content"], p.get("mode", "append"), p.get("tags") or []
            )
            return f"Wrote {path}"

        if name == "forget":
            removed = self.memory.forget(p["path"], p["matching"])
            return f"Removed {removed} line(s) from {p['path']}." if removed else "Nothing matched; note unchanged."

        if name == "add_daily_note":
            return f"Added to {self.memory.daily_note(p['content'])}"

        if name == "list_recent_notes":
            hits = self.memory.recent(int(p.get("limit", 10) or 10), p.get("folder", ""))
            if not hits:
                return "The vault is empty."
            return json.dumps([h.to_dict() for h in hits], ensure_ascii=False, indent=1)

        raise MemoryError_(f"Unknown tool '{name}'.")
