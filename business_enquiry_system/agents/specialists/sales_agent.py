# agents/specialists/sales_agent.py
"""
Sales Agent Module
Handles product inquiries, pricing, demos, and sales-related questions
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta
from agents.base_agent import BaseBusinessAgent


class SalesAgent(BaseBusinessAgent):
    SYSTEM_MESSAGE = """You are the Sales Agent for TechCorp Solutions.
    Provide pricing, plan recommendations, and demo scheduling.
    """

    def __init__(self, llm_config: Dict[str, Any]):
        super().__init__(
            name="sales_agent",
            system_message=self.SYSTEM_MESSAGE,
            llm_config=llm_config,
            description="Handles sales inquiries, pricing, demos, and product information"
        )
        self.product_catalog = self._load_product_catalog()
        self.pricing_matrix = self._load_pricing_matrix()
        self.active_promotions = self._load_promotions()
        self.demo_slots = self._initialize_demo_slots()

    def _load_product_catalog(self) -> Dict[str, Any]:
        return {
            "basic": {"name": "Basic Plan", "price_monthly": 49, "price_annual": 470, "features": ["Up to 10 users", "5GB storage", "Email support", "Basic analytics", "Mobile app access", "API access (1000 calls/day)"]},
            "professional": {"name": "Professional Plan", "price_monthly": 149, "price_annual": 1430, "features": ["Up to 50 users", "100GB storage", "Priority email & chat support", "Advanced analytics & reporting", "Custom dashboards", "API access (10000 calls/day)", "Integration marketplace", "Team collaboration tools", "Advanced security features"]},
            "enterprise": {"name": "Enterprise Plan", "price_monthly": "custom", "price_annual": "custom", "features": ["Unlimited users", "Unlimited storage", "24/7 dedicated support", "Custom analytics & reporting", "White-labeling options", "Unlimited API access", "Custom integrations", "Dedicated account manager", "99.9% SLA", "Advanced compliance features", "Priority feature requests", "On‑prem option"]}
        }

    def _load_pricing_matrix(self) -> Dict[str, Any]:
        return {
            "volume_discounts": {"10-25_users": 0.05, "26-50_users": 0.10, "51-100_users": 0.15, "100+_users": "custom"},
            "contract_discounts": {"monthly": 0, "quarterly": 0.05, "annual": 0.20, "2_year": 0.25}
        }

    def _load_promotions(self) -> List[Dict[str, Any]]:
        return [
            {"code": "ANNUAL20", "description": "20% off annual subscriptions", "discount": 0.20, "valid_until": (datetime.now() + timedelta(days=30)).isoformat(), "applicable_to": ["basic", "professional"]},
            {"code": "TRIAL30", "description": "Free 30-day trial", "trial_days": 30, "valid_until": (datetime.now() + timedelta(days=90)).isoformat(), "applicable_to": ["all"]}
        ]

    def _initialize_demo_slots(self) -> List[Dict[str, Any]]:
        slots = []
        base_date = datetime.now()
        for day in range(7):
            d = base_date + timedelta(days=day)
            if d.weekday() < 5:
                for hour in [9, 11, 14, 16]:
                    slots.append({"datetime": d.replace(hour=hour, minute=0).isoformat(), "duration": 45, "available": True})
        return slots

    def handle_pricing_inquiry(self, req: Dict[str, Any]) -> Dict[str, Any]:
        users = req.get("users", 1)
        contract_type = req.get("contract_type", "monthly")
        recs = []
        for tier_id, tier in self.product_catalog.items():
            price = tier[f"price_{contract_type}"]
            if price == "custom":
                p = None
            else:
                vol = 0.05 if 10 <= users <= 25 else 0.10 if 26 <= users <= 50 else 0
                disc = self.pricing_matrix["contract_discounts"].get(contract_type, 0)
                p = round(price * (1 - vol) * (1 - disc), 2)
            recs.append({"tier": tier_id, "name": tier["name"], "price": p, "contract_type": contract_type, "features": tier["features"]})
        return {"recommendations": recs}

    def schedule_demo(self, preferred_times: List[str] = None) -> Dict[str, Any]:
        avail = [s for s in self.demo_slots if s["available"]]
        if preferred_times:
            from datetime import datetime as dt
            for pt in preferred_times:
                pref = dt.fromisoformat(pt)
                for s in avail:
                    sd = dt.fromisoformat(s["datetime"])
                    if abs((sd - pref).total_seconds()) < 3600:
                        s["available"] = False
                        return {"status": "scheduled", "datetime": s["datetime"], "duration": s["duration"], "meeting_link": f"https://meet.techcorp.com/demo/{int(sd.timestamp())}"}
        return {"status": "options", "available_slots": avail[:5], "booking_link": "https://calendar.techcorp.com/sales-demo"}

    def _process_specific(self, message: str, context: Dict[str, Any] = None) -> Any:
        t = message.lower()
        ctx = context or {}
        if "price" in t or "cost" in t or "pricing" in t:
            req = {"users": ctx.get("users", 10), "features": ctx.get("features", []), "contract_type": "annual" if "annual" in t else "monthly"}
            return self.handle_pricing_inquiry(req)
        if "demo" in t:
            return self.schedule_demo(ctx.get("preferred_times"))
        return {"response": "Happy to help with plans, pricing, or demos. Let me know your team size and goals."}
