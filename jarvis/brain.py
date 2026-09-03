"""Claude as the brain: the reasoning + tool-use loop."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from .config import Config
from .memory import ObsidianMemory
from .persona import build_system_prompt
from .tools import TOOL_SCHEMAS, ToolRunner

log = logging.getLogger("jarvis.brain")

MAX_TOOL_ROUNDS = 8


class BrainError(Exception):
    pass


@dataclass
class Reply:
    text: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=dict)
    model: str = ""

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "tool_calls": self.tool_calls,
            "usage": self.usage,
            "model": self.model,
        }


class Brain:
    """Wraps the Anthropic client and runs the agentic loop over vault tools."""

    def __init__(self, config: Config, memory: ObsidianMemory):
        self.config = config
        self.memory = memory
        self._client = None

    @property
    def client(self):
        if self._client is None:
            if not self.config.anthropic_api_key:
                raise BrainError(
                    "ANTHROPIC_API_KEY is not set — J.A.R.V.I.S. has no brain to think with."
                )
            try:
                from anthropic import Anthropic
            except ImportError as exc:  # pragma: no cover
                raise BrainError("The 'anthropic' package is not installed.") from exc
            self._client = Anthropic(api_key=self.config.anthropic_api_key)
        return self._client

    @property
    def ready(self) -> bool:
        return bool(self.config.anthropic_api_key)

    def system_prompt(self) -> str:
        core = self.memory.core_memory() if self.memory.available else ""
        return build_system_prompt(
            assistant_name=self.config.assistant_name,
            user_name=self.config.user_name,
            core_memory=core,
            persona_file=self.config.persona_file,
        )

    def respond(self, user_text: str, history: list[dict] | None = None) -> Reply:
        """Send one user turn through Claude, running vault tools until it settles."""
        if not user_text.strip():
            raise BrainError("Nothing was said.")

        runner = ToolRunner(self.memory)
        messages: list[dict[str, Any]] = list(history or [])
        messages.append({"role": "user", "content": user_text})

        usage = {"input_tokens": 0, "output_tokens": 0}
        final_text = ""

        for _ in range(MAX_TOOL_ROUNDS):
            response = self._create(messages)
            usage["input_tokens"] += getattr(response.usage, "input_tokens", 0) or 0
            usage["output_tokens"] += getattr(response.usage, "output_tokens", 0) or 0

            messages.append({"role": "assistant", "content": response.content})
            tool_uses = [b for b in response.content if getattr(b, "type", "") == "tool_use"]
            text_blocks = [b.text for b in response.content if getattr(b, "type", "") == "text"]
            if text_blocks:
                final_text = "\n\n".join(t.strip() for t in text_blocks if t.strip())

            if not tool_uses:
                break

            results = []
            for block in tool_uses:
                log.info("tool %s %s", block.name, block.input)
                output, is_error = runner.run(block.name, dict(block.input or {}))
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": output,
                        "is_error": is_error,
                    }
                )
            messages.append({"role": "user", "content": results})
        else:
            log.warning("hit MAX_TOOL_ROUNDS without a final answer")
            if not final_text:
                final_text = "I got tangled up searching the vault, sir. Could you rephrase that?"

        return Reply(
            text=final_text.strip() or "…",
            tool_calls=runner.calls,
            usage=usage,
            model=self.config.model,
        )

    def _create(self, messages: list[dict]):
        kwargs: dict[str, Any] = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "system": self.system_prompt(),
            "messages": messages,
            "tools": TOOL_SCHEMAS,
        }
        if self.config.thinking_budget > 0:
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": self.config.thinking_budget}
            # Extended thinking requires headroom above the thinking budget.
            kwargs["max_tokens"] = max(self.config.max_tokens, self.config.thinking_budget + 1024)
        client = self.client  # raises BrainError with its own message
        try:
            return client.messages.create(**kwargs)
        except Exception as exc:  # noqa: BLE001 - the API surface is broad
            raise BrainError(f"Claude could not be reached: {exc}") from exc


def trim_history(history: list[dict], max_turns: int) -> list[dict]:
    """Keep the last N user/assistant turns, never splitting a tool_use pair.

    A tool_use block must always be followed by its tool_result, so we only ever
    cut at a plain-text user message.
    """
    if len(history) <= max_turns * 2:
        return history
    cut = len(history) - max_turns * 2
    while cut < len(history):
        msg = history[cut]
        if msg.get("role") == "user" and isinstance(msg.get("content"), str):
            return history[cut:]
        cut += 1
    return []
