"""Speech-Text Processing and Pronunciation Module for GDR AI.

Separates visual markdown output from natural spoken representation.
Strips formatting syntax, system labels, and decorative emojis while preserving
technical terms, numerals, and natural Hinglish phrasing.
"""

import re
from typing import List, Dict, Optional

# Pronunciation dictionary for common technical terms and names
PRONUNCIATION_DICTIONARY: Dict[str, str] = {
    # Programming Languages & Frameworks
    "python": "Python",
    "javascript": "JavaScript",
    "js": "JavaScript",
    "typescript": "TypeScript",
    "ts": "TypeScript",
    "php": "P H P",
    "html": "H T M L",
    "css": "C S S",
    "api": "A P I",
    "apis": "A P Is",
    "sdk": "S D K",
    "github": "GitHub",
    "git": "Git",
    "linux": "Linux",
    "kali linux": "Kali Linux",
    "kali": "Kali",
    "termux": "Termux",
    "ram": "RAM",
    "vram": "V-RAM",
    "ssd": "S S D",
    "hdd": "H D D",
    "cpu": "C P U",
    "gpu": "G P U",
    "terminal": "Terminal",
    "bash": "Bash",
    "ssh": "S S H",
    "url": "U R L",
    "json": "JSON",
    "sqlite": "SQLite",
    "postgres": "Postgres",
    "gdr": "G D R",
    "gdr-ai": "G D R AI",
    "gdr-ide": "G D R IDE",
    "ide": "I D E",
    "tts": "T T S",
    "stt": "S T T",
    "vad": "V A D",
    "matrix": "Matrix",
    "determinant": "Determinant",
    "probability": "Probability",
}


class SpeechTextProcessor:
    """Dedicated processor to clean and segment text for natural audio speech synthesis."""

    @classmethod
    def clean_for_speech(cls, text: str, mode: str = "concise") -> str:
        """Transform formatted response markdown into clean natural conversational speech."""
        if not text:
            return ""

        t = str(text)

        # 1. Strip system prefixes, bracketed provider metadata, and internal labels
        # e.g., '[Sarvam • Neural HD Studio]', '[LocalOfflineLLM • Piper Neural]', '[Offline Local AI Mode]'
        t = re.sub(r"\[(?:LocalOfflineLLM|Sarvam|Offline Local AI Mode|GDR Fast Lane|GDR Heavy MoE Lane|Local System AI|vol|FACT|PREFERENCE|PERSONA|STYLE|Query Ingestion|Policy Verification|Agent Response)[^\]]*\]", " ", t, flags=re.I)
        t = re.sub(r"\[[^\]]*\b(?:Mode|Engine|Model|Lane|tokens?|Studio|Neural)\b[^\]]*\]", " ", t, flags=re.I)
        t = re.sub(r"\b(?:Sweet Companion|Internal Telemetry)\b", " ", t, flags=re.I)

        # 2. Handle Markdown Code Blocks
        if mode == "concise":
            # If code block is surrounded by explanation, drop or summarize
            if re.search(r"```[\s\S]*?```", t):
                # If the entire message is almost just code, give a spoken summary
                subbed = re.sub(r"```[\s\S]*?```", " ", t).strip()
                if not subbed or len(subbed) < 15:
                    t = re.sub(r"```[\s\S]*?```", "Here is the code snippet.", t)
                else:
                    t = re.sub(r"```[\s\S]*?```", " ", t)
        else:
            # Code read mode: strip backticks, keep code lines
            t = re.sub(r"```[a-zA-Z0-9_]*\n?", " ", t)
            t = t.replace("```", " ")

        # 3. Handle inline code backticks (e.g. `python` -> python)
        t = re.sub(r"`([^`]+)`", r"\1", t)

        # 4. Handle Markdown Headings (e.g., '### System\n' -> 'System. ')
        t = re.sub(r"^#{1,6}\s*(.+)$", r"\1.", t, flags=re.M)

        # 5. Handle Markdown Table separators & structure
        t = re.sub(r"\|?\s*[-:]{2,}\s*\|\s*[-:]{2,}[\s\S]*?\|", " ", t)  # table header divider |--|--|
        t = re.sub(r"\|", " , ", t)  # cell dividers to gentle commas

        # 6. Convert percentages: 70% -> 70 percent
        t = re.sub(r"(\d+)%", r"\1 percent", t)

        # 7. Convert dashes: em-dash or double dash to comma pause
        t = re.sub(r"\s*[—–]\s*", ", ", t)
        t = re.sub(r"\s+--\s+", ", ", t)

        # 8. Clean Markdown bold and italics (**word** or *word*) while keeping punctuation
        # Special case: **Label:** -> Label:
        t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
        t = re.sub(r"\*([^*]+)\*", r"\1", t)
        t = re.sub(r"__([^_]+)__", r"\1", t)
        t = re.sub(r"_([^_]+)_", r"\1", t)

        # 9. Clean URLs: https://... -> link
        t = re.sub(r"https?://\S+", "link", t)

        # 10. Strip decorative emojis and symbols
        t = re.sub(r"[\U00010000-\U0010ffff\u2600-\u2669\u266C-\u27BF\u2B00-\u2BFF]", "", t)
        for sym in ["♪", "♫", "♩", "♬", "•", "●", "◆", "■", "★", "→", "►", "✓", "✗", "⚡", "💬", "🤖", "💖", "👻"]:
            t = t.replace(sym, " ")

        # 11. Normalize remaining raw special punctuation
        t = re.sub(r"[{}()\[\]|~#\\<>=^/@]", " ", t)

        # 12. Punctuation smoothing (fix multiple dots/commas)
        t = re.sub(r"\.{2,}", ". ", t)
        t = re.sub(r",\s*,+", ", ", t)
        t = re.sub(r"\s+([.,!?])", r"\1", t)
        t = re.sub(r"\s+", " ", t).strip()

        return t

    @classmethod
    def segment_into_speakable_phrases(cls, text: str) -> List[str]:
        """Split text into natural sentence/phrase chunks for low-latency streaming speech."""
        cleaned = cls.clean_for_speech(text)
        if not cleaned:
            return []

        # Split on sentence boundaries: periods, exclamation marks, question marks, newlines, Devanagari danda (।)
        # But avoid splitting on common abbreviations or decimal numbers like 10.5 or v2.0
        # Replace protected patterns temporarily
        protected = cleaned
        # Protect decimals: 3.14 -> 3<DOT>14
        protected = re.sub(r"(\d+)\.(\d+)", r"\1<DOT>\2", protected)
        # Protect abbreviations: e.g., i.e., Mr., Dr., etc.
        protected = re.sub(r"\b(e\.g|i\.e|mr|mrs|dr|vs|prof|etc)\.", r"\1<DOT>", protected, flags=re.I)

        # Split on sentence boundaries
        raw_parts = re.split(r"(?<=[.!?\n।])\s+", protected)
        segments: List[str] = []

        buffer = ""
        for part in raw_parts:
            # Restore protected dot
            restored = part.replace("<DOT>", ".").strip()
            if not restored:
                continue

            # If part is very short (< 15 chars and doesn't end with strong terminal), buffer it
            if len(restored) < 15 and not any(restored.endswith(p) for p in [".", "!", "?", "।"]):
                buffer = f"{buffer} {restored}".strip()
            else:
                if buffer:
                    combined = f"{buffer} {restored}".strip()
                    buffer = ""
                    segments.append(combined)
                else:
                    segments.append(restored)

        if buffer:
            if segments:
                segments[-1] = f"{segments[-1]} {buffer}".strip()
            else:
                segments.append(buffer)

        return [s for s in segments if len(s.strip()) > 0]

    @classmethod
    def apply_pronunciation_dictionary(cls, text: str) -> str:
        """Apply pronunciation hints for common technical terms."""
        if not text:
            return ""
        words = text.split()
        out = []
        for w in words:
            # Check lowercase match stripping punctuation
            clean_w = re.sub(r"[^\w-]", "", w).lower()
            if clean_w in PRONUNCIATION_DICTIONARY:
                replacement = PRONUNCIATION_DICTIONARY[clean_w]
                # Preserve surrounding punctuation
                out.append(re.sub(r"\b" + re.escape(clean_w) + r"\b", replacement, w, flags=re.I))
            else:
                out.append(w)
        return " ".join(out)


def clean_text_for_speech(text: str) -> str:
    """Backwards-compatible wrapper calling SpeechTextProcessor."""
    return SpeechTextProcessor.clean_for_speech(text)

