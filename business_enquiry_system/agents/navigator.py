"""
Navigator helper: centralized link resolution and CTA message generation
for airtime, power, and data services.
"""

from __future__ import annotations

from typing import Dict, Any, Optional
import json
import os


class Navigator:
    """
    Central helper to resolve self‑service URLs and compose consistent
    call‑to‑action (CTA) copy across service domains.
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._default_config_path()
        self._urls = self._load_urls(self.config_path)

    def _default_config_path(self) -> str:
        # __file__ => .../business_enquiry_system/agents/navigator.py
        # root     => .../business_enquiry_system
        root = os.path.dirname(os.path.dirname(__file__))
        return os.path.join(root, "config", "service_urls.json")

    def _load_urls(self, path: str) -> Dict[str, Any]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {
                "airtime": {},
                "data": {},
                "power": {},
                "support": {},
            }

    # ---- URL resolution ----
    def purchase_url(self, service: str, key: str) -> str:
        svc = (service or "").lower()
        k = (key or "").upper()
        coll = self._urls.get(svc, {})
        default_map = {
            "airtime": "https://portal.example.com/airtime",
            "data": "https://portal.example.com/data",
            "power": "https://portal.example.com/power",
        }
        return coll.get(k, default_map.get(svc, "https://portal.example.com"))

    def support_url(self, topic: str) -> str:
        return self._urls.get("support", {}).get(topic, "https://help.example.com/contact")

    # ---- CTA builders ----
    def build_cta(self, service: str, key: str, context: Dict[str, Any]) -> str:
        svc = (service or "").lower()
        if svc == "airtime":
            return self._cta_airtime(key, context)
        if svc == "power":
            return self._cta_power(key, context)
        if svc == "data":
            return self._cta_data(key, context)
        return self._cta_generic(context)

    def _cta_airtime(self, network: str, ctx: Dict[str, Any]) -> str:
        url = self.purchase_url("airtime", network)
        amount = ctx.get("amount")
        discount = ctx.get("discount") or 0
        discount_note = f" (bulk discount ₦{float(discount):,.2f})" if discount and discount > 0 else ""
        return (
            f"ℹ️ Airtime Purchase Guidance\n\n"
            f"Network: {network}\n"
            f"Recipient: {ctx.get('phone','')}\n"
            f"Target Amount: ₦{float(amount):,.2f}{discount_note}\n\n"
            f"Self‑service link: {url}\n\n"
            "Steps:\n"
            "1) Open the link above\n"
            "2) Enter the recipient number and amount\n"
            "3) Review and confirm payment\n\n"
            "Tips:\n"
            "- Minimum ₦50, maximum ₦50,000 per transaction\n"
            "- For ₦10,000+ purchases, bulk discounts may apply\n"
            "- Need help? Reply here and we can guide or escalate\n"
        ).strip()

    def _cta_power(self, disco: str, ctx: Dict[str, Any]) -> str:
        url = self.purchase_url("power", disco)
        amount = ctx.get("amount")
        service_charge = ctx.get("service_charge")
        total = (float(amount) if amount else 0.0) + (float(service_charge) if service_charge else 0.0)
        return (
            f"ℹ️ Electricity Token Purchase Guidance\n\n"
            f"DISCO: {disco}\n"
            f"Meter: {ctx.get('meter','')}\n"
            f"Target Amount: ₦{float(amount):,.2f}\n"
            f"Service charge (estimate): ₦{float(service_charge or 0):,.2f}\n"
            f"Approx. Total: ₦{total:,.2f}\n\n"
            f"Self‑service link: {url}\n\n"
            "Steps:\n"
            "1) Open the link above\n"
            "2) Enter meter number and amount (ensure PREPAID)\n"
            "3) Review and confirm payment\n"
            "4) Load the 20‑digit token on your meter\n\n"
            "Tips:\n"
            "- Meter number must be 11–13 digits\n"
            "- Keep your receipt/reference in case of issues\n"
            "- If token doesn’t load, share the error and we can guide/escalate\n"
        ).strip()

    def _cta_data(self, network: str, ctx: Dict[str, Any]) -> str:
        url = self.purchase_url("data", network)
        bundle = ctx.get("bundle", {})
        label = bundle.get("label", "Selected Bundle")
        price = bundle.get("price")
        validity = bundle.get("validity", "")
        price_str = f"₦{price:,.2f}" if isinstance(price, (int, float)) else ""
        return (
            f"ℹ️ Data Bundle Purchase Guidance\n\n"
            f"Network: {network}\n"
            f"Recipient: {ctx.get('phone','')}\n"
            f"Recommended Bundle: {label} {f'— {price_str}' if price_str else ''} {f'({validity})' if validity else ''}\n\n"
            f"Self‑service link: {url}\n\n"
            "Steps:\n"
            "1) Open the link above\n"
            "2) Enter recipient number and select bundle\n"
            "3) Review and confirm payment\n\n"
            "Tip: After activation, dial the network balance code to confirm.\n"
            "Need more help? We can guide further or escalate to a human agent.\n"
        ).strip()

    def _cta_generic(self, ctx: Dict[str, Any]) -> str:
        url = self.support_url("contact")
        return (
            f"ℹ️ Guidance\n\n"
            f"Please use our support portal: {url}\n"
        ).strip()
