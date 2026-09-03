#!/usr/bin/env python3
"""Terminal client for J.A.R.V.I.S. — the hands-free path.

Wispr Flow dictates into whatever has focus, including a terminal. Run this,
hold your Wispr Flow hotkey, speak, press Enter, and J.A.R.V.I.S. answers out
loud through Fish Audio.

    python bridge/jarvis_cli.py                 # talk to a running server
    python bridge/jarvis_cli.py --no-speech     # text only

Requires the server to be running (python run.py).
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import requests

CYAN = "\033[38;5;81m"
GOLD = "\033[38;5;221m"
DIM = "\033[2m"
RESET = "\033[0m"


def find_player() -> list[str] | None:
    """Pick whatever audio player this machine actually has."""
    for cmd, args in (
        ("afplay", []),                       # macOS
        ("mpv", ["--no-video", "--really-quiet"]),
        ("ffplay", ["-nodisp", "-autoexit", "-loglevel", "quiet"]),
        ("paplay", []),                       # Linux/PulseAudio
        ("aplay", []),
    ):
        if shutil.which(cmd):
            return [cmd, *args]
    return None


def play(audio: bytes, player: list[str]) -> None:
    suffix = ".wav" if player[0] in {"aplay", "paplay"} else ".mp3"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
        handle.write(audio)
        path = Path(handle.name)
    try:
        subprocess.run([*player, str(path)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    finally:
        path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Talk to J.A.R.V.I.S. from the terminal.")
    parser.add_argument("--server", default="http://127.0.0.1:5000", help="J.A.R.V.I.S. server URL")
    parser.add_argument("--no-speech", action="store_true", help="Do not play audio replies")
    parser.add_argument("message", nargs="*", help="Say one thing and exit")
    args = parser.parse_args()

    base = args.server.rstrip("/")
    session = requests.Session()
    player = None if args.no_speech else find_player()
    if not args.no_speech and player is None:
        print(f"{DIM}No audio player found (afplay/mpv/ffplay/paplay) — text only.{RESET}", file=sys.stderr)

    try:
        status = session.get(f"{base}/api/status", timeout=10).json()
    except requests.RequestException as exc:
        print(f"Cannot reach J.A.R.V.I.S. at {base}: {exc}", file=sys.stderr)
        return 1

    name = status.get("assistant", "J.A.R.V.I.S.")
    user = status.get("user", "Sir")

    def one_turn(text: str) -> None:
        try:
            response = session.post(f"{base}/api/chat", json={"text": text, "source": "cli"}, timeout=180)
            data = response.json()
        except requests.RequestException as exc:
            print(f"  connection lost: {exc}", file=sys.stderr)
            return
        if not response.ok:
            print(f"  {data.get('error', response.status_code)}", file=sys.stderr)
            return
        print(f"\n{CYAN}{name}:{RESET} {data['text']}\n")
        for call in data.get("tool_calls", []):
            mark = "·" if call.get("ok") else "x"
            print(f"{DIM}  {mark} {call['tool']}{RESET}")
        if player:
            try:
                audio = session.post(
                    f"{base}/api/speak", json={"text": data.get("speakable") or data["text"]}, timeout=120
                )
                if audio.ok:
                    play(audio.content, player)
                else:
                    print(f"{DIM}  (voice unavailable){RESET}", file=sys.stderr)
            except requests.RequestException as exc:
                print(f"{DIM}  (voice failed: {exc}){RESET}", file=sys.stderr)

    if args.message:
        one_turn(" ".join(args.message))
        return 0

    print(f"\n{CYAN}{name}{RESET} online. Dictate with Wispr Flow and press Enter. Ctrl-D to exit.\n")
    while True:
        try:
            text = input(f"{GOLD}{user}:{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{DIM}Goodbye, {user}.{RESET}")
            return 0
        if not text:
            continue
        if text.lower() in {"exit", "quit"}:
            print(f"{DIM}Goodbye, {user}.{RESET}")
            return 0
        one_turn(text)


if __name__ == "__main__":
    raise SystemExit(main())
