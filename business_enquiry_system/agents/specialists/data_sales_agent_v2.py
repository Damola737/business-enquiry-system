"""
Data Sales Agent - Handles mobile data bundle purchases for Nigerian networks.
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


class DataPurchaseRequest(BaseModel):
    network: str
    recipient_phone: str
    size_gb: float  # bundle size in GB (normalize from MB/GB)
    customer_id: Optional[str] = None


class DataPurchaseResult(BaseModel):
    success: bool
    transaction_id: Optional[str] = None
    reference: Optional[str] = None
    network: str
    recipient: str
    bundle_label: str
    price: float
    validity: str
    message: str
    error: Optional[str] = None


class DataSalesAgent(BaseBusinessAgent):
    """
    Data information and navigation agent for MTN, Airtel, Glo, 9Mobile.

    Scope (info-only):
    - Validates phone number (Nigerian format)
    - Maps requested size to available bundle matrix (simplified)
    - Provides purchase links and activation steps; no direct vending
    """

    SYSTEM_MESSAGE = """You are a data package sales specialist for Nigerian networks.
Assist customers to purchase and activate data bundles (MTN, Airtel, Glo, 9Mobile).
"""

    SUPPORTED_NETWORKS = ["MTN", "AIRTEL", "GLO", "9MOBILE"]

    # Simplified bundle matrix (subset)
    DATA_BUNDLES: Dict[str, list] = {
        "MTN": [
            {"size_gb": 0.1, "label": "100MB", "price": 100, "validity": "1 day", "code": "*312*1#"},
            {"size_gb": 1.0, "label": "1GB", "price": 500, "validity": "7 days", "code": "*312*16#"},
            {"size_gb": 2.0, "label": "2GB", "price": 1200, "validity": "30 days", "code": "*312*20#"},
            {"size_gb": 10.0, "label": "10GB", "price": 5000, "validity": "30 days", "code": "*312*21#"},
        ],
        "AIRTEL": [
            {"size_gb": 0.1, "label": "100MB", "price": 100, "validity": "1 day", "code": "*141*100#"},
            {"size_gb": 1.0, "label": "1GB", "price": 500, "validity": "7 days", "code": "*141*1*3#"},
            {"size_gb": 2.0, "label": "2GB", "price": 1200, "validity": "30 days", "code": "*141*1*5#"},
        ],
        "GLO": [
            {"size_gb": 1.0, "label": "1GB", "price": 300, "validity": "1 day", "code": "*312#"},
            {"size_gb": 10.0, "label": "10GB", "price": 3000, "validity": "30 days", "code": "*312#"},
        ],
        "9MOBILE": [
            {"size_gb": 1.0, "label": "1GB", "price": 500, "validity": "7 days", "code": "*229*2*7#"},
            {"size_gb": 2.0, "label": "2GB", "price": 1200, "validity": "30 days", "code": "*229*2*8#"},
        ],
    }

    PROVIDER_APIS = {
        "MTN": {"base_url": "https://api.mtn.ng", "vend_endpoint": "/data/vend", "enabled": False},
        "AIRTEL": {"base_url": "https://api.airtel.ng", "vend_endpoint": "/data/activate", "enabled": False},
    }

    def __init__(self, llm_config: Dict[str, Any]):
        super().__init__(
            name="DataSalesAgent",
            system_message=self.SYSTEM_MESSAGE,
            llm_config=llm_config,
            description="Processes data bundle purchases for MTN, Airtel, Glo, 9Mobile"
        )
        self.navigator = Navigator()

    # Public API
    def _process_specific(self, message: str, context: Optional[ConversationContext]) -> Dict[str, Any]:
        details = self._extract_purchase_details(message)
        if details:
            result = self.process_purchase(
                network=details["network"],
                recipient_phone=details["phone"],
                size_gb=details["size_gb"],
                customer_id=context.customer_id if context else None,
            )
            try:
                if re.search(r"\b(failed|deducted|refund|slow|not working|data not)\b", message.lower()):
                    result["escalation"] = {"suggested": True, "reason": "Potential issue indicated in message"}
            except Exception:
                pass
            return result
        llm_resp = self.get_llm_response("Help the user choose and activate a data bundle in Nigeria.")
        out = {"action": "information_provided", "response": llm_resp}
        try:
            low = message.lower()
            cues = [
                "failed", "deducted", "refund", "slow", "not working",
                "data not", "didn't", "didnt", "not receive", "not received", "not delivered", "charged"
            ]
            if any(c in low for c in cues):
                out["escalation"] = {"suggested": True, "reason": "Potential issue indicated in message"}
        except Exception:
            pass
        return out

    def process_purchase(self, network: str, recipient_phone: str, size_gb: float, customer_id: Optional[str] = None) -> Dict[str, Any]:
        self.logger.info(f"Processing data purchase: {network} - {recipient_phone} - {size_gb}GB")
        validation = self._validate_purchase(network, recipient_phone, size_gb)
        if not validation["valid"]:
            return {"success": False, "action": "purchase_failed", "error": validation["error"]}

        bundle = self._select_bundle(network, size_gb)
        if not bundle:
            return {"success": False, "action": "purchase_failed", "error": "Requested bundle not available"}

        purchase_url = self.navigator.purchase_url("data", network)
        message = self.navigator.build_cta("data", network, {
            "network": network,
            "phone": recipient_phone,
            "bundle": bundle,
        })
        return {"success": True, "action": "guidance_provided", "response": message, "navigation": {"purchase_url": purchase_url}}

    # Internals
    def _validate_purchase(self, network: str, phone: str, size_gb: float) -> Dict[str, Any]:
        if network.upper() not in self.SUPPORTED_NETWORKS:
            return {"valid": False, "error": f"Network '{network}' not supported. Supported: {', '.join(self.SUPPORTED_NETWORKS)}"}
        if not self._is_valid_nigerian_phone(phone):
            return {"valid": False, "error": "Invalid phone number. Use 080xxxxxxxx or +234xxxxxxxxxx"}
        if size_gb <= 0:
            return {"valid": False, "error": "Bundle size must be greater than 0"}
        return {"valid": True}

    def _select_bundle(self, network: str, size_gb: float) -> Optional[Dict[str, Any]]:
        # Pick the closest available bundle size at or above the requested size
        options = self.DATA_BUNDLES.get(network.upper(), [])
        if not options:
            return None
        # Find exact or next-higher match
        sorted_opts = sorted(options, key=lambda b: b["size_gb"])
        for b in sorted_opts:
            if b["size_gb"] >= size_gb - 1e-6:
                return b
        return sorted_opts[-1]  # fallback to largest available

    def _process_transaction(self, network: str, phone: str, bundle: Dict[str, Any]) -> Dict[str, Any]:
        return {"success": False, "error": "TRANSACTIONS_DISABLED", "error_code": "INFO_ONLY"}

    def _mock_transaction(self, network: str, phone: str, bundle: Dict[str, Any]) -> Dict[str, Any]:
        return {"success": False, "error": "TRANSACTIONS_DISABLED", "error_code": "INFO_ONLY"}

    def _call_real_api(self, network: str, phone: str, bundle: Dict[str, Any]) -> Dict[str, Any]:
        return {"success": False, "error": "TRANSACTIONS_DISABLED", "error_code": "INFO_ONLY"}

    def _resolve_purchase_url(self, network: str) -> str:
        return self.navigator.purchase_url("data", network)

    def _format_navigation_message(self, network: str, phone: str, bundle: Dict[str, Any], url: str) -> str:
        return self.navigator.build_cta("data", network, {
            "network": network,
            "phone": phone,
            "bundle": bundle,
        })

    def _extract_purchase_details(self, message: str) -> Optional[Dict[str, Any]]:
        text = message.lower()
        # Network
        network = None
        for n in self.SUPPORTED_NETWORKS:
            if n.lower() in text or (n == "9MOBILE" and "9mobile" in text or "etisalat" in text):
                network = n
                break
        if not network:
            return None
        # Phone
        phone_match = re.search(r"(\+?234|0)[789]\d{9}", message.replace(" ", "").replace("-", ""))
        if not phone_match:
            return None
        phone = phone_match.group(0)
        # Size (e.g., 2GB, 500MB)
        size_gb = None
        size_match = re.search(r"(\d+(?:\.\d+)?)\s*(gb|mb)\b", text)
        if size_match:
            val = float(size_match.group(1))
            unit = size_match.group(2)
            size_gb = val if unit == "gb" else (val / 1024.0)
        else:
            # Fallback heuristics: common sizes mentioned as numbers without unit
            num_match = re.search(r"\b(\d{1,2})\b", text)
            if num_match:
                size_gb = float(num_match.group(1))  # assume GB if no unit
        if not size_gb or size_gb <= 0:
            return None
        return {"network": network, "phone": phone, "size_gb": size_gb}

    def _is_valid_nigerian_phone(self, phone: str) -> bool:
        p = phone.replace(" ", "").replace("-", "")
        return bool(re.fullmatch(r"(\+?234|0)[789]\d{9}", p))

    def _get_failure_recommendation(self, error_code: str) -> str:
        tips = {
            "TIMEOUT": "Provider is delayed. Please wait 2 minutes and check again.",
            "SANDBOX_DISABLED": "Service not configured yet. Please contact support.",
            "API_ERROR": "Temporary provider issue. We will retry shortly.",
        }
        return tips.get(error_code, "Please contact support with your reference for assistance.")


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

    agent = DataSalesAgent(llm_config)

    print("=" * 80)
    print("DATA SALES AGENT TESTING")
    print("=" * 80)

    res = agent.process_purchase(
        network="MTN",
        recipient_phone="08012345678",
        size_gb=2.0
    )
    print(res.get("response", res))
