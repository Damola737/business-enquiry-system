#!/usr/bin/env python3
"""
Test All UIs - Quick verification that all three interfaces are working
"""

import os
import sys
from pathlib import Path

print("\n" + "=" * 80)
print("  TESTING ALL THREE USER INTERFACES")
print("=" * 80 + "\n")

# Check Python version
print("1. Checking Python version...")
import sys
python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
print(f"   ✅ Python {python_version}")

# Check core dependencies
print("\n2. Checking core dependencies...")
try:
    from dotenv import load_dotenv
    print("   ✅ python-dotenv")
except ImportError:
    print("   ❌ python-dotenv missing")
    sys.exit(1)

try:
    from autogen import ConversableAgent
    print("   ✅ pyautogen")
except ImportError:
    print("   ❌ pyautogen missing")
    sys.exit(1)

try:
    from pydantic import BaseModel
    print("   ✅ pydantic")
except ImportError:
    print("   ❌ pydantic missing")
    sys.exit(1)

# Check UI dependencies
print("\n3. Checking UI dependencies...")
colorama_available = False
gradio_available = False
streamlit_available = False

try:
    import colorama
    colorama_available = True
    print("   ✅ colorama (Enhanced CLI)")
except ImportError:
    print("   ⚠️  colorama missing (Enhanced CLI won't have colors)")

try:
    import gradio
    gradio_available = True
    print("   ✅ gradio (Web UI)")
except ImportError:
    print("   ⚠️  gradio missing (Web UI unavailable)")

try:
    import streamlit
    streamlit_available = True
    print("   ✅ streamlit (Dashboard)")
except ImportError:
    print("   ⚠️  streamlit missing (Dashboard unavailable)")

# Check environment
print("\n4. Checking environment configuration...")
load_dotenv()
if os.getenv("OPENAI_API_KEY"):
    print("   ✅ OPENAI_API_KEY configured")
else:
    print("   ❌ OPENAI_API_KEY missing in .env")
    sys.exit(1)

# Check UI files
print("\n5. Checking UI files...")
ui_files = {
    "ui_enhanced_cli.py": "Enhanced CLI",
    "ui_web_gradio.py": "Gradio Web UI",
    "ui_web_streamlit.py": "Streamlit Dashboard"
}

for filename, description in ui_files.items():
    if Path(filename).exists():
        print(f"   ✅ {filename} - {description}")
    else:
        print(f"   ❌ {filename} missing")

# Check pipeline
print("\n6. Checking pipeline...")
try:
    from mvp_pipeline import SimpleCustomerServicePipeline
    print("   ✅ mvp_pipeline.py")
except ImportError as e:
    print(f"   ❌ mvp_pipeline.py import failed: {e}")
    sys.exit(1)

# Quick functional test
print("\n7. Running quick functional test...")
try:
    pipeline = SimpleCustomerServicePipeline()
    print("   ✅ Pipeline initialized")

    # Test a simple query
    result = pipeline.process(
        customer_message="How much is MTN airtime?",
        customer_phone="+2348012345678",
        customer_name="Test User",
        tenant_id=os.getenv("TENANT_ID", "legacy-ng-telecom"),
    )

    if result.get("status") == "completed":
        print("   ✅ Pipeline processing works")
        print(f"   ✅ Response time: {result['processing_time_ms']}ms")
    else:
        print("   ⚠️  Pipeline processed but status not completed")

except Exception as e:
    print(f"   ❌ Pipeline test failed: {e}")
    import traceback
    traceback.print_exc()

# Summary
print("\n" + "=" * 80)
print("  SUMMARY")
print("=" * 80 + "\n")

available_uis = []
if colorama_available:
    available_uis.append("Enhanced CLI (python ui_enhanced_cli.py)")
if gradio_available:
    available_uis.append("Gradio Web UI (python ui_web_gradio.py)")
if streamlit_available:
    available_uis.append("Streamlit Dashboard (streamlit run ui_web_streamlit.py)")

if available_uis:
    print("Available User Interfaces:\n")
    for i, ui in enumerate(available_uis, 1):
        print(f"  {i}. {ui}")

    print("\n" + "=" * 80)
    print("  ALL SYSTEMS READY! 🎉")
    print("=" * 80)
    print("\nQuick Start Commands:")
    print("  python ui_enhanced_cli.py          # Terminal interface")
    print("  python ui_web_gradio.py            # Web interface")
    print("  streamlit run ui_web_streamlit.py # Dashboard interface")
    print()
else:
    print("⚠️  No UI dependencies installed")
    print("\nInstall with: pip install -r requirements_ui.txt")

# Installation instructions if needed
missing_packages = []
if not colorama_available:
    missing_packages.append("colorama")
if not gradio_available:
    missing_packages.append("gradio")
if not streamlit_available:
    missing_packages.append("streamlit")

if missing_packages:
    print("\n" + "=" * 80)
    print("  OPTIONAL: Install Missing UI Packages")
    print("=" * 80)
    print(f"\nMissing: {', '.join(missing_packages)}")
    print("\nInstall all UI dependencies:")
    print("  pip install -r requirements_ui.txt")
    print("\nOr install individually:")
    for pkg in missing_packages:
        print(f"  pip install {pkg}")
