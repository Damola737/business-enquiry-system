# scripts/demo_run.py
import os, sys, json

# --- Make project root importable when running from scripts/ ---
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from main import BusinessEnquirySystem  # noqa: E402


def run_demo():
    system = BusinessEnquirySystem()
    test_enquiries = [
        {"text": "I'm interested in your Professional plan. What are the features and price? Can we get a demo?", "customer_info": {"name": "Ava", "tier": "professional"}},
        {"text": "I'm getting error 429 when calling /analytics. It's urgent and breaking our dashboard.", "customer_info": {"name": "Noah", "tier": "basic"}},
        {"text": "I want to upgrade my plan but I'm having technical issues and need to update my billing information", "customer_info": {"name": "Liam", "account_type": "basic"}}
    ]
    for e in test_enquiries:
        print("\n" + "="*72)
        print("ENQUIRY:", e["text"])
        print("="*72)
        result = system.process_enquiry(e["text"], e.get("customer_info"))
        fr = result.get("final_response")
        if isinstance(fr, dict) and "result" in fr:
            print(fr["result"].get("response", json.dumps(fr, indent=2)))
        elif isinstance(fr, dict):
            print(json.dumps(fr, indent=2))
        else:
            print(fr)
        print("\nAgents involved:", ", ".join(result["agents_involved"]))
        print("Status:", result["status"])

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("WARNING: OPENAI_API_KEY not set; LLM calls may not run.")
    run_demo()
