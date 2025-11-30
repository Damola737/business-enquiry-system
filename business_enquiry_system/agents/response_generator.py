# agents/response_generator.py
"""
Response Generator Agent Module
Compiles and formats final responses for customers
"""

from typing import Dict, Any
from datetime import datetime
from agents.base_agent import BaseBusinessAgent
import re


class ResponseGeneratorAgent(BaseBusinessAgent):
    """
    Response Generator agent that compiles and formats final customer responses
    """

    SYSTEM_MESSAGE = """You are the Response Generator Agent for TechCorp Solutions.
    Compile info from agents, produce a clear professional response, mark completion with RESPONSE_COMPLETE.
    """

    def __init__(self, llm_config: Dict[str, Any]):
        super().__init__(
            name="response_generator",
            system_message=self.SYSTEM_MESSAGE,
            llm_config=llm_config,
            description="Compiles and formats final responses for customers"
        )
        self.response_templates = self._load_response_templates()
        self.tone_profiles = self._initialize_tone_profiles()
        self.generated_responses = []

    def _load_response_templates(self) -> Dict[str, str]:
        return {
            "standard": """
{greeting}

Thank you for contacting TechCorp Solutions. {acknowledgment}

{main_content}

{resources}

{next_steps}

{closing}

Best regards,
TechCorp Support Team

---
Need further assistance? Contact us at support@techcorp.com or call 1-800-TECH-HELP
            """.strip(),
            "technical_issue": """
{greeting}

Thank you for reporting this technical issue. {acknowledgment}

**Issue Summary:**
{issue_summary}

**Resolution Steps:**
{resolution_steps}

{resources}

{next_steps}

{closing}

Best regards,
Technical Support Team

---
Still experiencing issues? Our technical team is available 24/7 at tech-support@techcorp.com
            """.strip(),
            "sales_inquiry": """
{greeting}

Thank you for your interest in TechCorp Solutions! {acknowledgment}

**Pricing Options:**
{pricing_details}

{resources}

{next_steps}

{closing}

Best regards,
Sales Team

---
Ready to get started? Schedule a demo at techcorp.com/demo or call our sales team at 1-800-BUY-TECH
            """.strip(),
            "escalation": """
{greeting}

Thank you for your patience. {acknowledgment}

**Escalation Summary:**
Your enquiry has been escalated to our specialist team for immediate attention.

**Reference Number:** {ticket_number}

**What Happens Next:**
1. A senior specialist will review your case within 2 hours
2. You'll receive a detailed response within 24 hours
3. We'll follow up to ensure complete resolution

{closing}

Best regards,
Escalation Team

---
We appreciate your patience and are committed to resolving this matter promptly.
            """.strip()
        }

    def _initialize_tone_profiles(self) -> Dict[str, Dict[str, Any]]:
        return {
            "standard": {"formality": "professional", "empathy": "moderate", "urgency": "normal"},
            "apology": {"formality": "professional", "empathy": "high", "urgency": "high"},
            "sales": {"formality": "friendly", "empathy": "moderate", "urgency": "moderate"},
            "technical": {"formality": "professional", "empathy": "low", "urgency": "normal"},
            "vip": {"formality": "highly professional", "empathy": "high", "urgency": "high"}
        }

    def generate_response(self, enquiry: Dict[str, Any], agent_inputs: Dict[str, Any], customer_info: Dict[str, Any] = None) -> Dict[str, Any]:
        self.logger.info("Generating final response")
        response_type = self._determine_response_type(enquiry, agent_inputs)
        tone_profile = self._select_tone_profile(enquiry, customer_info)
        template = self.response_templates.get(response_type, self.response_templates["standard"])

        content = self._compile_content(agent_inputs, enquiry)
        if customer_info and customer_info.get("name"):
            content["greeting"] = f"Hello {customer_info['name']}"
        content = self._apply_tone(content, tone_profile)

        final = self._format_response(template, content)
        data = {
            "response": final,
            "type": response_type,
            "tone": tone_profile,
            "timestamp": datetime.now().isoformat(),
            "agents_involved": list(agent_inputs.keys()),
            "customer_id": customer_info.get("id") if customer_info else None,
            "enquiry_id": enquiry.get("id"),
            "status": "RESPONSE_COMPLETE"
        }
        self.generated_responses.append({"enquiry_id": enquiry.get("id"), "response_type": response_type, "timestamp": data["timestamp"]})
        self.logger.info(f"Response generated: Type={response_type}")
        return data

    def _determine_response_type(self, enquiry: Dict[str, Any], agent_inputs: Dict[str, Any]) -> str:
        if any("ESCALATION_REQUIRED" in str(v) for v in agent_inputs.values()):
            return "escalation"
        c = enquiry.get("category", "").upper()
        if c == "TECHNICAL": return "technical_issue"
        if c == "SALES": return "sales_inquiry"
        return "standard"

    def _select_tone_profile(self, enquiry: Dict[str, Any], customer_info: Dict[str, Any] = None) -> str:
        if customer_info and (customer_info.get("tier") == "enterprise" or customer_info.get("vip")):
            return "vip"
        s = enquiry.get("sentiment", "neutral")
        if s in ["negative", "very negative"]: return "apology"
        c = enquiry.get("category", "").upper()
        return "technical" if c == "TECHNICAL" else ("sales" if c == "SALES" else "standard")

    def _compile_content(self, agent_inputs: Dict[str, Any], enquiry: Dict[str, Any]) -> Dict[str, str]:
        content = {
            "greeting": "Hello",
            "acknowledgment": f"We've received your enquiry regarding {enquiry.get('intent', 'your concern')}.",
            "main_content": "",
            "resources": "",
            "next_steps": "Please let us know if you need any further assistance.",
            "closing": "Thank you for choosing TechCorp Solutions."
        }

        # Research → resources
        research = agent_inputs.get("research_agent")
        if isinstance(research, dict) and "findings" in research:
            f = research["findings"]
            if f.get("sources"):
                content["resources"] = "**Helpful Resources:**\n" + "\n".join(f"• {s}" for s in f["sources"][:3])

        # Sales → pricing
        sales = agent_inputs.get("sales_agent")
        if isinstance(sales, dict) and "pricing" in sales and "recommendations" in sales["pricing"]:
            recs = sales["pricing"]["recommendations"]
            content["pricing_details"] = "\n".join(f"• {r['name']}: ${r['price']}/month" for r in recs if r.get("price") is not None)

        # Technical → diagnosis & steps
        tech = agent_inputs.get("technical_agent")
        if isinstance(tech, dict):
            if "diagnosis" in tech:
                d = tech["diagnosis"]
                content["issue_summary"] = f"{d.get('summary', 'Issue detected')} (Severity: {d.get('severity', 'medium')})"
                # Fallback: if no solution, show recommended_actions
                if "solution" not in tech and d.get("recommended_actions"):
                    steps = d["recommended_actions"]
                    content["resolution_steps"] = "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps))

            if "solution" in tech:
                s = tech["solution"]
                steps = s.get("detailed_steps") or [s.get("next_step", "Please follow standard troubleshooting.")]
                content["resolution_steps"] = "\n".join(f"{i+1}. {step}" for i, step in enumerate(steps))

        # ⬇⬇⬇ ADD THIS: Billing → action list ⬇⬇⬇
        billing = agent_inputs.get("billing_agent")
        if isinstance(billing, dict) and "billing_actions" in billing:
            actions = billing["billing_actions"]
            if actions:
                content["billing_details"] = "\n".join(f"{i+1}. {a}" for i, a in enumerate(actions))
                
        # Compile main body
        parts = []
        for key in ["issue_summary", "resolution_steps", "pricing_details", "billing_details"]:  # ⬅ add billing_details
            if key in content and content[key]:
                parts.append(content[key])
        content["main_content"] = "\n\n".join(parts) if parts else "We're processing your request."

        return content

    def _apply_tone(self, content: Dict[str, str], tone: str) -> Dict[str, str]:
        profile = self.tone_profiles.get(tone, self.tone_profiles["standard"])
        if profile["formality"] == "highly professional":
            content["greeting"] = "Dear Valued Customer"
            content["closing"] = "With our highest regards,\n" + content["closing"]
        if profile["empathy"] == "high":
            content["acknowledgment"] = "We sincerely understand your concern and " + content["acknowledgment"]
            content["closing"] = "We truly appreciate your patience and understanding. " + content["closing"]
        return content

    def _format_response(self, template: str, content: Dict[str, str]) -> str:
        """
        Render the template using {key} placeholders from `content`.
        - Missing keys render as empty strings.
        - Extra placeholders are removed.
        - Excess blank lines are collapsed.
        """
        import re

        # Replace only placeholders of the form {alnum_}
        def _repl(match: re.Match) -> str:
            key = match.group(1)
            val = content.get(key, "")
            return "" if val is None else str(val)

        # First pass: substitute known placeholders
        response = re.sub(r"\{([A-Za-z0-9_]+)\}", _repl, template)

        # Remove any leftover placeholders like {unknown_key}
        response = re.sub(r"\{[^}]+\}", "", response)

        # Normalize excessive blank lines
        response = re.sub(r"[ \t]+\n", "\n", response)   # trim trailing spaces on lines
        response = re.sub(r"\n{3,}", "\n\n", response)   # collapse 3+ newlines to 2

        return response.strip()

    def _process_specific(self, message: str, context: Dict[str, Any] = None) -> Any:
        if context and "agent_inputs" in context:
            return self.generate_response(context.get("enquiry", {}), context["agent_inputs"], context.get("customer_info"))
        return {"error": "Missing required context for response generation", "required": ["enquiry", "agent_inputs"]}
