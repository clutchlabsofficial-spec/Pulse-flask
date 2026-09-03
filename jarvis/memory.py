"""Obsidian-backed long term memory.

The vault *is* the database. Every fact J.A.R.V.I.S. learns becomes a plain
markdown note with YAML frontmatter, so it stays readable, greppable, syncable
and editable by hand inside Obsidian. Nothing is locked in a binary store.

Layout created inside the vault (under ``JARVIS/`` by default)::

    JARVIS/
      Core.md                      # always-loaded profile / standing orders
      Memory/
        People/Pepper Potts.md
        Projects/Mark VII.md
        Preferences/Coffee.md
      Conversations/2026-09-03.md  # transcript log, one note per day
      Daily/2026-09-03.md          # scratch notes for the day
"""

from __future__ import annotations

import datetime as dt
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

SKIP_DIRS = {".obsidian", ".trash", ".git", "node_modules", ".smart-env", ".space"}
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
WORD_RE = re.compile(r"[a-z0-9][a-z0-9'_-]*")
STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for", "with",
    "is", "are", "was", "were", "be", "been", "it", "that", "this", "what",
    "who", "when", "where", "how", "do", "does", "did", "my", "me", "i", "you",
    "about", "from", "as", "at", "by", "so", "if", "then", "than", "we", "us",
}


def slugify(text: str) -> str:
    """Turn an arbitrary subject into a safe, human-readable note filename."""
    cleaned = re.sub(r"[^\w\s.-]", "", text, flags=re.UNICODE).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return (cleaned or "Untitled")[:120]


def tokenize(text: str) -> list[str]:
    return [w for w in WORD_RE.findall(text.lower()) if w not in STOPWORDS and len(w) > 1]


@dataclass
class SearchHit:
    path: str
    title: str
    score: float
    excerpt: str
    modified: str

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "title": self.title,
            "score": round(self.score, 3),
            "excerpt": self.excerpt,
            "modified": self.modified,
        }


class MemoryError_(Exception):
    """Raised for anything the caller (or Claude) did wrong, not the disk."""


class ObsidianMemory:
    """Read/write access to an Obsidian vault, scoped and path-safe."""

    def __init__(self, vault_path: Path, subfolder: str = "JARVIS", max_files: int = 20000):
        self.vault = Path(vault_path).expanduser()
        self.subfolder = subfolder.strip("/")
        self.max_files = max_files
        self._lock = threading.Lock()
        self._cache: dict[Path, tuple[float, str]] = {}

    # -- setup -----------------------------------------------------------
    def ensure_vault(self) -> None:
        """Create the vault scaffolding if it is not there yet."""
        for folder in (
            self.root,
            self.root / "Memory",
            self.root / "Memory" / "People",
            self.root / "Memory" / "Projects",
            self.root / "Memory" / "Preferences",
            self.root / "Conversations",
            self.root / "Daily",
        ):
            folder.mkdir(parents=True, exist_ok=True)
        core = self.root / "Core.md"
        if not core.exists():
            core.write_text(
                "---\ntags: [jarvis, core]\n---\n\n"
                "# Core Memory\n\n"
                "This note is loaded into J.A.R.V.I.S.'s context on every single "
                "exchange. Keep it short and high value: who you are, standing "
                "orders, and things that must never be forgotten.\n\n"
                "## About me\n- \n\n## Standing orders\n- \n\n## Current focus\n- \n",
                encoding="utf-8",
            )

    @property
    def root(self) -> Path:
        return self.vault / self.subfolder if self.subfolder else self.vault

    @property
    def available(self) -> bool:
        return self.vault.is_dir()

    # -- path safety ------------------------------------------------------
    def resolve(self, relative: str) -> Path:
        """Resolve a vault-relative path, refusing anything outside the vault."""
        if not relative or not relative.strip():
            raise MemoryError_("A note path is required.")
        candidate = (self.vault / relative.strip().lstrip("/")).expanduser()
        if candidate.suffix.lower() != ".md":
            candidate = candidate.with_suffix(".md")
        vault_real = self.vault.resolve()
        try:
            resolved = candidate.resolve()
        except OSError as exc:  # pragma: no cover - filesystem edge case
            raise MemoryError_(f"Cannot resolve path: {exc}") from exc
        if resolved != vault_real and vault_real not in resolved.parents:
            raise MemoryError_(f"Refusing to touch '{relative}': outside the vault.")
        return resolved

    def relative(self, path: Path) -> str:
        try:
            return str(path.resolve().relative_to(self.vault.resolve()))
        except ValueError:
            return str(path)

    # -- reading ----------------------------------------------------------
    def iter_notes(self, folder: str = "") -> Iterable[Path]:
        base = self.resolve_folder(folder)
        if not base.is_dir():
            return []
        found = 0
        for path in sorted(base.rglob("*.md")):
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            found += 1
            if found > self.max_files:
                break
            yield path

    def resolve_folder(self, folder: str) -> Path:
        if not folder:
            return self.vault
        candidate = (self.vault / folder.strip().lstrip("/")).expanduser()
        vault_real = self.vault.resolve()
        resolved = candidate.resolve()
        if resolved != vault_real and vault_real not in resolved.parents:
            raise MemoryError_(f"Refusing to list '{folder}': outside the vault.")
        return resolved

    def _read_cached(self, path: Path) -> str:
        """Read a note, caching on mtime so repeated searches stay cheap."""
        try:
            mtime = path.stat().st_mtime
        except OSError:
            return ""
        with self._lock:
            cached = self._cache.get(path)
            if cached and cached[0] == mtime:
                return cached[1]
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""
        with self._lock:
            if len(self._cache) > self.max_files:
                self._cache.clear()
            self._cache[path] = (mtime, text)
        return text

    def read_note(self, relative: str) -> str:
        path = self.resolve(relative)
        if not path.is_file():
            raise MemoryError_(f"No note at '{relative}'.")
        return path.read_text(encoding="utf-8", errors="replace")

    def core_memory(self) -> str:
        core = self.root / "Core.md"
        if core.is_file():
            return strip_frontmatter(core.read_text(encoding="utf-8", errors="replace")).strip()
        return ""

    # -- searching --------------------------------------------------------
    def search(self, query: str, limit: int = 6, folder: str = "") -> list[SearchHit]:
        """Rank notes against a query with a small TF + title/tag heuristic."""
        terms = tokenize(query)
        if not terms:
            return []
        phrase = query.strip().lower()
        hits: list[SearchHit] = []
        for path in self.iter_notes(folder):
            text = self._read_cached(path)
            if not text:
                continue
            lowered = text.lower()
            title = path.stem
            title_lower = title.lower()
            score = 0.0
            matched = 0
            for term in terms:
                count = lowered.count(term)
                if count:
                    matched += 1
                    score += 1.0 + min(count, 8) * 0.25
                if term in title_lower:
                    score += 3.0
            if not matched:
                continue
            # Reward notes that match most of the query, not just one word.
            score *= 0.5 + 0.5 * (matched / len(terms))
            if len(phrase) > 3 and phrase in lowered:
                score += 4.0
            if self.subfolder and self.subfolder in path.parts:
                score += 0.75  # J.A.R.V.I.S.'s own memory outranks stray notes
            hits.append(
                SearchHit(
                    path=self.relative(path),
                    title=title,
                    score=score,
                    excerpt=excerpt_for(text, terms),
                    modified=dt.datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                )
            )
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[: max(1, limit)]

    def recent(self, limit: int = 10, folder: str = "") -> list[SearchHit]:
        notes = list(self.iter_notes(folder))
        notes.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        out = []
        for path in notes[: max(1, limit)]:
            text = self._read_cached(path)
            out.append(
                SearchHit(
                    path=self.relative(path),
                    title=path.stem,
                    score=0.0,
                    excerpt=strip_frontmatter(text).strip()[:240],
                    modified=dt.datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                )
            )
        return out

    # -- writing ----------------------------------------------------------
    def write_note(self, relative: str, content: str, mode: str = "append", tags: list[str] | None = None) -> str:
        if mode not in {"append", "overwrite", "prepend"}:
            raise MemoryError_("mode must be one of: append, overwrite, prepend")
        path = self.resolve(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        now = dt.datetime.now()
        if not path.exists() or mode == "overwrite":
            header = frontmatter(created=now, tags=tags or ["jarvis"])
            body = f"{header}\n# {path.stem}\n\n{content.rstrip()}\n"
            path.write_text(body, encoding="utf-8")
        else:
            existing = path.read_text(encoding="utf-8", errors="replace").rstrip()
            if mode == "append":
                body = f"{existing}\n\n{content.rstrip()}\n"
            else:
                match = FRONTMATTER_RE.match(existing)
                if match:
                    head = existing[: match.end()]
                    rest = existing[match.end():].lstrip("\n")
                    body = f"{head}\n{content.rstrip()}\n\n{rest}\n"
                else:
                    body = f"{content.rstrip()}\n\n{existing}\n"
            path.write_text(body, encoding="utf-8")
        return self.relative(path)

    def remember(self, subject: str, fact: str, category: str = "Facts", tags: list[str] | None = None) -> str:
        """Store one durable fact under ``JARVIS/Memory/<category>/<subject>.md``."""
        if not fact.strip():
            raise MemoryError_("Nothing to remember: 'fact' was empty.")
        category = slugify(category or "Facts")
        subject = slugify(subject or "General")
        rel = f"{self.subfolder}/Memory/{category}/{subject}.md" if self.subfolder else f"Memory/{category}/{subject}.md"
        stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"- {fact.strip()} ^{dt.datetime.now().strftime('%Y%m%d%H%M%S')}\n  <!-- learned {stamp} -->"
        return self.write_note(rel, entry, mode="append", tags=(tags or []) + ["jarvis", "memory"])

    def forget(self, relative: str, matching: str) -> int:
        """Remove lines from a note that contain ``matching``. Returns count."""
        path = self.resolve(relative)
        if not path.is_file():
            raise MemoryError_(f"No note at '{relative}'.")
        needle = matching.strip().lower()
        if not needle:
            raise MemoryError_("'matching' is required so we don't wipe a whole note.")
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        kept = [line for line in lines if needle not in line.lower()]
        removed = len(lines) - len(kept)
        if removed:
            path.write_text("\n".join(kept) + "\n", encoding="utf-8")
        return removed

    def log_exchange(self, user_text: str, assistant_text: str) -> str:
        """Append one turn to today's conversation note."""
        today = dt.date.today().isoformat()
        rel = f"{self.subfolder}/Conversations/{today}.md" if self.subfolder else f"Conversations/{today}.md"
        stamp = dt.datetime.now().strftime("%H:%M")
        entry = (
            f"### {stamp}\n\n"
            f"**You:** {user_text.strip()}\n\n"
            f"**J.A.R.V.I.S.:** {assistant_text.strip()}"
        )
        return self.write_note(rel, entry, mode="append", tags=["jarvis", "conversation"])

    def daily_note(self, content: str) -> str:
        today = dt.date.today().isoformat()
        rel = f"{self.subfolder}/Daily/{today}.md" if self.subfolder else f"Daily/{today}.md"
        stamp = dt.datetime.now().strftime("%H:%M")
        return self.write_note(rel, f"- {stamp} — {content.strip()}", mode="append", tags=["jarvis", "daily"])

    def stats(self) -> dict:
        if not self.available:
            return {"available": False, "vault": str(self.vault), "notes": 0}
        notes = list(self.iter_notes())
        return {
            "available": True,
            "vault": str(self.vault),
            "memory_root": str(self.root),
            "notes": len(notes),
            "memory_notes": len(list(self.iter_notes(f"{self.subfolder}/Memory"))) if self.subfolder else 0,
        }


# -- helpers --------------------------------------------------------------
def frontmatter(created: dt.datetime, tags: list[str]) -> str:
    unique = sorted({t.strip() for t in tags if t and t.strip()})
    tag_line = ", ".join(unique)
    return f"---\ncreated: {created.strftime('%Y-%m-%d %H:%M')}\ntags: [{tag_line}]\n---\n"


def strip_frontmatter(text: str) -> str:
    return FRONTMATTER_RE.sub("", text, count=1)


def excerpt_for(text: str, terms: list[str], width: int = 260) -> str:
    """Pull the most relevant window of the note around a matching term."""
    body = strip_frontmatter(text)
    lowered = body.lower()
    position = -1
    for term in terms:
        position = lowered.find(term)
        if position != -1:
            break
    if position == -1:
        return body.strip()[:width]
    start = max(0, position - width // 3)
    snippet = body[start : start + width].strip().replace("\n\n", "\n")
    prefix = "…" if start > 0 else ""
    suffix = "…" if start + width < len(body) else ""
    return f"{prefix}{snippet}{suffix}"
