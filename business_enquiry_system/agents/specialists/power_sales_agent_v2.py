"""
Power Sales Agent - Handles electricity token purchases for Nigerian DISCOs.
"""

from typing import Dict, Any, Optional
from decimal import Decimal
try:
    from pydantic import BaseModel  # type: ignore
except Exception:
    class BaseModel:  # type: ignore
        def __init__(self, **data):
            for k, v in data.items():
                setattr(self, k, v)
from datetime import datetime
import re
import uuid

from agents.base_agent_v2 import BaseBusinessAgent, ConversationContext
from agents.navigator import Navigator


class PowerPurchaseRequest(BaseModel):
    disco: str
    meter_number: str
    amount: Decimal
    meter_type: str = "PREPAID"  # PREPAID or POSTPAID (MVP focuses on PREPAID)
    customer_id: Optional[str] = None


class PowerPurchaseResult(BaseModel):
    success: bool
    transaction_id: Optional[str] = None
    reference: Optional[str] = None
    disco: str
    meter_number: str
    amount: float
    service_charge: float
    total_amount: float
    token: Optional[str] = None
    units: Optional[float] = None
    message: str
    error: Optional[str] = None


class PowerSalesAgent(BaseBusinessAgent):
    """
    Electricity information and navigation agent for DISCO tokens.

    Scope (info-only):
    - Support for major DISCOs (EKEDC, IKEDC, AEDC, PHEDC, IBEDC, etc.)
    - Meter number validation (11–13 digits)
    - Amount guidance (₦500 – ₦500,000)
    - Provide purchase links and steps (self-service portal)
    - Troubleshooting and escalation guidance; no direct vending
    """

    SYSTEM_MESSAGE = """You are a power/electricity sales specialist.
Process prepaid token purchases for Nigerian DISCOs. Validate meter, amount, and return clear confirmations.
"""

    SUPPORTED_DISCOS = [
        "EKEDC", "IKEDC", "AEDC", "PHEDC", "IBEDC", "EEDC", "KEDCO", "BEDC", "JEDC", "KAEDCO",
    ]
    MIN_AMOUNT = Decimal("500.00")
    MAX_AMOUNT = Decimal("500000.00")
    SERVICE_CHARGE = Decimal("100.00")
    DEFAULT_TARIFF_NGN_PER_KWH = Decimal("55.00")  # Simplified estimate for MVP

    PROVIDER_APIS = {
        "EKEDC": {"base_url": "https://api.ekedp.com", "vend_endpoint": "/prepaid/vend", "enabled": False},
        "IKEDC": {"base_url": "https://www.ikejaelectric.com", "vend_endpoint": "/api/v1/vend", "enabled": False},
    }

    def __init__(self, llm_config: Dict[str, Any]):
        super().__init__(
            name="PowerSalesAgent",
            system_message=self.SYSTEM_MESSAGE,
            llm_config=llm_config,
            description="Processes electricity token purchases for DISCOs"
        )
        self.navigator = Navigator()

    # Public API
    def _process_specific(self, message: str, context: Optional[ConversationContext]) -> Dict[str, Any]:
        details = self._extract_purchase_details(message)
        if details:
            result = self.process_purchase(
                disco=details["disco"],
                meter_number=details["meter"],
                amount=details["amount"],
                meter_type=details.get("meter_type", "PREPAID"),
                customer_id=context.customer_id if context else None,
            )
            try:
                if re.search(r"\b(failed|error|refund|not working|token|deducted)\b", message.lower()):
                    result["escalation"] = {"suggested": True, "reason": "Potential issue indicated in message"}
            except Exception:
                pass
            return result
        # Non-purchase message → use LLM to assist
        llm_resp = self.get_llm_response(
            "Provide assistance for purchasing electricity tokens in Nigeria (DISCOs)."
        )
        out = {"action": "information_provided", "response": llm_resp}
        try:
            import re as _re
            if _re.search(r"\b(failed|error|refund|not working|token|deducted)\b", message.lower()):
                out["escalation"] = {"suggested": True, "reason": "Potential issue indicated in message"}
        except Exception:
            pass
        return out

    def process_purchase(
        self,
        disco: str,
        meter_number: str,
        amount: Decimal,
        meter_type: str = "PREPAID",
        customer_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        self.logger.info(f"Processing power purchase: {disco} - {meter_number} - ₦{amount}")

        validation = self._validate_purchase(disco, meter_number, amount)
        if not validation["valid"]:
            return {"success": False, "action": "guidance_provided", "error": validation["error"]}

        total_amount = amount + self.SERVICE_CHARGE
        purchase_url = self.navigator.purchase_url("power", disco)
        message = self.navigator.build_cta("power", disco, {
            "disco": disco,
            "meter": meter_number,
            "amount": amount,
            "service_charge": self.SERVICE_CHARGE,
        })
        return {"success": True, "action": "guidance_provided", "response": message, "navigation": {"purchase_url": purchase_url}}

    # Internals
    def _validate_purchase(self, disco: str, meter: str, amount: Decimal) -> Dict[str, Any]:
        if disco.upper() not in self.SUPPORTED_DISCOS:
            return {"valid": False, "error": f"DISCO '{disco}' not supported. Supported: {', '.join(self.SUPPORTED_DISCOS)}"}
        if not re.fullmatch(r"\d{11,13}", meter):
            return {"valid": False, "error": "Invalid meter number. Must be 11-13 digits."}
        if amount < self.MIN_AMOUNT:
            return {"valid": False, "error": f"Minimum purchase is ₦{self.MIN_AMOUNT}"}
        if amount > self.MAX_AMOUNT:
            return {"valid": False, "error": f"Maximum purchase is ₦{self.MAX_AMOUNT:,} per transaction"}
        return {"valid": True}

    def _process_transaction(self, disco: str, meter: str, amount: Decimal, total_amount: Decimal, meter_type: str) -> Dict[str, Any]:
        return {"success": False, "error": "TRANSACTIONS_DISABLED", "error_code": "INFO_ONLY"}

    def _mock_transaction(self, disco: str, meter: str, amount: Decimal, total_amount: Decimal) -> Dict[str, Any]:
        return {"success": False, "error": "TRANSACTIONS_DISABLED", "error_code": "INFO_ONLY"}

    def _call_real_api(self, disco: str, meter: str, amount: Decimal, total_amount: Decimal, meter_type: str) -> Dict[str, Any]:
        return {"success": False, "error": "TRANSACTIONS_DISABLED", "error_code": "INFO_ONLY"}

    def _resolve_purchase_url(self, disco: str) -> str:
        return self.navigator.purchase_url("power", disco)

    def _format_navigation_message(self, disco: str, meter: str, amount: Decimal, total_amount: Decimal, url: str) -> str:
        return self.navigator.build_cta("power", disco, {
            "disco": disco,
            "meter": meter,
            "amount": amount,
            "service_charge": self.SERVICE_CHARGE,
        })

    def _extract_purchase_details(self, message: str) -> Optional[Dict[str, Any]]:
        text = message.lower()
        # DISCO
        disco = None
        for d in self.SUPPORTED_DISCOS:
            if d.lower() in text:
                disco = d
                break
        if not disco:
            return None
        # Meter number (11-13 digits)
        meter_match = re.search(r"\b(\d{11,13})\b", message)
        if not meter_match:
            return None
        meter = meter_match.group(1)
        # Amount
        amt_match = re.search(r"₦?\s*(\d{1,3}(?:,\d{3})*|\d+)\s*(?:naira|ngn|₦)?", message, re.IGNORECASE)
        if not amt_match:
            return None
        try:
            amt = Decimal(amt_match.group(1).replace(",", ""))
        except Exception:
            return None
        # Meter type (optional hint)
        meter_type = "PREPAID" if "prepaid" in text else ("POSTPAID" if "postpaid" in text else "PREPAID")
        return {"disco": disco, "meter": meter, "amount": amt, "meter_type": meter_type}

    def _get_failure_recommendation(self, error_code: str) -> str:
        tips = {
            "TIMEOUT": "Provider is delayed. Please wait 5 minutes and verify again.",
            "INVALID_METER": "Please confirm the meter number with your DISCO.",
            "SANDBOX_DISABLED": "Service not configured yet. Please contact support.",
            "API_ERROR": "Temporary provider issue. We will retry shortly.",
        }
        return tips.get(error_code, "Please contact support with your transaction reference for assistance.")


# ============================================================
# TESTING (optional quick run)
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

    agent = PowerSalesAgent(llm_config)

    print("=" * 80)
    print("POWER SALES AGENT TESTING")
    print("=" * 80)

    res = agent.process_purchase(
        disco="EKEDC",
        meter_number="12345678901",
        amount=Decimal("5000")
    )
    print(res.get("response", res))
