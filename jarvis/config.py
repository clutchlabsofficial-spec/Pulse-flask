"""Configuration for J.A.R.V.I.S.

Everything is driven by environment variables so the same code runs on a
laptop, a Raspberry Pi in the workshop, or a server.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


@dataclass
class Config:
    # --- Brain (Claude) ---------------------------------------------------
    anthropic_api_key: str = ""
    model: str = "claude-opus-5"
    max_tokens: int = 2048
    thinking_budget: int = 0  # 0 disables extended thinking

    # --- Memory (Obsidian vault) -----------------------------------------
    vault_path: Path = field(default_factory=lambda: Path.home() / "Obsidian" / "Vault")
    vault_subfolder: str = "JARVIS"
    max_memory_files: int = 20000

    # --- Voice (Fish Audio) ----------------------------------------------
    fish_api_key: str = ""
    fish_voice_id: str = ""  # reference_id of your J.A.R.V.I.S. voice model
    fish_model: str = "s1"
    fish_format: str = "mp3"
    fish_base_url: str = "https://api.fish.audio"
    speech_enabled: bool = True

    # --- Persona ----------------------------------------------------------
    user_name: str = "Sir"
    assistant_name: str = "J.A.R.V.I.S."
    persona_file: str = ""  # optional path to a custom system prompt

    # --- Server -----------------------------------------------------------
    host: str = "127.0.0.1"
    port: int = 5000
    debug: bool = False
    history_turns: int = 20

    @classmethod
    def from_env(cls) -> "Config":
        home_vault = Path.home() / "Obsidian" / "Vault"
        return cls(
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
            model=os.environ.get("JARVIS_MODEL", "claude-opus-5"),
            max_tokens=_int("JARVIS_MAX_TOKENS", 2048),
            thinking_budget=_int("JARVIS_THINKING_BUDGET", 0),
            vault_path=Path(os.environ.get("OBSIDIAN_VAULT_PATH", str(home_vault))).expanduser(),
            vault_subfolder=os.environ.get("OBSIDIAN_SUBFOLDER", "JARVIS"),
            max_memory_files=_int("JARVIS_MAX_MEMORY_FILES", 20000),
            fish_api_key=os.environ.get("FISH_AUDIO_API_KEY", ""),
            fish_voice_id=os.environ.get("FISH_AUDIO_VOICE_ID", ""),
            fish_model=os.environ.get("FISH_AUDIO_MODEL", "s1"),
            fish_format=os.environ.get("FISH_AUDIO_FORMAT", "mp3"),
            fish_base_url=os.environ.get("FISH_AUDIO_BASE_URL", "https://api.fish.audio"),
            speech_enabled=_bool("JARVIS_SPEECH_ENABLED", True),
            user_name=os.environ.get("JARVIS_USER_NAME", "Sir"),
            assistant_name=os.environ.get("JARVIS_NAME", "J.A.R.V.I.S."),
            persona_file=os.environ.get("JARVIS_PERSONA_FILE", ""),
            host=os.environ.get("JARVIS_HOST", "127.0.0.1"),
            port=_int("JARVIS_PORT", 5000),
            debug=_bool("JARVIS_DEBUG", False),
            history_turns=_int("JARVIS_HISTORY_TURNS", 20),
        )

    @property
    def memory_root(self) -> Path:
        """Where J.A.R.V.I.S. keeps its own notes inside the vault."""
        if self.vault_subfolder:
            return self.vault_path / self.vault_subfolder
        return self.vault_path
