"""J.A.R.V.I.S. — Just A Rather Very Intelligent System.

Claude for reasoning, an Obsidian vault for memory, Fish Audio for the voice,
and Wispr Flow for dictation.
"""

from __future__ import annotations

import logging
import os

from flask import Flask

from .config import Config
from .memory import ObsidianMemory
from .session import ConversationStore

__version__ = "1.0.0"


def create_app(config: Config | None = None) -> Flask:
    try:  # optional, but convenient for local runs
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:  # pragma: no cover
        pass

    cfg = config or Config.from_env()
    logging.basicConfig(
        level=logging.DEBUG if cfg.debug else logging.INFO,
        format="%(asctime)s  %(name)-14s %(levelname)-7s %(message)s",
    )

    app = Flask(__name__)
    app.config["JARVIS"] = cfg
    app.secret_key = os.environ.get("JARVIS_SECRET_KEY", os.urandom(32).hex())

    memory = ObsidianMemory(cfg.vault_path, cfg.vault_subfolder, cfg.max_memory_files)
    if memory.available:
        memory.ensure_vault()
    else:
        logging.getLogger("jarvis").warning(
            "Obsidian vault not found at %s — memory tools will fail until "
            "OBSIDIAN_VAULT_PATH points at a real vault.",
            cfg.vault_path,
        )

    from .brain import Brain
    from .voice import FishVoice

    app.extensions["memory"] = memory
    app.extensions["brain"] = Brain(cfg, memory)
    app.extensions["voice"] = FishVoice(
        api_key=cfg.fish_api_key,
        voice_id=cfg.fish_voice_id,
        model=cfg.fish_model,
        audio_format=cfg.fish_format,
        base_url=cfg.fish_base_url,
    )
    app.extensions["conversations"] = ConversationStore(cfg.history_turns)

    from .routes import bp

    app.register_blueprint(bp)
    return app
