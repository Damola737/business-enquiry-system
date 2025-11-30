#!/usr/bin/env python3
"""
Enhanced CLI with beautiful formatting, colors, and progress indicators.
"""

import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any
try:
    from dotenv import load_dotenv
except:
    def load_dotenv(): pass

# Try to import colorama for Windows color support
try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)
    COLORS_AVAILABLE = True
except ImportError:
    # Fallback if colorama not installed
    class Fore:
        RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = RESET = ""
    class Back:
        RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = RESET = ""
    class Style:
        BRIGHT = DIM = NORMAL = RESET_ALL = ""
    COLORS_AVAILABLE = False

from mvp_pipeline import SimpleCustomerServicePipeline


class EnhancedCLI:
    """Beautiful command-line interface with colors and formatting."""

    def __init__(self):
        load_dotenv()
        self.pipeline = None
        self.session_start = datetime.now()
        self.query_count = 0
        # Simple tenant selection via environment variable, with a safe default
        self.tenant_id = os.getenv("TENANT_ID", "legacy-ng-telecom")

    def clear_screen(self):
        """Clear the console screen."""
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_banner(self):
        """Print a beautiful welcome banner."""
        banner = f"""
{Fore.CYAN}{Style.BRIGHT}╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║            {Fore.WHITE}🤖  MULTI-SERVICE AI CUSTOMER SERVICE SYSTEM  🤖{Fore.CYAN}                ║
║                                                                              ║
║                  {Fore.YELLOW}Airtime  •  Power/Electricity  •  Data Bundles{Fore.CYAN}                ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}

{Fore.WHITE}Welcome! I'm your AI assistant for Nigerian mobile and utility services.{Style.RESET_ALL}
{Fore.GREEN}Type your request naturally, and I'll help you with guidance and navigation.{Style.RESET_ALL}

{Style.DIM}💡 Examples:
  • "I need 1000 naira MTN airtime for 08012345678"
  • "Buy me 5000 naira EKEDC token for meter 12345678901"
  • "How much is 10GB data on Airtel?"
  • Type 'help' for more examples, 'quit' to exit{Style.RESET_ALL}
"""
        print(banner)

    def print_separator(self, char="─", width=80, color=Fore.CYAN):
        """Print a separator line."""
        print(f"{color}{char * width}{Style.RESET_ALL}")

    def print_header(self, text: str, emoji: str = ""):
        """Print a section header."""
        print(f"\n{Fore.CYAN}{Style.BRIGHT}{'═' * 80}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}{Style.BRIGHT}  {emoji} {text}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{Style.BRIGHT}{'═' * 80}{Style.RESET_ALL}\n")

    def print_step(self, step_num: int, description: str, status: str = "processing"):
        """Print a processing step with status."""
        status_icons = {
            "processing": f"{Fore.YELLOW}⏳",
            "success": f"{Fore.GREEN}✅",
            "error": f"{Fore.RED}❌",
            "info": f"{Fore.BLUE}ℹ️"
        }
        icon = status_icons.get(status, "•")
        print(f"{icon} {Fore.WHITE}{Style.BRIGHT}Step {step_num}:{Style.RESET_ALL} {description}")

    def print_classification(self, classification: Dict[str, Any]):
        """Print classification results in a beautiful format."""
        domain_colors = {
            "AIRTIME": Fore.GREEN,
            "POWER": Fore.YELLOW,
            "DATA": Fore.BLUE,
            "MULTI": Fore.MAGENTA
        }

        priority_colors = {
            "LOW": Fore.GREEN,
            "MEDIUM": Fore.YELLOW,
            "HIGH": Fore.RED,
            "CRITICAL": Fore.RED + Style.BRIGHT
        }

        sentiment_emoji = {
            "VERY_NEGATIVE": "😡",
            "NEGATIVE": "😟",
            "NEUTRAL": "😐",
            "POSITIVE": "😊"
        }

        domain = classification.get('service_domain', 'UNKNOWN')
        domain_color = domain_colors.get(domain, Fore.WHITE)

        print(f"  {Fore.WHITE}Service Domain:{Style.RESET_ALL} {domain_color}{Style.BRIGHT}{domain}{Style.RESET_ALL}")
        print(f"  {Fore.WHITE}Intent:{Style.RESET_ALL} {classification.get('intent', 'unknown')}")

        priority = classification.get('priority', 'MEDIUM')
        priority_color = priority_colors.get(priority, Fore.WHITE)
        print(f"  {Fore.WHITE}Priority:{Style.RESET_ALL} {priority_color}{priority}{Style.RESET_ALL}")

        sentiment = classification.get('sentiment', 'NEUTRAL')
        emoji = sentiment_emoji.get(sentiment, "")
        print(f"  {Fore.WHITE}Sentiment:{Style.RESET_ALL} {emoji} {sentiment}")

        confidence = classification.get('confidence', 0.0)
        confidence_bar = self._generate_progress_bar(confidence, width=20)
        print(f"  {Fore.WHITE}Confidence:{Style.RESET_ALL} {confidence_bar} {confidence:.0%}")

        # Show entities if present
        entities = classification.get('entities', {})
        if any(entities.values()):
            print(f"\n  {Fore.CYAN}Extracted Information:{Style.RESET_ALL}")
            if entities.get('phone_numbers'):
                print(f"    📱 Phone: {', '.join(entities['phone_numbers'])}")
            if entities.get('amounts'):
                amounts = [f"₦{float(a):,.0f}" for a in entities['amounts']]
                print(f"    💰 Amount: {', '.join(amounts)}")
            if entities.get('networks'):
                print(f"    📡 Network: {', '.join(entities['networks'])}")
            if entities.get('meter_numbers'):
                print(f"    🔌 Meter: {', '.join(entities['meter_numbers'])}")
            if entities.get('discos'):
                print(f"    ⚡ DISCO: {', '.join(entities['discos'])}")

    def _generate_progress_bar(self, value: float, width: int = 20, filled_char: str = "█", empty_char: str = "░") -> str:
        """Generate a visual progress bar."""
        filled = int(value * width)
        empty = width - filled

        if value >= 0.8:
            color = Fore.GREEN
        elif value >= 0.5:
            color = Fore.YELLOW
        else:
            color = Fore.RED

        return f"{color}{filled_char * filled}{Style.DIM}{empty_char * empty}{Style.RESET_ALL}"

    def format_response(self, response: str) -> str:
        """Format the response with nice styling."""
        # Add colors to important parts
        response = response.replace("ℹ️", f"{Fore.BLUE}ℹ️{Style.RESET_ALL}")
        response = response.replace("✅", f"{Fore.GREEN}✅{Style.RESET_ALL}")
        response = response.replace("❌", f"{Fore.RED}❌{Style.RESET_ALL}")
        response = response.replace("⚠️", f"{Fore.YELLOW}⚠️{Style.RESET_ALL}")

        # Highlight URLs
        import re
        response = re.sub(
            r'(https?://[^\s]+)',
            lambda m: f"{Fore.CYAN}{Style.BRIGHT}{m.group(1)}{Style.RESET_ALL}",
            response
        )

        # Highlight amounts
        response = re.sub(
            r'(₦[\d,]+(?:\.\d{2})?)',
            lambda m: f"{Fore.GREEN}{Style.BRIGHT}{m.group(1)}{Style.RESET_ALL}",
            response
        )

        return response

    def print_response(self, result: Dict[str, Any]):
        """Print the final response beautifully."""
        self.print_header("ASSISTANT RESPONSE", "🤖")

        # Format and print response
        response = result.get('final_response', 'No response generated')
        formatted_response = self.format_response(response)

        # Print in a box
        lines = formatted_response.split('\n')
        max_width = max(len(line.replace(Fore.CYAN, '').replace(Fore.GREEN, '').replace(Style.BRIGHT, '').replace(Style.RESET_ALL, '')) for line in lines)
        max_width = min(max_width, 78)

        print(f"{Fore.WHITE}┌{'─' * (max_width + 2)}┐{Style.RESET_ALL}")
        for line in lines:
            print(f"{Fore.WHITE}│{Style.RESET_ALL} {line}")
        print(f"{Fore.WHITE}└{'─' * (max_width + 2)}┘{Style.RESET_ALL}")

    def print_metadata(self, result: Dict[str, Any]):
        """Print processing metadata."""
        print(f"\n{Style.DIM}{'─' * 80}{Style.RESET_ALL}")

        # Processing time with color coding
        proc_time = result.get('processing_time_ms', 0)
        if proc_time < 1000:
            time_color = Fore.GREEN
        elif proc_time < 5000:
            time_color = Fore.YELLOW
        else:
            time_color = Fore.RED

        print(f"{Style.DIM}⏱️  Processing Time: {time_color}{proc_time}ms{Style.RESET_ALL}")

        # Agents involved
        agents = result.get('agents_involved', [])
        if agents:
            agents_str = f"{Fore.CYAN} → {Style.RESET_ALL}".join(agents)
            print(f"{Style.DIM}🤖 Agents: {agents_str}{Style.RESET_ALL}")

        # Status
        status = result.get('status', 'unknown')
        status_color = Fore.GREEN if status == 'completed' else Fore.RED
        print(f"{Style.DIM}📊 Status: {status_color}{status.upper()}{Style.RESET_ALL}")

        # Escalation notice
        if 'escalation_summary' in result:
            print(f"\n{Fore.YELLOW}{Style.BRIGHT}⚠️  This enquiry has been flagged for human review{Style.RESET_ALL}")

        print(f"{Style.DIM}{'─' * 80}{Style.RESET_ALL}\n")

    def show_help(self):
        """Show help message with examples."""
        help_text = f"""
{Fore.CYAN}{Style.BRIGHT}HOW TO USE THIS SYSTEM{Style.RESET_ALL}

{Fore.GREEN}📱 AIRTIME EXAMPLES:{Style.RESET_ALL}
  • "I need 1000 naira MTN airtime for 08012345678"
  • "Send me 2000 naira Airtel airtime"
  • "Buy 500 naira Glo credit"
  • "How much is 5000 naira airtime?"

{Fore.YELLOW}⚡ POWER/ELECTRICITY EXAMPLES:{Style.RESET_ALL}
  • "Buy me 5000 naira EKEDC token for meter 12345678901"
  • "I need 10000 naira IKEDC electricity"
  • "How do I buy prepaid token?"

{Fore.BLUE}📶 DATA BUNDLE EXAMPLES:{Style.RESET_ALL}
  • "I want 10GB MTN data"
  • "How much is 5GB Airtel bundle?"
  • "Recommend data plan for heavy usage"

{Fore.WHITE}COMMANDS:{Style.RESET_ALL}
  • {Fore.CYAN}help{Style.RESET_ALL}    - Show this help message
  • {Fore.CYAN}clear{Style.RESET_ALL}   - Clear the screen
  • {Fore.CYAN}stats{Style.RESET_ALL}   - Show session statistics
  • {Fore.CYAN}quit{Style.RESET_ALL}    - Exit the program

{Style.DIM}💡 Tip: Just type naturally! The AI will understand your request.{Style.RESET_ALL}
"""
        print(help_text)

    def show_stats(self):
        """Show session statistics."""
        duration = (datetime.now() - self.session_start).total_seconds()
        minutes = int(duration // 60)
        seconds = int(duration % 60)

        stats = f"""
{Fore.CYAN}{Style.BRIGHT}SESSION STATISTICS{Style.RESET_ALL}

  {Fore.WHITE}Queries Processed:{Style.RESET_ALL} {Fore.GREEN}{self.query_count}{Style.RESET_ALL}
  {Fore.WHITE}Session Duration:{Style.RESET_ALL} {minutes}m {seconds}s
  {Fore.WHITE}Started:{Style.RESET_ALL} {self.session_start.strftime('%H:%M:%S')}
"""

        if self.pipeline and self.query_count > 0:
            try:
                metrics = self.pipeline.get_metrics()
                stats += f"\n{Fore.CYAN}  AGENT PERFORMANCE:{Style.RESET_ALL}\n"
                for agent_name, agent_metrics in metrics.items():
                    success_rate = agent_metrics.get('success_rate', 0)
                    color = Fore.GREEN if success_rate >= 90 else Fore.YELLOW if success_rate >= 70 else Fore.RED
                    stats += f"    • {agent_name}: {color}{success_rate:.0f}%{Style.RESET_ALL} success\n"
            except:
                pass

        print(stats)

    def run(self):
        """Run the enhanced CLI."""
        self.clear_screen()
        self.print_banner()

        # Initialize pipeline with loading indicator
        print(f"{Fore.YELLOW}⏳ Initializing AI agents...{Style.RESET_ALL}", end="", flush=True)
        try:
            self.pipeline = SimpleCustomerServicePipeline()
            print(f"\r{Fore.GREEN}✅ AI agents ready!{' ' * 30}{Style.RESET_ALL}")
        except Exception as e:
            print(f"\r{Fore.RED}❌ Failed to initialize: {e}{Style.RESET_ALL}")
            return

        print()
        self.print_separator()

        # Main interaction loop
        while True:
            try:
                # Prompt
                prompt = f"\n{Fore.CYAN}{'>' * 3}{Style.RESET_ALL} "
                user_input = input(prompt).strip()

                if not user_input:
                    continue

                # Handle commands
                cmd = user_input.lower()
                if cmd in ['quit', 'exit', 'q']:
                    print(f"\n{Fore.YELLOW}👋 Thank you for using our service! Goodbye!{Style.RESET_ALL}\n")
                    break
                elif cmd == 'help':
                    self.show_help()
                    continue
                elif cmd == 'clear':
                    self.clear_screen()
                    self.print_banner()
                    continue
                elif cmd == 'stats':
                    self.show_stats()
                    continue

                # Process query
                self.query_count += 1
                print()  # Blank line

                # Show processing indicator
                print(f"{Fore.YELLOW}⏳ Processing your request...{Style.RESET_ALL}\n")

                # Process through pipeline
                result = self.pipeline.process(
                    customer_message=user_input,
                    customer_phone="+2348012345678",  # Default for demo
                    customer_name="Customer",
                    tenant_id=self.tenant_id
                )

                # Show classification
                self.print_header("ANALYSIS", "🔍")
                self.print_classification(result['classification'])

                # Show response
                print()
                self.print_response(result)

                # Show metadata
                self.print_metadata(result)

            except KeyboardInterrupt:
                print(f"\n\n{Fore.YELLOW}👋 Interrupted. Type 'quit' to exit or continue chatting.{Style.RESET_ALL}\n")
                continue
            except Exception as e:
                print(f"\n{Fore.RED}❌ Error: {e}{Style.RESET_ALL}\n")
                import traceback
                if '--debug' in sys.argv:
                    traceback.print_exc()


def main():
    """Entry point."""
    cli = EnhancedCLI()
    cli.run()


if __name__ == "__main__":
    main()
