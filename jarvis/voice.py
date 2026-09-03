"""Fish Audio text-to-speech — the voice J.A.R.V.I.S. speaks with.

Point ``FISH_AUDIO_VOICE_ID`` at a voice model you own or have cloned on
fish.audio and every reply comes back in that voice.
"""

from __future__ import annotations

import hashlib
import logging
import re
import threading
from pathlib import Path

import requests

log = logging.getLogger("jarvis.voice")

CODE_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`([^`]*)`")
LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
EMPHASIS_RE = re.compile(r"(\*\*|__|\*|_|~~)")
HEADING_RE = re.compile(r"^#{1,6}\s*", re.MULTILINE)
BULLET_RE = re.compile(r"^\s*[-*+]\s+", re.MULTILINE)
EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF←-⇿⬀-⯿]"
)
MAX_TTS_CHARS = 4000


class VoiceError(Exception):
    pass


def speakable(text: str) -> str:
    """Strip markdown noise so the TTS reads prose, not punctuation."""
    out = CODE_BLOCK_RE.sub(" (code omitted) ", text)
    out = INLINE_CODE_RE.sub(r"\1", out)
    out = LINK_RE.sub(r"\1", out)
    out = WIKILINK_RE.sub(lambda m: m.group(2) or m.group(1), out)
    out = HEADING_RE.sub("", out)
    out = BULLET_RE.sub("", out)
    out = EMPHASIS_RE.sub("", out)
    out = EMOJI_RE.sub("", out)
    out = re.sub(r"\n{2,}", ". ", out)
    out = re.sub(r"[ \t]+", " ", out).strip()
    if len(out) > MAX_TTS_CHARS:
        cut = out.rfind(". ", 0, MAX_TTS_CHARS)
        out = out[: cut + 1] if cut > MAX_TTS_CHARS // 2 else out[:MAX_TTS_CHARS]
    return out


class FishVoice:
    """Thin, cached client for the Fish Audio TTS endpoint."""

    def __init__(
        self,
        api_key: str,
        voice_id: str = "",
        model: str = "s1",
        audio_format: str = "mp3",
        base_url: str = "https://api.fish.audio",
        cache_dir: Path | None = None,
    ):
        self.api_key = api_key
        self.voice_id = voice_id
        self.model = model
        self.format = audio_format
        self.base_url = base_url.rstrip("/")
        self.cache_dir = cache_dir or (Path.home() / ".cache" / "jarvis" / "tts")
        self._lock = threading.Lock()

    @property
    def ready(self) -> bool:
        return bool(self.api_key)

    @property
    def mimetype(self) -> str:
        return {"mp3": "audio/mpeg", "wav": "audio/wav", "opus": "audio/ogg", "pcm": "audio/pcm"}.get(
            self.format, "audio/mpeg"
        )

    def _cache_key(self, text: str) -> Path:
        digest = hashlib.sha256(
            f"{self.model}|{self.voice_id}|{self.format}|{text}".encode("utf-8")
        ).hexdigest()[:32]
        return self.cache_dir / f"{digest}.{self.format}"

    def synthesize(self, text: str, use_cache: bool = True) -> bytes:
        """Return audio bytes for ``text``. Repeated lines come from disk cache."""
        if not self.ready:
            raise VoiceError("FISH_AUDIO_API_KEY is not set — J.A.R.V.I.S. has no voice.")
        clean = speakable(text)
        if not clean:
            raise VoiceError("Nothing to say.")

        cache_path = self._cache_key(clean)
        if use_cache and cache_path.is_file():
            return cache_path.read_bytes()

        payload = {
            "text": clean,
            "format": self.format,
            "normalize": True,
            "latency": "normal",
        }
        if self.voice_id:
            payload["reference_id"] = self.voice_id
        if self.format == "mp3":
            payload["mp3_bitrate"] = 128

        try:
            response = requests.post(
                f"{self.base_url}/v1/tts",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "model": self.model,
                },
                timeout=90,
            )
        except requests.RequestException as exc:
            raise VoiceError(f"Fish Audio unreachable: {exc}") from exc

        if response.status_code != 200:
            detail = response.text[:300].strip()
            raise VoiceError(f"Fish Audio returned {response.status_code}: {detail}")
        audio = response.content
        if not audio:
            raise VoiceError("Fish Audio returned an empty response.")

        if use_cache:
            with self._lock:
                try:
                    self.cache_dir.mkdir(parents=True, exist_ok=True)
                    cache_path.write_bytes(audio)
                except OSError as exc:  # cache failure must never break speech
                    log.warning("could not cache speech: %s", exc)
        return audio

    def list_voices(self) -> list[dict]:
        """List the voice models on the account, so you can find J.A.R.V.I.S.'s id."""
        if not self.ready:
            raise VoiceError("FISH_AUDIO_API_KEY is not set.")
        try:
            response = requests.get(
                f"{self.base_url}/model",
                params={"page_size": 50, "self": "true"},
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=30,
            )
        except requests.RequestException as exc:
            raise VoiceError(f"Fish Audio unreachable: {exc}") from exc
        if response.status_code != 200:
            raise VoiceError(f"Fish Audio returned {response.status_code}: {response.text[:200]}")
        data = response.json()
        items = data.get("items", data if isinstance(data, list) else [])
        return [
            {"id": i.get("_id") or i.get("id"), "title": i.get("title"), "languages": i.get("languages")}
            for i in items
        ]
