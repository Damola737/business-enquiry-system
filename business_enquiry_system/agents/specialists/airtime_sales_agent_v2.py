# agents/specialists/airtime_sales_agent_v2.py
"""
Airtime Sales Agent - Handles mobile airtime purchases across Nigerian networks.
"""

import requests
import re
from typing import Dict, Any, Optional
from decimal import Decimal
try:
    from pydantic import BaseModel  # type: ignore
except Exception:
    class BaseModel:  # type: ignore
        def __init__(self, **data):
            for k, v in data.items():
                setattr(self, k, v)
import uuid

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from agents.base_agent_v2 import BaseBusinessAgent, ConversationContext
from agents.navigator import Navigator


# ============================================================
# DATA MODELS
# ============================================================

class AirtimePurchaseRequest(BaseModel):
    """Airtime purchase request model."""
    network: str
    recipient_phone: str
    amount: Decimal
    customer_id: Optional[str] = None


class AirtimePurchaseResult(BaseModel):
    """Airtime purchase result model."""
    success: bool
    transaction_id: Optional[str] = None
    reference: Optional[str] = None
    network: str
    recipient: str
    amount: float
    discount: float = 0.0
    final_amount: float
    message: str
    error: Optional[str] = None


# ============================================================
# AIRTIME SALES AGENT
# ============================================================

class AirtimeSalesAgent(BaseBusinessAgent):
    """
    Airtime information and navigation agent for Nigerian mobile networks.

    Scope (info-only):
    - Support for MTN, Airtel, Glo, 9Mobile (guidance only)
    - Phone number validation (Nigerian format)
    - Amount guidance (₦50 - ₦50,000)
    - Provide purchase links and steps (self-service portal)
    - Troubleshooting and escalation guidance; no direct transactions
    """

    SYSTEM_MESSAGE = """You are an airtime information and navigation specialist for Nigerian mobile networks.

NETWORKS SUPPORTED:
- MTN Nigeria
- Airtel Nigeria
- Glo Mobile
- 9Mobile (formerly Etisalat)

YOUR RESPONSIBILITIES:
1. Understand airtime requests and validate details (network, phone, amount)
2. Provide self-service purchase links and clear step-by-step guidance
3. Explain pricing, limits, and applicable discounts
4. Offer troubleshooting tips for common issues and when to escalate
5. Do not execute transactions; navigation and information only

PRICING:
- Minimum: ₦50
- Maximum: ₦50,000 per transaction
- Bulk discount: 5% off for ₦10,000+
- No transaction fee

RESPONSE GUIDELINES:
- Always confirm network and amount before processing
- Provide clear transaction references
- Explain any errors in simple terms
- Suggest solutions if something fails

Be professional, helpful, and efficient."""

    # Business rules
    SUPPORTED_NETWORKS = ["MTN", "AIRTEL", "GLO", "9MOBILE"]
    MIN_AMOUNT = Decimal("50.00")
    MAX_AMOUNT = Decimal("50000.00")
    BULK_THRESHOLD = Decimal("10000.00")
    BULK_DISCOUNT = Decimal("0.05")  # 5%

    # Network API configurations (mock for MVP)
    NETWORK_APIS = {
        "MTN": {
            "base_url": "https://api.mtn.ng/v1",
            "vend_endpoint": "/airtime/vend",
            "enabled": False  # Set to True when real API is ready
        },
        "AIRTEL": {
            "base_url": "https://api.airtel.ng",
            "vend_endpoint": "/airtime/purchase",
            "enabled": False
        },
        "GLO": {
            "base_url": "https://api.glo.com.ng",
            "vend_endpoint": "/airtime/recharge",
            "enabled": False
        },
        "9MOBILE": {
            "base_url": "https://api.9mobile.com.ng",
            "vend_endpoint": "/airtime/topup",
            "enabled": False
        }
    }

    def __init__(self, llm_config: Dict[str, Any], api_keys: Optional[Dict[str, str]] = None):
        super().__init__(
            name="AirtimeSalesAgent",
            system_message=self.SYSTEM_MESSAGE,
            llm_config=llm_config,
            description="Processes airtime purchases for MTN, Airtel, Glo, and 9Mobile"
        )

        self.api_keys = api_keys or {}
        self.session = requests.Session()
        self.navigator = Navigator()

    def _process_specific(
        self,
        message: str,
        context: Optional[ConversationContext]
    ) -> Dict[str, Any]:
        """
        Process airtime-related messages.

        Args:
            message: Customer message
            context: Conversation context

        Returns:
            Processing results
        """
        # Extract purchase details from message
        purchase_details = self._extract_purchase_details(message)

        if purchase_details:
            # Provide guidance for the purchase (no direct processing)
            result = self.process_purchase(
                network=purchase_details["network"],
                recipient_phone=purchase_details["phone"],
                amount=purchase_details["amount"],
                customer_id=context.customer_id if context else None
            )
            try:
                if re.search(r"\b(failed|deducted|refund|not received|delayed)\b", message.lower()):
                    result["escalation"] = {"suggested": True, "reason": "Potential issue indicated in message"}
            except Exception:
                pass
            return result
        else:
            # Use LLM for general inquiry
            llm_response = self.get_llm_response(message)
            ret = {
                "action": "information_provided",
                "response": llm_response,
                "purchase_processed": False
            }
            try:
                if re.search(r"\b(failed|deducted|refund|not received|delayed)\b", message.lower()):
                    ret["escalation"] = {"suggested": True, "reason": "Potential issue indicated in message"}
            except Exception:
                pass
            return ret

    def process_purchase(
        self,
        network: str,
        recipient_phone: str,
        amount: Decimal,
        customer_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Information-only: validate inputs and provide self-service guidance."""
        self.logger.info(
            f"Processing airtime purchase: {network} - {recipient_phone} - ₦{amount}"
        )

        # Step 1: Validate inputs
        validation = self._validate_purchase(network, recipient_phone, amount)
        if not validation["valid"]:
            return {
                "success": False,
                "error": validation["error"],
                "action": "guidance_provided"
            }

        # Step 2: Calculate guidance and provide navigation link (no transactions)
        final_amount, discount = self._calculate_amount(amount)
        purchase_url = self.navigator.purchase_url("airtime", network)
        response = self.navigator.build_cta("airtime", network, {
            "network": network,
            "phone": recipient_phone,
            "amount": amount,
            "discount": discount,
            "final_amount": final_amount,
        })
        return {"success": True, "action": "guidance_provided", "response": response, "navigation": {"purchase_url": purchase_url}}

    def _validate_purchase(
        self,
        network: str,
        phone: str,
        amount: Decimal
    ) -> Dict[str, Any]:
        """Validate purchase parameters."""

        # Check network support
        if network.upper() not in self.SUPPORTED_NETWORKS:
            return {
                "valid": False,
                "error": f"Network '{network}' not supported. We support: {', '.join(self.SUPPORTED_NETWORKS)}"
            }

        # Validate phone number
        if not self._is_valid_nigerian_phone(phone):
            return {
                "valid": False,
                "error": "Invalid phone number. Please use Nigerian format: 08012345678 or +2348012345678"
            }

        # Check amount range
        if amount < self.MIN_AMOUNT:
            return {
                "valid": False,
                "error": f"Minimum airtime purchase is ₦{self.MIN_AMOUNT}"
            }

        if amount > self.MAX_AMOUNT:
            return {
                "valid": False,
                "error": f"Maximum airtime purchase is ₦{self.MAX_AMOUNT:,} per transaction"
            }

        return {"valid": True}

    def _is_valid_nigerian_phone(self, phone: str) -> bool:
        """Validate Nigerian phone number format."""
        # Remove spaces and dashes
        phone = phone.replace(" ", "").replace("-", "")

        # Patterns: 08012345678, +2348012345678, 2348012345678
        pattern = r'^(\+?234|0)[789]\d{9}$'
        return bool(re.match(pattern, phone))

    def _calculate_amount(self, amount: Decimal) -> tuple[Decimal, Decimal]:
        """Calculate final amount with bulk discount."""
        if amount >= self.BULK_THRESHOLD:
            discount = amount * self.BULK_DISCOUNT
            final_amount = amount - discount
            return final_amount, discount
        return amount, Decimal("0.00")

    def _process_transaction(
        self,
        network: str,
        phone: str,
        amount: Decimal
    ) -> Dict[str, Any]:
        """Deprecated in info-only scope: returns a guidance-only result."""
        return {"success": False, "error": "TRANSACTIONS_DISABLED", "error_code": "INFO_ONLY"}

    def _mock_transaction(self, network: str, phone: str, amount: Decimal) -> Dict[str, Any]:
        return {"success": False, "error": "TRANSACTIONS_DISABLED", "error_code": "INFO_ONLY"}

    def _call_real_api(self, network: str, phone: str, amount: Decimal) -> Dict[str, Any]:
        return {"success": False, "error": "TRANSACTIONS_DISABLED", "error_code": "INFO_ONLY"}

    # Navigation helpers
    def _resolve_purchase_url(self, network: str) -> str:
        return self.navigator.purchase_url("airtime", network)

    def _format_navigation_message(self, network: str, phone: str, amount: Decimal, discount: Decimal, final_amount: Decimal, url: str) -> str:
        return self.navigator.build_cta("airtime", network, {
            "network": network,
            "phone": phone,
            "amount": amount,
            "discount": discount,
            "final_amount": final_amount,
        })

    def _extract_purchase_details(self, message: str) -> Optional[Dict[str, Any]]:
        """
        Extract purchase details from natural language message.

        Args:
            message: Customer message

        Returns:
            Dictionary with network, phone, amount or None
        """
        text_lower = message.lower()

        # Extract network
        network = None
        for net in self.SUPPORTED_NETWORKS:
            if net.lower() in text_lower:
                network = net
                break

        if not network:
            return None

        # Extract phone number
        phone_pattern = r'(\+?234|0)[789]\d{9}'
        phone_match = re.search(phone_pattern, message.replace(" ", "").replace("-", ""))
        if not phone_match:
            return None

        phone = phone_match.group(0)

        # Extract amount
        amount_patterns = [
            r'₦?\s*(\d{1,3}(?:,\d{3})*|\d+)\s*(?:naira|NGN|₦)?',
            r'(\d+)\s*(?:naira|NGN)'
        ]

        amount = None
        for pattern in amount_patterns:
            match = re.search(pattern, message)
            if match:
                amount_str = match.group(1).replace(",", "")
                try:
                    amount = Decimal(amount_str)
                    break
                except:
                    continue

        if not amount:
            return None

        return {
            "network": network,
            "phone": phone,
            "amount": amount
        }

    def _get_failure_recommendation(self, error_code: str) -> str:
        """Get recommendation for failed transaction."""
        recommendations = {
            "INSUFFICIENT_BALANCE": "Our platform balance is low. Transaction will be processed shortly.",
            "INVALID_PHONE": "Please verify the phone number is correct and active on the network.",
            "TIMEOUT": "Network is experiencing delays. Check your balance in 5 minutes.",
            "DUPLICATE": "This transaction was already processed. Check recipient's balance.",
            "NETWORK_ERROR": "Network provider is experiencing issues. Please try again in 10 minutes.",
            "API_ERROR": "Temporary service issue. Your money is safe. Try again in a few minutes."
        }
        return recommendations.get(error_code, "Please contact support with your transaction reference.")


# ============================================================
# TESTING
# ============================================================

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()

    llm_config = {
        "config_list": [{
            "model": "gpt-4o-mini",
            "api_key": os.getenv("OPENAI_API_KEY")
        }],
        "temperature": 0.3
    }

    agent = AirtimeSalesAgent(llm_config)

    print("=" * 80)
    print("AIRTIME SALES AGENT TESTING")
    print("=" * 80)

    # Test 1: Direct purchase
    print("\n[Test 1] Direct purchase processing")
    result = agent.process_purchase(
        network="MTN",
        recipient_phone="08012345678",
        amount=Decimal("1000")
    )
    print(result.get("response", result.get("error")))

    # Test 2: Bulk purchase with discount
    print("\n[Test 2] Bulk purchase (with discount)")
    result = agent.process_purchase(
        network="AIRTEL",
        recipient_phone="+2348098765432",
        amount=Decimal("15000")
    )
    print(result.get("response", result.get("error")))

    # Test 3: Natural language processing
    print("\n[Test 3] Natural language message")
    response = agent.process_message("Send me 500 naira Glo airtime to 07012345678")
    if response.success:
        print(response.result.get("response", response.result))
    else:
        print(f"ERROR: {response.error}")

    # Test 4: Invalid amount
    print("\n[Test 4] Invalid amount (too low)")
    result = agent.process_purchase(
        network="9MOBILE",
        recipient_phone="09012345678",
        amount=Decimal("25")
    )
    print(result.get("error"))

    # Metrics
    print("\n" + "=" * 80)
    print("AGENT METRICS")
    print("=" * 80)
    print(agent.get_metrics())
