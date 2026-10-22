"""Natural language memory commands and CLI management for Phase 7.
Handles English, Hindi, and Hinglish triggers: 'remember', 'don't forget', 'note that', 'याद रखना'.
"""

from datetime import datetime
import json
import re
from typing import Optional, Tuple, Dict, Any

from blockbrain.memory.encrypted_store import get_secure_memory, EncryptedMemoryStore


def parse_memory_intent(text: str) -> Optional[Tuple[str, str, str]]:
    """Detect if user is instructing blockbrain to remember something.
    Returns (action: 'remember' | 'recall' | 'forget', subject, content) or None.
    """
    raw = text.strip()
    low = raw.lower()

    # Triggers for remember: "remember that...", "don't forget...", "note that...", "याद रखना..."
    rem_patterns = [
        r"^(?:please\s+)?remember\s+(?:that\s+)?(.+)",
        r"^(?:please\s+)?don'?t\s+forget\s+(?:that\s+)?(.+)",
        r"^(?:please\s+)?note\s+(?:down\s+)?(?:that\s+)?(.+)",
        r"^(?:कृपया\s+)?याद\s+रखना\s+(?:कि\s+)?(.+)",
    ]

    for pat in rem_patterns:
        m = re.search(pat, raw, flags=re.I)
        if m:
            content = m.group(1).strip()
            # Derive subject / entity key
            subj_match = re.search(r"^(?:my\s+|the\s+)?([\w\s]+?)\s+(?:is|expires|was|lives|are)\s+", content, flags=re.I)
            subject = subj_match.group(1).strip() if subj_match else content[:30]
            return ("remember", subject, content)

    # Triggers for forget
    if low.startswith("forget ") or "भूल जाओ" in low:
        subj = re.sub(r"^(?:please\s+)?forget\s+", "", raw, flags=re.I).strip()
        return ("forget", subj, "")

    # Triggers for recall
    rec_patterns = [
        r"^(?:what|when|who|where|do you remember)\s+.+",
        r"^(?:मुझे\s+)?बताओ\s+.+",
    ]
    for pat in rec_patterns:
        if re.search(pat, low):
            return ("recall", raw, "")

    return None


def execute_memory_action(action: str, subject: str, content: str) -> str:
    """Execute parsed memory intent against encrypted store."""
    store = get_secure_memory()

    if action == "remember":
        res = store.remember(subject=subject, content=content, category="pinned_fact")
        if res.get("status") == "superseded_old":
            return f"✅ Remembered: \"{content}\" (Updated prior fact #{res['superseded_old_id']})."
        return f"✅ Remembered: \"{content}\" (Stored securely)."

    elif action == "forget":
        success = store.forget(subject)
        if success:
            return f"🗑️ Memory regarding '{subject}' has been deleted."
        return f"No active memory found for '{subject}'."

    elif action == "recall":
        # Check if user specifically asks for old/superseded memories ("what was my old address?")
        include_superseded = any(w in subject.lower() for w in ["old", "previous", "earlier", "पुराना", "पहले"])
        matches = store.recall(subject, include_superseded=include_superseded, limit=5)
        if not matches:
            return "I don't have any record of that in my memory."

        lines = []
        for m in matches:
            dt = m["event_date"][:10]
            status_tag = f" [Superseded on {m.get('created_at', '')[:10]}]" if m.get("status") == "superseded" else ""
            lines.append(f"• According to memory from {dt}{status_tag}: {m['content']}")

        return "\n".join(lines)

    return ""

