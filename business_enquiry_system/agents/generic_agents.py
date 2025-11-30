"""
Generic, tenant-agnostic specialist agents.

These are simple LLM-backed / template-backed agents intended to handle
non-telecom domains such as e-commerce and healthcare in a configurable way.
"""

from typing import Dict, Any, Optional

from agents.base_agent_v2 import BaseBusinessAgent, ConversationContext
from config.tenant_config_store import TenantConfigStore


class ProductInquiryAgent(BaseBusinessAgent):
    """
    Handles general product or service questions for any tenant.

    Intended domain examples:
    - PRODUCT_INQUIRY (e-commerce)
    - Similar domains defined in tenant config.
    """

    SYSTEM_MESSAGE = """You are a helpful product inquiry assistant.
You answer questions about products or services clearly and concisely.
If exact product data is not available, give general guidance and suggest
how the user can find more details on the company's website or catalog."""

    def __init__(self, llm_config: Dict[str, Any]):
        super().__init__(
            name="ProductInquiryAgent",
            system_message=self.SYSTEM_MESSAGE,
            llm_config=llm_config,
            description="Handles product/service inquiry questions for any tenant",
        )

    def _process_specific(
        self,
        message: str,
        context: Optional[ConversationContext],
    ) -> Dict[str, Any]:
        tenant_id = getattr(context, "tenant_id", None) if context else None
        cfg = TenantConfigStore.get_instance().get_config(tenant_id or "legacy-ng-telecom")
        company = cfg.get("company_name", cfg.get("tenant_key", "this company"))

        # Best-effort LLM response; if LLM is disabled, a static string is returned.
        prompt = (
            f"You are answering for tenant/company: {company}.\n\n"
            f"User question:\n{message}\n\n"
            "Provide a concise answer about products or services. "
            "If you cannot know exact catalog details, say so and describe how "
            "the user can check the website, catalog, or contact support."
        )
        reply = self.get_llm_response(prompt)

        return {
            "action": "product_inquiry",
            "response": reply,
        }


class TransactionGuidanceAgent(BaseBusinessAgent):
    """
    Guides users through generic transactions such as orders, payments,
    bookings, or billing flows for any tenant.
    """

    SYSTEM_MESSAGE = """You are a transaction guidance assistant.
You help users with orders, payments, bookings, or billing steps.
You do NOT execute transactions; instead, explain the next steps clearly and
tell the user what information is required (IDs, dates, amounts, etc.)."""

    def __init__(self, llm_config: Dict[str, Any]):
        super().__init__(
            name="TransactionGuidanceAgent",
            system_message=self.SYSTEM_MESSAGE,
            llm_config=llm_config,
            description="Guides users through generic transaction flows",
        )

    def _process_specific(
        self,
        message: str,
        context: Optional[ConversationContext],
    ) -> Dict[str, Any]:
        tenant_id = getattr(context, "tenant_id", None) if context else None
        cfg = TenantConfigStore.get_instance().get_config(tenant_id or "legacy-ng-telecom")
        company = cfg.get("company_name", cfg.get("tenant_key", "this company"))

        prompt = (
            f"You are helping with a transaction for: {company}.\n\n"
            f"User message:\n{message}\n\n"
            "Explain in clear steps what the user should do next "
            "(for example: check order status, provide an order ID, confirm payment details, etc.). "
            "You do not have access to internal systems, so avoid pretending you can check live data."
        )
        reply = self.get_llm_response(prompt)

        return {
            "action": "transaction_guidance",
            "response": reply,
        }


class TroubleshootingAgent(BaseBusinessAgent):
    """
    Handles generic troubleshooting / problem descriptions for any tenant.
    """

    SYSTEM_MESSAGE = """You are a troubleshooting assistant.
You help users describe their problem clearly and suggest safe next steps.
You never provide medical, legal, or financial advice beyond general guidance.
Always suggest contacting a human expert or support channel for high-risk issues."""

    def __init__(self, llm_config: Dict[str, Any]):
        super().__init__(
            name="TroubleshootingAgent",
            system_message=self.SYSTEM_MESSAGE,
            llm_config=llm_config,
            description="Helps users troubleshoot issues in a safe, generic way",
        )

    def _process_specific(
        self,
        message: str,
        context: Optional[ConversationContext],
    ) -> Dict[str, Any]:
        tenant_id = getattr(context, "tenant_id", None) if context else None
        cfg = TenantConfigStore.get_instance().get_config(tenant_id or "legacy-ng-telecom")
        company = cfg.get("company_name", cfg.get("tenant_key", "this company"))

        prompt = (
            f"You are troubleshooting for: {company}.\n\n"
            f"User message:\n{message}\n\n"
            "1) Help the user clarify the problem.\n"
            "2) Suggest safe, generic next steps.\n"
            "3) For anything high-risk (health, money, legal), tell them to contact a human professional."
        )
        reply = self.get_llm_response(prompt)

        return {
            "action": "troubleshooting",
            "response": reply,
        }

