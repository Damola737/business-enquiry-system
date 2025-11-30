#!/usr/bin/env python3
"""
Quick test of the Enhanced CLI features (non-interactive).
"""

import sys
import os
from datetime import datetime

# Test colorama
try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)
    print(f"{Fore.GREEN}✅ Colorama installed and working{Style.RESET_ALL}")
except ImportError:
    print("❌ Colorama not installed")
    sys.exit(1)

# Test enhanced CLI class
try:
    from ui_enhanced_cli import EnhancedCLI
    print(f"{Fore.GREEN}✅ EnhancedCLI module imported successfully{Style.RESET_ALL}")
except Exception as e:
    print(f"{Fore.RED}❌ Failed to import EnhancedCLI: {e}{Style.RESET_ALL}")
    sys.exit(1)

print()
print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
print(f"{Fore.WHITE}{Style.BRIGHT}  ENHANCED CLI FEATURES DEMO{Style.RESET_ALL}")
print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
print()

cli = EnhancedCLI()

# Test banner
print(f"{Fore.YELLOW}Testing banner display...{Style.RESET_ALL}")
cli.print_banner()

# Test classification display
print(f"\n{Fore.YELLOW}Testing classification display...{Style.RESET_ALL}")
test_classification = {
    'service_domain': 'AIRTIME',
    'intent': 'purchase_airtime',
    'priority': 'MEDIUM',
    'sentiment': 'NEUTRAL',
    'confidence': 0.95,
    'entities': {
        'phone_numbers': ['08012345678'],
        'amounts': [1000],
        'networks': ['MTN']
    }
}
cli.print_header("TEST ANALYSIS", "🔍")
cli.print_classification(test_classification)

# Test response formatting
print(f"\n{Fore.YELLOW}Testing response formatting...{Style.RESET_ALL}")
test_response = """ℹ️ Airtime Purchase Guidance

Network: MTN
Recipient: 08012345678
Target Amount: ₦1,000.00

Self‑service link: https://portal.example.com/airtime

Steps:
1) Open the link above
2) Enter the recipient number and amount
3) Review and confirm payment

Tips:
- Minimum ₦50, maximum ₦50,000 per transaction
"""

formatted = cli.format_response(test_response)
print(formatted)

# Test metadata display
print(f"\n{Fore.YELLOW}Testing metadata display...{Style.RESET_ALL}")
test_result = {
    'processing_time_ms': 1234,
    'agents_involved': ['ClassifierAgent', 'AirtimeSalesAgent'],
    'status': 'completed'
}
cli.print_metadata(test_result)

# Test progress bar
print(f"\n{Fore.YELLOW}Testing progress bars...{Style.RESET_ALL}")
for confidence in [0.3, 0.6, 0.9]:
    bar = cli._generate_progress_bar(confidence, width=30)
    print(f"Confidence {confidence:.0%}: {bar}")

print()
print(f"{Fore.GREEN}{'=' * 80}{Style.RESET_ALL}")
print(f"{Fore.GREEN}{Style.BRIGHT}  ✅ ALL ENHANCED CLI FEATURES WORKING!{Style.RESET_ALL}")
print(f"{Fore.GREEN}{'=' * 80}{Style.RESET_ALL}")
print()
print(f"{Fore.CYAN}To run the full interactive CLI, use:{Style.RESET_ALL}")
print(f"{Fore.WHITE}  python ui_enhanced_cli.py{Style.RESET_ALL}")
print()
