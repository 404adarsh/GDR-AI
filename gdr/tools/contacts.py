"""Contact and relationship tools for Aarushi / GDR-AI."""

from typing import Dict, Any, Optional
from gdr.tools.registry import tool
from gdr.contacts.service import get_contact_service


@tool(name="add_contact", description="Save a friend, family member, colleague, or enemy/untrusted contact with relationship and trust level details (0-100%).", category="contacts", tier="AUTO")
def add_contact(
    display_name: str,
    relationship_type: str = "Friend",
    trust_level: int = 50,
    email: str = "",
    phone_number: str = "",
    notes: str = "",
    is_trusted_contact: Optional[bool] = None
) -> str:
    svc = get_contact_service()
    res = svc.add_contact(
        display_name=display_name,
        relationship_type=relationship_type,
        trust_level=trust_level,
        email=email or None,
        phone_number=phone_number or None,
        notes=notes,
        is_trusted_contact=is_trusted_contact
    )
    t_val = res.get("trust_level", 50)
    trusted_tag = f" [Trust: {t_val}% - ⭐ Trusted]" if res.get("is_trusted_contact") else (f" [Trust: {t_val}% - ⚠️ Enemy/Untrusted]" if t_val <= 25 else f" [Trust: {t_val}%]")
    return f"Saved contact {res['display_name']} ({res['relationship_type']}){trusted_tag}. ID: {res['id']}."


@tool(name="search_contacts", description="Search saved contacts by name, relationship, email, or notes to find emails, numbers, and trust levels.", category="contacts", tier="AUTO")
def search_contacts(query: str = "", relationship_type: str = "") -> str:
    svc = get_contact_service()
    results = svc.search_contacts(query=query, relationship_type=relationship_type or None)
    if not results:
        return f"No contacts found matching '{query}'."

    lines = [f"Found {len(results)} contacts:"]
    for c in results:
        t_val = c.get("trust_level", 50)
        trust_badge = f" [Trust: {t_val}% ⭐ Trusted]" if c.get("is_trusted_contact") else (f" [Trust: {t_val}% ⚠️ Enemy]" if t_val <= 25 else f" [Trust: {t_val}%]")
        details = []
        if c.get("email"):
            details.append(f"Email: {c['email']}")
        if c.get("phone_number"):
            details.append(f"Phone: {c['phone_number']}")
        if c.get("notes"):
            details.append(f"Notes: {c['notes']}")
        det_str = f" | {', '.join(details)}" if details else ""
        lines.append(f"• {c['display_name']} ({c['relationship_type']}){trust_badge}{det_str}")

    return "\n".join(lines)


@tool(name="get_trusted_contacts", description="Retrieve the list of trusted emergency / close support contacts.", category="contacts", tier="AUTO")
def get_trusted_contacts() -> str:
    svc = get_contact_service()
    results = svc.get_trusted_contacts()
    if not results:
        return "No trusted contacts have been designated yet."

    lines = [f"Trusted Contacts ({len(results)}):"]
    for c in results:
        contact_info = c.get("email") or c.get("phone_number") or "No contact details"
        lines.append(f"• {c['display_name']} ({c['relationship_type']}) - {contact_info} (preferred: {c['preferred_contact_method']})")
    return "\n".join(lines)

