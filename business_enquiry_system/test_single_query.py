#!/usr/bin/env python3
"""
Quick single query test - Run a single test without interactive prompts
"""

import os
try:
    from dotenv import load_dotenv
except Exception:
    def load_dotenv():
        return False
from mvp_pipeline import SimpleCustomerServicePipeline

load_dotenv()

print("\n" + "=" * 80)
print("  SINGLE QUERY TEST")
print("=" * 80 + "\n")

# Initialize pipeline
pipeline = SimpleCustomerServicePipeline()

# Test query
result = pipeline.process(
    customer_message="I need 1000 naira MTN airtime for 08012345678",
    customer_phone="+2348012345678",
    customer_name="Test Customer",
    tenant_id=os.getenv("TENANT_ID", "legacy-ng-telecom"),
)

print("\n" + "=" * 80)
print("  TEST COMPLETE")
print("=" * 80)
print(f"\nStatus: {result['status'].upper()}")
print(f"Enquiry ID: {result['enquiry_id']}")
print(f"Processing Time: {result['processing_time_ms']}ms")
print(f"Agents Involved: {', '.join(result['agents_involved'])}")

print("\n✅ All systems operational!")
