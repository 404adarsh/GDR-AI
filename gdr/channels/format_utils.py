"""Message formatting utilities for GDR chat channels (Telegram, MarkanM, etc.).

Ensures outgoing messages are clean, well-drafted, natural, and free of AI-generated
system labels, raw tags, thought blocks, and distracting symbols.
"""

import re
from typing import Optional


def format_clean_bot_message(raw_text: Optional[str]) -> str:
    """Format and clean AI response for delivery through chat bots (Telegram / MarkanM).

    - Strips internal reasoning / <think> tags.
    - Strips bracketed AI mode / telemetry banners (e.g. '[Offline Local AI Mode]').
    - Strips musical symbols, decorative bullet stars, and AI marker glyphs.
    - Normalizes paragraph whitespace and produces well-structured, human-friendly text.
    """
    if not raw_text:
        return ""

    text = str(raw_text).strip()

    # 1. Strip <think>...</think> blocks from DeepSeek / reasoning models
    text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE)

    # 2. Strip bracketed provider prefixes and internal execution banners:
    # e.g., '[Offline Local AI Mode]', '[Sarvam • Neural HD Studio (hi-IN-SwaraNeural)]', '[Local System AI]'
    text = re.sub(
        r"\[(?:Offline Local AI Mode|LocalOfflineLLM|Sarvam|GDR Fast Lane|GDR Heavy MoE Lane|Local System AI|vol|FACT|PREFERENCE|PERSONA|STYLE|Query Ingestion|Policy Verification|Agent Response)[^\]]*\]",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\[[^\]]*\b(?:Mode|Engine|Model|Lane|tokens?|Studio|Neural)\b[^\]]*\]",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # 3. Strip decorative / AI-generated symbols and musical notes
    dirty_symbols = ["♪", "♫", "♩", "♬", "★", "☆", "◆", "◇", "■", "□", "▲", "▼", "►", "◄", "✦", "✧"]
    for s in dirty_symbols:
        text = text.replace(s, "")

    # 4. Normalize list bullets: convert non-standard bullets like '●' or '•' to standard '-'
    text = re.sub(r"^[ \t]*[•●]\s*", "- ", text, flags=re.MULTILINE)

    # 5. Clean up tool execution verbose lines if leaked into response (e.g. '🎬 Searching YouTube for...')
    # keep genuine information but clean up excessive robot logs
    text = re.sub(r"\[vol:\s*\d+%\]", "", text, flags=re.IGNORECASE)

    # 6. Normalize whitespace: reduce 3+ consecutive newlines to 2, strip trailing whitespace per line
    lines = [line.rstrip() for line in text.splitlines()]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()

