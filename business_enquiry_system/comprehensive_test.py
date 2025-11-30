#!/usr/bin/env python3
"""
Comprehensive test of all agent capabilities
"""

import os
from dotenv import load_dotenv
from mvp_pipeline import SimpleCustomerServicePipeline
import time

load_dotenv()

def run_test(pipeline, test_num, test_name, message, phone, name):
    """Run a single test case."""
    print(f"\n{'=' * 80}")
    print(f"TEST {test_num}: {test_name}")
    print(f"{'=' * 80}\n")

    start = time.time()
    result = pipeline.process(
        customer_message=message,
        customer_phone=phone,
        customer_name=name,
        tenant_id=os.getenv("TENANT_ID", "legacy-ng-telecom"),
    )
    duration = time.time() - start

    print(f"\n{'─' * 80}")
    print(f"✅ Test completed in {duration:.2f}s")
    print(f"Status: {result['status'].upper()}")
    print(f"Domain: {result['classification']['service_domain']}")
    print(f"Processing time: {result['processing_time_ms']}ms")
    print(f"{'─' * 80}")

    return result

def main():
    print("\n" + "=" * 80)
    print("  COMPREHENSIVE AGENT TESTING")
    print("=" * 80)

    pipeline = SimpleCustomerServicePipeline()

    tests = [
        {
            "name": "Simple Airtime Purchase",
            "message": "I need 1000 naira MTN airtime for 08012345678",
            "phone": "+2348012345678",
            "customer_name": "Chinedu Okafor"
        },
        {
            "name": "Bulk Airtime with Discount",
            "message": "Send me 15000 naira Airtel airtime to 08098765432",
            "phone": "+2348123456789",
            "customer_name": "Amina Bello"
        },
        {
            "name": "Different Network (Glo)",
            "message": "Buy 2000 naira Glo credit for 07012345678",
            "phone": "+2347012345678",
            "customer_name": "Emeka Nwosu"
        },
        {
            "name": "Question About Pricing",
            "message": "How much is 5000 naira airtime?",
            "phone": "+2348087654321",
            "customer_name": "Fatima Abdullahi"
        },
        {
            "name": "Power Token Guidance (EKEDC)",
            "message": "I want to buy 5000 naira EKEDC electricity token, meter 12345678901",
            "phone": "+2348011223344",
            "customer_name": "Ibrahim Mohammed"
        }
    ]

    results = []

    for i, test in enumerate(tests, 1):
        result = run_test(
            pipeline, i, test["name"],
            test["message"], test["phone"], test["customer_name"]
        )
        results.append(result)

        if i < len(tests):
            print("\n⏳ Waiting 2 seconds before next test...")
            time.sleep(2)

    # Summary
    print("\n\n" + "=" * 80)
    print("  TEST SUMMARY")
    print("=" * 80)

    for i, (test, result) in enumerate(zip(tests, results), 1):
        status_icon = "✅" if result['status'] == 'completed' else "⚠️"
        print(f"\n{i}. {test['name']}")
        print(f"   {status_icon} Status: {result['status'].upper()}")
        print(f"   Domain: {result['classification']['service_domain']}")
        print(f"   Intent: {result['classification']['intent']}")
        print(f"   Processing: {result['processing_time_ms']}ms")

    # Agent Metrics
    print("\n\n" + "=" * 80)
    print("  AGENT PERFORMANCE METRICS")
    print("=" * 80)

    metrics = pipeline.get_metrics()
    for agent_name, agent_metrics in metrics.items():
        print(f"\n{agent_name}:")
        print(f"   Total requests: {agent_metrics['total_requests']}")
        print(f"   Success rate: {agent_metrics['success_rate']}%")
        print(f"   Avg time: {agent_metrics['average_processing_time_ms']:.0f}ms")

    print("\n" + "=" * 80)
    print("  ✅ ALL TESTS COMPLETE")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
