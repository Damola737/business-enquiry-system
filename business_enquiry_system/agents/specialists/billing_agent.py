from typing import Dict, Any, List
from datetime import datetime
from agents.base_agent import BaseBusinessAgent

class BillingAgent(BaseBusinessAgent):
    SYSTEM_MESSAGE = """You are the Billing Agent for TechCorp Solutions.
    Handle invoices, refunds, payment methods, and subscription changes.
    """

    def __init__(self, llm_config):
        super().__init__(
            name="billing_agent",
            system_message=self.SYSTEM_MESSAGE,
            llm_config=llm_config,
            description="Manages payment, invoices, refunds, and subscriptions"
        )

    def _process_specific(self, message: str, context: Dict[str, Any] = None) -> Any:
        t = message.lower()
        if any(k in t for k in ["invoice", "receipt", "charged", "charge", "billing", "refund", "payment"]):
            actions: List[str] = []
            if "invoice" in t or "receipt" in t:
                actions.append("Locate the customer’s last invoice and email a PDF copy.")
            if "refund" in t or "charged twice" in t or "double charge" in t:
                actions.append("Open a refund ticket and verify duplicate charge before processing.")
            if "payment" in t or "card" in t:
                actions.append("Guide the customer to Settings > Billing > Payment Methods to update card.")
            if not actions:
                actions.append("Verify subscription status and recent transactions.")
            return {"billing_actions": actions, "status": "ok"}
        return {"billing_actions": ["Clarify billing need (invoice copy, refund, payment update, plan change)."], "status": "needs_more_info"}
