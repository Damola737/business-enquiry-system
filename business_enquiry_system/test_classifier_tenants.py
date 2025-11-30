#!/usr/bin/env python3
"""
Tenant-aware classifier demo

Runs a few sample messages through the config-driven fallback classifier
for three tenants:
- legacy-ng-telecom
- acme-ecommerce
- medicor-health

This is a diagnostic utility to make tenant-specific classification
differences explicit without relying on live LLM calls.
"""

import os
from typing import List, Tuple

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    def load_dotenv():
        return False

from agents.classifier_v2 import ClassifierAgent
from agents.base_agent_v2 import ConversationContext


def build_classifier() -> ClassifierAgent:
    load_dotenv()
    llm_config = {
        "config_list": [{
            "model": "gpt-4o-mini",
            "api_key": os.getenv("OPENAI_API_KEY", "dummy-key")
        }],
        "temperature": 0.1,
    }
    return ClassifierAgent(llm_config)


def run_for_tenant(tenant_key: str, messages: List[str]) -> None:
    print("\n" + "=" * 80)
    print(f"TENANT: {tenant_key}")
    print("=" * 80)

    clf = build_classifier()

    for i, msg in enumerate(messages, 1):
        ctx = ConversationContext(
            tenant_id=tenant_key,
            enquiry_id=f"ENQ-T-{i}",
            session_id="SES-TEST",
            customer_phone="+00000000000",
        )

        # Use the config-driven fallback directly to avoid LLM variability.
        result = clf._fallback_classify(msg, ctx)  # type: ignore[attr-defined]
        classification = result["classification"]

        print(f"\n[{i}] Message: {msg}")
        print("-" * 80)
        print(f"Domain   : {classification['service_domain']}")
        print(f"Intent   : {classification['intent']}")
        print(f"Priority : {classification['priority']}")
        print(f"Sentiment: {classification['sentiment']}")
        print(f"Method   : {result.get('method')}")


def main() -> None:
    messages = [
        # Telecom-style
        "I need 1000 naira MTN airtime for 08012345678",
        # E-commerce-style
        "Where is my order #12345? It was supposed to arrive yesterday.",
        "I want to return a damaged laptop and get a refund.",
        # Healthcare-style
        "I have a headache and mild fever, should I book an appointment?",
        "Is my insurance going to cover this procedure?",
    ]

    tenants = [
        "legacy-ng-telecom",
        "acme-ecommerce",
        "medicor-health",
    ]

    for tenant_key in tenants:
        run_for_tenant(tenant_key, messages)


if __name__ == "__main__":
    main()

