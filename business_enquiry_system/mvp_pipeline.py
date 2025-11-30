#!/usr/bin/env python3
"""
MVP Pipeline - Simple Sequential Processing
Demonstrates the complete flow from customer message to response.
"""

import os
import sys
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any
try:
    from dotenv import load_dotenv
except Exception:
    def load_dotenv():
        return False

# Import our agents
from agents.base_agent_v2 import ConversationContext
from agents.classifier_v2 import ClassifierAgent
from agents.specialists.airtime_sales_agent_v2 import AirtimeSalesAgent
from agents.specialists.power_sales_agent_v2 import PowerSalesAgent
from agents.specialists.data_sales_agent_v2 import DataSalesAgent
from agents.generic_agents import (
    ProductInquiryAgent,
    TransactionGuidanceAgent,
    TroubleshootingAgent,
)
from agents.research_agent import ResearchAgent
from agents.escalation_formatter import build_escalation_summary


class SimpleCustomerServicePipeline:
    """
    Simple sequential pipeline for MVP.

    Flow:
    1. ClassifierAgent → Classify message
    2. Route to appropriate specialist (AirtimeSalesAgent for now)
    3. Generate response
    """

    def __init__(self):
        load_dotenv()

        # LLM configuration
        self.llm_config = {
            "config_list": [{
                "model": "gpt-4o-mini",
                "api_key": os.getenv("OPENAI_API_KEY")
            }],
            "temperature": 0.3
        }

        # Initialize agents
        print("Initializing agents...")
        self.classifier = ClassifierAgent(self.llm_config)
        self.airtime_agent = AirtimeSalesAgent(self.llm_config)
        self.power_agent = PowerSalesAgent(self.llm_config)
        self.data_agent = DataSalesAgent(self.llm_config)
        # Generic, tenant-agnostic agents for non-telecom domains
        self.product_agent = ProductInquiryAgent(self.llm_config)
        self.transaction_agent = TransactionGuidanceAgent(self.llm_config)
        self.troubleshooting_agent = TroubleshootingAgent(self.llm_config)
        self.research_agent = ResearchAgent(self.llm_config, knowledge_base_path="./knowledge_base")

        print("✅ Pipeline ready")

    def process(
        self,
        customer_message: str,
        customer_phone: str,
        customer_name: str = None,
        tenant_id: str = "legacy-ng-telecom"
    ) -> Dict[str, Any]:
        """
        Process customer message through the pipeline.

        Args:
            customer_message: Customer's message
            customer_phone: Customer's phone number
            customer_name: Customer's name (optional)

        Returns:
            Complete processing result
        """
        start_time = datetime.now()

        # Print header
        self._print_header("PROCESSING CUSTOMER ENQUIRY")
        print(f"Customer: {customer_name or customer_phone}")
        print(f"Message: {customer_message}")
        print()

        # Create conversation context
        context = ConversationContext(
            tenant_id=tenant_id,
            enquiry_id=f"ENQ-{uuid.uuid4().hex[:12].upper()}",
            session_id=f"SES-{uuid.uuid4().hex[:8].upper()}",
            customer_phone=customer_phone,
            customer_name=customer_name,
            created_at=start_time,
            updated_at=start_time
        )

        # Step 1: Classification
        self._print_step(1, "Classifying message")
        classification_response = self.classifier.process_message(customer_message, context)

        if not classification_response.success:
            return self._error_response(
                context,
                "Classification failed",
                classification_response.error
            )

        classification = classification_response.result["classification"]

        print(f"   Domain: {classification['service_domain']}")
        print(f"   Intent: {classification['intent']}")
        print(f"   Priority: {classification['priority']}")
        print(f"   Sentiment: {classification['sentiment']}")
        print(f"   Confidence: {classification['confidence']}")
        print()

        # Optional: KB research (for richer answers)
        research_block = ""
        try:
            research_resp = self.research_agent.process_message(
                customer_message,
                {
                    "domain": classification["service_domain"],
                    "tenant_id": tenant_id,
                },
            )
            if research_resp and research_resp.get("success"):
                res = research_resp.get("result", {})
                results = res.get("results", [])
                if results:
                    top = results[:3]
                    bullets = "\n".join(f"• {r.get('title','Doc')}" for r in top)
                    research_block = f"\n\nHelpful Resources:\n{bullets}"
        except Exception:
            pass

        # Step 2: Route to specialist
        self._print_step(2, "Routing to specialist agent")

        specialist_response = self._route_to_specialist(
            service_domain=classification["service_domain"],
            tenant_id=tenant_id,
            customer_message=customer_message,
            context=context,
        )

        print()

        # Step 3: Generate final response
        self._print_step(3, "Generating final response")

        if specialist_response and specialist_response.success:
            final_response = specialist_response.result.get("response", "Processing completed")
            if research_block:
                final_response = f"{final_response}{research_block}"
        else:
            final_response = specialist_response.error if specialist_response else "Unable to process request"

        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        # Build complete result
        result = {
            "enquiry_id": context.enquiry_id,
            "session_id": context.session_id,
            "customer_phone": customer_phone,
            "customer_name": customer_name,
            "original_message": customer_message,

            # Classification
            "classification": classification,

            # Processing
            "agents_involved": context.agents_involved,
            "processing_steps": context.processing_steps,
            "processing_time_ms": int(processing_time),

            # Response
            "final_response": final_response,
            "status": "completed" if specialist_response.success else "failed",

            # Metadata
            "timestamp": datetime.now().isoformat()
        }

        # Add escalation summary if specialist suggested
        try:
            if getattr(specialist_response, "success", False):
                payload = specialist_response.result if isinstance(specialist_response.result, dict) else {}
                esc = payload.get("escalation", {}) if isinstance(payload, dict) else {}
                if esc.get("suggested"):
                    result["escalation_summary"] = build_escalation_summary(
                        enquiry_id=context.enquiry_id,
                        original_message=customer_message,
                        classification=classification,
                        specialist_output=payload,
                        customer={"name": customer_name, "phone": customer_phone}
                    )
        except Exception:
            pass

        # Print final response
        self._print_header("FINAL RESPONSE")
        print(final_response)
        print()
        print(f"Processing time: {int(processing_time)}ms")
        print(f"Agents involved: {', '.join(context.agents_involved)}")
        print(f"Status: {result['status'].upper()}")

        return result

    def _placeholder_response(self, message: str) -> Any:
        """Create placeholder response for unimplemented features."""
        class PlaceholderResponse:
            def __init__(self, msg):
                self.success = True
                self.result = {"response": msg}
                self.error = None

        return PlaceholderResponse(message)

    def _error_response(
        self,
        context: ConversationContext,
        error_type: str,
        error_message: str
    ) -> Dict[str, Any]:
        """Create error response."""
        return {
            "enquiry_id": context.enquiry_id,
            "session_id": context.session_id,
            "status": "error",
            "error_type": error_type,
            "error_message": error_message,
            "final_response": f"We encountered an error processing your request. Please try again or contact support. (Error: {error_type})",
            "timestamp": datetime.now().isoformat()
        }

    def _print_header(self, text: str):
        """Print formatted header."""
        print("\n" + "=" * 80)
        print(f"  {text}")
        print("=" * 80 + "\n")

    def _print_step(self, step_num: int, description: str):
        """Print step header."""
        print(f"STEP {step_num}: {description}")
        print("-" * 80)

    # ============================================================
    # Routing logic
    # ============================================================

    def _route_to_specialist(
        self,
        service_domain: str,
        tenant_id: str,
        customer_message: str,
        context: ConversationContext,
    ):
        """
        Route a request to the appropriate specialist agent based on
        tenant and classified service_domain.

        For the legacy telecom tenant we preserve the original mapping
        (AIRTIME/POWER/DATA). For newer tenants we use the generic agents.
        """
        sd = (service_domain or "").upper()
        tenant = (tenant_id or "legacy-ng-telecom")

        # Legacy Nigerian telecom behavior (unchanged)
        if tenant == "legacy-ng-telecom":
            if sd == "AIRTIME":
                print("   → Routing to AirtimeSalesAgent")
                return self.airtime_agent.process_message(customer_message, context)
            if sd == "POWER":
                print("   → Routing to PowerSalesAgent")
                return self.power_agent.process_message(customer_message, context)
            if sd == "DATA":
                print("   → Routing to DataSalesAgent")
                return self.data_agent.process_message(customer_message, context)

        # E-commerce example: Acme Online Store
        if tenant == "acme-ecommerce":
            if sd == "PRODUCT_INQUIRY":
                print("   → Routing to ProductInquiryAgent")
                return self.product_agent.process_message(customer_message, context)
            if sd in ("ORDER_SUPPORT", "PAYMENTS_BILLING"):
                print("   → Routing to TransactionGuidanceAgent")
                return self.transaction_agent.process_message(customer_message, context)
            # Fallback: generic transaction guidance
            print(f"   → Domain '{sd}' not explicitly mapped, using TransactionGuidanceAgent")
            return self.transaction_agent.process_message(customer_message, context)

        # Healthcare example: Medicor Health
        if tenant == "medicor-health":
            if sd == "APPOINTMENTS":
                print("   → Routing to TransactionGuidanceAgent (appointments)")
                return self.transaction_agent.process_message(customer_message, context)
            if sd == "SYMPTOMS_TRIAGE":
                print("   → Routing to TroubleshootingAgent (symptoms)")
                return self.troubleshooting_agent.process_message(customer_message, context)
            if sd == "BILLING_INSURANCE":
                print("   → Routing to TransactionGuidanceAgent (billing/insurance)")
                return self.transaction_agent.process_message(customer_message, context)
            print(f"   → Domain '{sd}' not explicitly mapped, using TroubleshootingAgent")
            return self.troubleshooting_agent.process_message(customer_message, context)

        # Default: if tenant is unknown, fall back to telecom mapping where possible,
        # otherwise generic troubleshooting so the user still gets a helpful response.
        print(f"   → Tenant '{tenant}' or domain '{sd}' not recognized; using generic TroubleshootingAgent")
        return self.troubleshooting_agent.process_message(customer_message, context)

    def get_metrics(self) -> Dict[str, Any]:
        """Get metrics from all agents."""
        return {
            "classifier": self.classifier.get_metrics(),
            "airtime_agent": self.airtime_agent.get_metrics(),
            "power_agent": self.power_agent.get_metrics(),
            "data_agent": self.data_agent.get_metrics(),
        }


# ============================================================
# DEMO / TESTING
# ============================================================

def run_demo():
    """Run demo with test cases."""
    print("\n" + "=" * 80)
    print("  MULTI-SERVICE CUSTOMER SERVICE SYSTEM - MVP DEMO")
    print("=" * 80)

    pipeline = SimpleCustomerServicePipeline()

    # Test cases
    test_cases = [
        {
            "name": "Simple Airtime Purchase",
            "message": "I need 1000 naira MTN airtime for 08012345678",
            "phone": "+2347012345678",
            "customer_name": "Chinedu Okafor"
        },
        {
            "name": "Bulk Airtime Purchase",
            "message": "Send me 15000 naira Airtel airtime to 08098765432",
            "phone": "+2348123456789",
            "customer_name": "Amina Bello"
        },
        {
            "name": "Power Token Request (Not Yet Implemented)",
            "message": "Buy me 5000 naira EKEDC token for meter 12345678901",
            "phone": "+2348012345678",
            "customer_name": "Emeka Nwosu"
        },
        {
            "name": "Data Bundle Request (Not Yet Implemented)",
            "message": "How much is 10GB data on MTN?",
            "phone": "+2347098765432",
            "customer_name": "Fatima Abdullahi"
        },
    ]

    results = []

    for i, test in enumerate(test_cases, 1):
        print(f"\n{'=' * 80}")
        print(f"TEST CASE {i}: {test['name']}")
        print(f"{'=' * 80}\n")

        result = pipeline.process(
            customer_message=test["message"],
            customer_phone=test["phone"],
            customer_name=test["customer_name"]
        )

        results.append({
            "test_name": test["name"],
            "result": result
        })

        print("\n" + "-" * 80)
        input("Press Enter to continue to next test...")

    # Print summary
    print("\n" + "=" * 80)
    print("  TEST SUMMARY")
    print("=" * 80)

    for i, test_result in enumerate(results, 1):
        print(f"\n{i}. {test_result['test_name']}")
        print(f"   Status: {test_result['result']['status'].upper()}")
        print(f"   Processing time: {test_result['result']['processing_time_ms']}ms")
        print(f"   Domain: {test_result['result']['classification']['service_domain']}")

    # Print agent metrics
    print("\n" + "=" * 80)
    print("  AGENT METRICS")
    print("=" * 80)

    metrics = pipeline.get_metrics()
    for agent_name, agent_metrics in metrics.items():
        print(f"\n{agent_name}:")
        print(f"   Total requests: {agent_metrics['total_requests']}")
        print(f"   Success rate: {agent_metrics['success_rate']}%")
        print(f"   Avg processing time: {agent_metrics['average_processing_time_ms']}ms")

    print("\n" + "=" * 80)
    print("  DEMO COMPLETE")
    print("=" * 80 + "\n")


def run_interactive():
    """Run interactive mode."""
    print("\n" + "=" * 80)
    print("  INTERACTIVE MODE")
    print("=" * 80)
    print("\nType your message and press Enter. Type 'quit' to exit.\n")

    pipeline = SimpleCustomerServicePipeline()

    while True:
        try:
            message = input("\n👤 Customer: ").strip()

            if message.lower() in ['quit', 'exit', 'q']:
                print("\nGoodbye!")
                break

            if not message:
                continue

            # Process message
            result = pipeline.process(
                customer_message=message,
                customer_phone="+2348012345678",  # Default test number
                customer_name="Test Customer"
            )

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MVP Pipeline for Multi-Service Customer Service")
    parser.add_argument(
        "--mode",
        choices=["demo", "interactive"],
        default="demo",
        help="Run mode: demo (automated tests) or interactive (manual testing)"
    )

    args = parser.parse_args()

    if args.mode == "demo":
        run_demo()
    else:
        run_interactive()
