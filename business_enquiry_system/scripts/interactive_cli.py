import os, sys, json
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path: sys.path.insert(0, ROOT)
from main import BusinessEnquirySystem

def main():
    be = BusinessEnquirySystem()
    print("Type your enquiry (or 'exit'):\n")
    while True:
        msg = input("> ").strip()
        if msg.lower() in {"exit", "quit"}:
            break
        result = be.process_enquiry(msg, {"name": "Console User"})
        fr = result.get("final_response", {})
        out = (fr.get("result", {}) or {}).get("response") or fr.get("response") or str(fr)
        print("\n--- Reply ---\n" + out + "\n")
        print("Agents:", ", ".join(result.get("agents_involved", [])), "\n")

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("WARNING: OPENAI_API_KEY not set.")
    main()
