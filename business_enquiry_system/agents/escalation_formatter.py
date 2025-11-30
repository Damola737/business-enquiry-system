"""
Escalation summary formatter for human handoff.
Produces a compact, structured summary plus a human‑readable text block.
"""

from typing import Dict, Any
from datetime import datetime


def build_escalation_summary(
    enquiry_id: str,
    original_message: str,
    classification: Dict[str, Any],
    specialist_output: Dict[str, Any],
    customer: Dict[str, Any],
) -> Dict[str, Any]:
    """Return a minimal escalation summary for human agents."""
    domain = classification.get("service_domain")
    intent = classification.get("intent")
    priority = classification.get("priority")
    sentiment = classification.get("sentiment")
    entities = classification.get("entities", {})

    nav = specialist_output.get("navigation", {})
    response = specialist_output.get("response", "")
    reason = (specialist_output.get("escalation") or {}).get("reason", "")

    text = (
        f"Escalation Summary (Enquiry: {enquiry_id})\n"
        f"Date: {datetime.utcnow().isoformat()}Z\n\n"
        f"Customer\n"
        f"- Name: {customer.get('name') or '-'}\n"
        f"- Phone: {customer.get('phone') or '-'}\n\n"
        f"Classification\n"
        f"- Domain: {domain} | Intent: {intent} | Priority: {priority} | Sentiment: {sentiment}\n"
        f"- Entities: {entities}\n\n"
        f"Customer Message\n"
        f"---\n{original_message}\n---\n\n"
        f"Assistant Guidance (last)\n"
        f"---\n{response}\n---\n\n"
        f"Links / Navigation\n"
        f"- Purchase/Help: {nav.get('purchase_url') or '-'}\n\n"
        f"Escalation Trigger\n"
        f"- {reason or 'Agent suggested handoff based on message content'}"
    )

    return {
        "enquiry_id": enquiry_id,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "customer": customer,
        "classification": classification,
        "entities": entities,
        "navigation": nav,
        "reason": reason or "agent_suggestion",
        "summary_text": text,
    }
