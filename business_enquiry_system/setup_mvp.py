#!/usr/bin/env python3
"""
MVP Setup Script
Quick setup and test for the enhanced multi-service system.
"""

import os
import sys
from pathlib import Path


def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")


def check_python_version():
    """Check if Python version is 3.11+."""
    print_header("Checking Python Version")
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")

    if version.major < 3 or (version.major == 3 and version.minor < 11):
        print("❌ ERROR: Python 3.11 or higher is required")
        print("   Please upgrade Python and try again.")
        return False

    print("✅ Python version is compatible")
    return True


def check_env_file():
    """Check if .env file exists."""
    print_header("Checking Environment Configuration")

    if not Path(".env").exists():
        print("⚠️  .env file not found")
        print("   Copying .env.example to .env...")

        if Path(".env.example").exists():
            import shutil
            shutil.copy(".env.example", ".env")
            print("✅ Created .env file from .env.example")
            print("\n📝 IMPORTANT: Edit .env and add your API keys:")
            print("   - OPENAI_API_KEY")
            print("   - Database credentials")
            print("   - Service API keys (MTN, EKEDC, Paystack, etc.)")
            return False
        else:
            print("❌ .env.example not found. Please create .env manually.")
            return False

    print("✅ .env file exists")
    return True


def check_dependencies():
    """Check if required packages are installed."""
    print_header("Checking Dependencies")

    required_packages = [
        "pyautogen",
        "pydantic",
        "python-dotenv",
        "openai"
    ]

    missing = []

    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - NOT INSTALLED")
            missing.append(package)

    if missing:
        print("\n⚠️  Missing packages detected")
        print("   Run: pip install -r requirements_enhanced.txt")
        return False

    print("\n✅ All core dependencies installed")
    return True


def test_imports():
    """Test if custom modules can be imported."""
    print_header("Testing Module Imports")

    try:
        from agents.base_agent_v2 import BaseBusinessAgent, ConversationContext
        print("✅ base_agent_v2 imported successfully")

        from agents.classifier_v2 import ClassifierAgent
        print("✅ classifier_v2 imported successfully")

        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def test_llm_connection():
    """Test connection to OpenAI API."""
    print_header("Testing OpenAI API Connection")

    try:
        from dotenv import load_dotenv
        import openai

        load_dotenv()

        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key or api_key == "sk-your-openai-key-here":
            print("❌ OPENAI_API_KEY not set in .env file")
            print("   Please add your OpenAI API key to .env")
            return False

        # Try a simple API call
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'test'"}],
            max_tokens=5
        )

        print("✅ OpenAI API connection successful")
        print(f"   Model: gpt-4o-mini")
        print(f"   Response: {response.choices[0].message.content}")
        return True

    except Exception as e:
        print(f"❌ OpenAI API connection failed: {e}")
        return False


def run_classifier_test():
    """Run a quick test of the classifier agent."""
    print_header("Testing Classifier Agent")

    try:
        from dotenv import load_dotenv
        from agents.classifier_v2 import ClassifierAgent

        load_dotenv()

        llm_config = {
            "config_list": [{
                "model": "gpt-4o-mini",
                "api_key": os.getenv("OPENAI_API_KEY")
            }],
            "temperature": 0.1
        }

        classifier = ClassifierAgent(llm_config)

        test_message = "I need 1000 naira MTN airtime"

        print(f"Test message: '{test_message}'")
        print("Processing...")

        response = classifier.process_message(test_message)

        if response.success:
            classification = response.result["classification"]
            print("\n✅ Classification successful!")
            print(f"   Domain: {classification['service_domain']}")
            print(f"   Intent: {classification['intent']}")
            print(f"   Priority: {classification['priority']}")
            print(f"   Confidence: {classification['confidence']}")
            print(f"   Processing time: {response.processing_time_ms}ms")
            return True
        else:
            print(f"❌ Classification failed: {response.error}")
            return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_directory_structure():
    """Create necessary directories."""
    print_header("Creating Directory Structure")

    directories = [
        "logs",
        "database",
        "knowledge_base/airtime",
        "knowledge_base/power",
        "knowledge_base/data",
        "tests",
    ]

    for directory in directories:
        path = Path(directory)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            print(f"✅ Created: {directory}/")
        else:
            print(f"✓  Exists: {directory}/")


def main():
    """Run all setup checks."""
    print("🚀 Multi-Service Customer Service System - MVP Setup")

    all_passed = True

    # Run checks
    if not check_python_version():
        all_passed = False

    create_directory_structure()

    if not check_env_file():
        all_passed = False
        print("\n⚠️  Please configure .env file and run this script again")
        return

    if not check_dependencies():
        all_passed = False
        print("\n⚠️  Please install dependencies and run this script again")
        return

    if not test_imports():
        all_passed = False
        return

    if not test_llm_connection():
        all_passed = False
        print("\n⚠️  Please fix OpenAI API configuration")
        return

    if not run_classifier_test():
        all_passed = False

    # Final summary
    print_header("Setup Summary")

    if all_passed:
        print("✅ All checks passed!")
        print("\n🎉 Your system is ready for development!")
        print("\nNext steps:")
        print("1. Review ENHANCED_SYSTEM_DESIGN.md for architecture details")
        print("2. Follow IMPLEMENTATION_QUICKSTART.md for day-by-day guide")
        print("3. Test with: python agents/classifier_v2.py")
        print("4. Build additional agents following the base_agent_v2 pattern")
    else:
        print("⚠️  Some checks failed")
        print("   Please resolve the issues above and run setup again")

    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()
