# agents/classifier_v2.py
"""
Enhanced Classifier Agent with LLM-powered classification.
Replaces keyword-based classification with true AI reasoning.
"""

import json
import re
from typing import Dict, Any, Optional
try:
    from pydantic import BaseModel, Field  # type: ignore
except Exception:
    class BaseModel:  # type: ignore
        def __init__(self, **data):
            for k, v in data.items():
                setattr(self, k, v)

        def dict(self):
            return self.__dict__

    def Field(default=None, default_factory=None):  # type: ignore
        if default_factory is not None:
            return default_factory()
        return default
from agents.base_agent_v2 import BaseBusinessAgent, ConversationContext
from config.tenant_config_store import TenantConfigStore


# ============================================================
# CLASSIFICATION MODELS
# ============================================================

class ClassificationResult(BaseModel):
    """Structured classification output."""
    service_domain: str  # AIRTIME, POWER, DATA, MULTI, OTHER
    intent: str
    priority: str  # LOW, MEDIUM, HIGH, CRITICAL
    sentiment: str  # VERY_NEGATIVE, NEGATIVE, NEUTRAL, POSITIVE

    entities: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0
    reasoning: str = ""

    class Config:
        json_schema_extra = {
            "example": {
                "service_domain": "AIRTIME",
                "intent": "purchase",
                "priority": "MEDIUM",
                "sentiment": "NEUTRAL",
                "entities": {
                    "phone_numbers": ["+2348012345678"],
                    "amounts": [1000.0],
                    "networks": ["MTN"]
                },
                "confidence": 0.95,
                "reasoning": "Customer wants to purchase MTN airtime"
            }
        }


# ============================================================
# CLASSIFIER AGENT
# ============================================================

class ClassifierAgent(BaseBusinessAgent):
    """
    LLM-powered classification agent for multi-service platform.

    Responsibilities:
    - Classify service domain (AIRTIME, POWER, DATA, MULTI)
    - Determine customer intent (purchase, inquiry, complaint, etc.)
    - Assess priority (LOW, MEDIUM, HIGH, CRITICAL)
    - Analyze sentiment (VERY_NEGATIVE to POSITIVE)
    - Extract entities (phone numbers, amounts, networks, etc.)
    """

    SYSTEM_MESSAGE = """You are an expert classification agent for a Nigerian multi-service customer support platform.

SERVICES WE OFFER:
1. **AIRTIME**: Mobile phone credit/top-ups for MTN, Airtel, Glo, 9Mobile
2. **POWER**: Electricity tokens and billing for DISCOs (EKEDC, IKEDC, AEDC, PHEDC, IBEDC, etc.)
3. **DATA**: Internet data bundles for MTN, Airtel, Glo, 9Mobile

YOUR TASK:
Analyze customer messages and return a JSON classification with:

{
    "service_domain": "AIRTIME" | "POWER" | "DATA" | "MULTI" | "OTHER",
    "intent": "specific intent",
    "priority": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
    "sentiment": "VERY_NEGATIVE" | "NEGATIVE" | "NEUTRAL" | "POSITIVE",
    "entities": {
        "phone_numbers": [],
        "meter_numbers": [],
        "amounts": [],
        "networks": [],
        "discos": []
    },
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}

DOMAIN CLASSIFICATION RULES:
- **AIRTIME**: Keywords: airtime, recharge, credit, top up, vend airtime
  Networks: MTN, Airtel, Glo, 9Mobile, 080, 081, 090, 091, 070
- **POWER**: Keywords: electricity, power, light, NEPA, PHCN, token, meter, bill, units, kWh
  DISCOs: EKEDC, IKEDC, AEDC, PHEDC, IBEDC, EEDC, KEDCO, BEDC, JEDC, AEDC, KAEDCO
- **DATA**: Keywords: data, MB, GB, internet, browsing, bundle, hotspot
- **MULTI**: Message mentions multiple services (e.g., "airtime and data")
- **OTHER**: Doesn't fit any category

INTENT CLASSIFICATION:
- purchase: Buy/get/need service
- inquiry: Questions about pricing, plans, how to use
- complaint: Problem, not working, disappointed, frustrated
- technical_issue: Error, failed, not delivered, delayed
- billing_issue: Wrong charge, refund, dispute, overcharged
- status_check: Check balance, transaction status, history

PRIORITY RULES:
- **CRITICAL**: System down, can't access service, financial loss, legal threats ("lawyer", "sue", "police")
- **HIGH**: Transaction failed with money deducted, urgent need, very angry customer
- **MEDIUM**: Normal purchases, general complaints, standard issues
- **LOW**: Information requests, FAQs, non-urgent inquiries

SENTIMENT INDICATORS:
- **VERY_NEGATIVE**: "scam", "fraud", "terrible", "worst", "useless", "never again", "lawyer", anger/rage
- **NEGATIVE**: "disappointed", "frustrated", "not working", "failed", "poor", "bad"
- **NEUTRAL**: Factual statements, no emotional language
- **POSITIVE**: "thanks", "great", "appreciate", "excellent", "helpful"

ENTITY EXTRACTION:
- **phone_numbers**: Nigerian format (080xxxxxxxx, +234xxxxxxxxxx, 070, 081, 090, 091)
- **meter_numbers**: 11-13 digit numbers (not phone numbers)
- **amounts**: Numbers with "naira", "NGN", "₦", or standalone numbers (50, 1000, 5000, etc.)
- **networks**: MTN, Airtel, Glo, 9Mobile (case-insensitive)
- **discos**: EKEDC, IKEDC, AEDC, etc. (any DISCO name)

IMPORTANT:
- Always respond with VALID JSON only, no extra text
- Confidence should reflect certainty (0.9+ for clear cases, <0.7 for ambiguous)
- Be specific with intent (e.g., "purchase_airtime" not just "purchase")
- Extract ALL entities found in the message
"""

    def __init__(self, llm_config: Dict[str, Any]):
        super().__init__(
            name="ClassifierAgent",
            system_message=self.SYSTEM_MESSAGE,
            llm_config={**llm_config, "temperature": 0.1},  # Low temp for consistency
            description="Classifies customer enquiries by domain, intent, priority, and sentiment"
        )

    def _process_specific(
        self,
        message: str,
        context: Optional[ConversationContext]
    ) -> Dict[str, Any]:
        """
        Classify the customer message using LLM.

        Args:
            message: Customer message to classify
            context: Conversation context (optional)

        Returns:
            Dictionary with classification results
        """
        # Determine tenant and load configuration (for prompt conditioning)
        tenant_id = None
        if context is not None:
            try:
                tenant_id = getattr(context, "tenant_id", None)
            except Exception:
                tenant_id = None
        tenant_cfg = TenantConfigStore.get_instance().get_config(tenant_id or "legacy-ng-telecom")

        tenant_prompt = self._build_tenant_prompt_section(tenant_cfg)

        # Build prompt (message-specific part)
        prompt = f"""{tenant_prompt}
Classify this customer message:

\"{message}\"

Respond with JSON only (no markdown, no extra text):"""

        try:
            # Get LLM response
            response = self.get_llm_response(prompt)

            # Extract and parse JSON
            classification_data = self._extract_and_parse_json(response)

            # Validate classification
            classification = ClassificationResult(**classification_data)

            # Update context if provided
            if context:
                context.service_domain = classification.service_domain
                context.intent = classification.intent
                context.priority = classification.priority
                context.sentiment = classification.sentiment

            return {
                "classification": classification.dict(),
                "raw_response": response,
                "method": "llm"
            }

        except Exception as e:
            self.logger.warning(f"LLM classification failed: {e}. Using fallback.")
            # Fallback to rule-based classification
            return self._fallback_classify(message, context)

    def _build_tenant_prompt_section(self, tenant_cfg: Dict[str, Any]) -> str:
        """
        Build a short, tenant-aware description of domains, intents, and entities
        to prepend to the classification prompt.

        This keeps the classifier configurable without breaking legacy behavior:
        if the config is empty, the original SYSTEM_MESSAGE still provides guidance.
        """
        if not tenant_cfg:
            return ""

        company = tenant_cfg.get("company_name", tenant_cfg.get("tenant_key", "this tenant"))
        domains = tenant_cfg.get("domains", [])
        intents = tenant_cfg.get("intents", [])
        entities = tenant_cfg.get("entities", {})

        lines = [f"You are classifying messages for tenant: {company}."]

        if domains:
            lines.append("Supported service domains:")
            for d in domains:
                name = d.get("name", "").upper()
                desc = d.get("description", "")
                lines.append(f"- {name}: {desc}")

        if intents:
            lines.append("Common intents:")
            for it in intents:
                name = it.get("name", "")
                desc = it.get("description", "")
                lines.append(f"- {name}: {desc}")

        if entities:
            lines.append("Important entity types to extract (when present):")
            for key, meta in entities.items():
                desc = meta.get("description", "")
                lines.append(f"- {key}: {desc}")

        return "\n".join(lines) + "\n"

    def _extract_and_parse_json(self, text: str) -> Dict[str, Any]:
        """
        Extract JSON from LLM response (handles markdown code blocks).

        Args:
            text: LLM response text

        Returns:
            Parsed JSON dictionary

        Raises:
            ValueError: If JSON cannot be extracted or parsed
        """
        # Try to find JSON in code blocks first
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            json_text = json_match.group(1)
        else:
            # Try to find raw JSON object
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                json_text = json_match.group(0)
            else:
                raise ValueError("No JSON object found in response")

        # Parse JSON
        try:
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")

    def _fallback_classify(
        self,
        message: str,
        context: Optional[ConversationContext]
    ) -> Dict[str, Any]:
        """
        Rule-based fallback classification when LLM fails.

        Args:
            message: Customer message
            context: Conversation context

        Returns:
            Dictionary with classification results
        """
        text_lower = message.lower()

        # Figure out tenant and config so fallback can be tenant-aware.
        tenant_id = None
        if context is not None:
            try:
                tenant_id = getattr(context, "tenant_id", None)
            except Exception:
                tenant_id = None
        tenant_cfg = TenantConfigStore.get_instance().get_config(tenant_id or "legacy-ng-telecom")

        # Domain detection (config-driven when patterns are available)
        patterns = tenant_cfg.get("fallback_patterns", {}).get("domains") or {}
        domain_scores: Dict[str, int]

        if patterns:
            domain_scores = {}
            for domain_name, keywords in patterns.items():
                score = 0
                for kw in keywords:
                    if kw and kw.lower() in text_lower:
                        score += 1
                domain_scores[domain_name] = score

            # Choose the best domain based on config-driven scores
            positive = {d: s for d, s in domain_scores.items() if s > 0}
            if not positive:
                # No strong signal → fall back to OTHER if present, else leave to legacy logic
                if "OTHER" in domain_scores:
                    max_domain = "OTHER"
                else:
                    # Fall back to legacy scoring as a safety net
                    domain_scores = {
                        "AIRTIME": self._score_airtime(text_lower),
                        "POWER": self._score_power(text_lower),
                        "DATA": self._score_data(text_lower)
                    }
                    max_domain = self._legacy_pick_domain(domain_scores)
            elif len(positive) > 1 and "MULTI" in domain_scores:
                max_domain = "MULTI"
            else:
                max_domain = max(positive, key=positive.get)
        else:
            # Legacy behavior for tenants without config patterns
            domain_scores = {
                "AIRTIME": self._score_airtime(text_lower),
                "POWER": self._score_power(text_lower),
                "DATA": self._score_data(text_lower)
            }
            max_domain = self._legacy_pick_domain(domain_scores)

        # Intent detection
        intent = self._detect_intent(text_lower)

        # Priority detection
        priority = self._detect_priority(text_lower)

        # Sentiment detection
        sentiment = self._detect_sentiment(text_lower)

        # Entity extraction
        entities = self._extract_entities(message)

        classification = ClassificationResult(
            service_domain=max_domain,
            intent=intent,
            priority=priority,
            sentiment=sentiment,
            entities=entities,
            confidence=0.6,
            reasoning="Fallback rule-based classification"
        )

        # Update context
        if context:
            context.service_domain = classification.service_domain
            context.intent = classification.intent
            context.priority = classification.priority
            context.sentiment = classification.sentiment

        return {
            "classification": classification.dict(),
            "raw_response": None,
            "method": "fallback",
            "fallback_used": True
        }

    def _legacy_pick_domain(self, domain_scores: Dict[str, int]) -> str:
        """Preserve original AIRTIME/POWER/DATA + MULTI/OTHER selection logic."""
        data_score = domain_scores.get("DATA", 0)
        power_score = domain_scores.get("POWER", 0)
        airtime_score = domain_scores.get("AIRTIME", 0)

        if data_score > 0 and power_score == 0:
            return "DATA"
        if power_score > 0 and data_score == 0:
            return "POWER"

        if domain_scores:
            max_domain = max(domain_scores, key=domain_scores.get)
            if domain_scores[max_domain] == 0:
                return "OTHER"
            if sum(1 for score in domain_scores.values() if score > 0) > 1:
                return "MULTI"
            return max_domain

        return "OTHER"

    # ========================================
    # Fallback Helper Methods
    # ========================================

    def _score_airtime(self, text: str) -> int:
        """Score text for airtime domain."""
        keywords = ["airtime", "recharge", "credit", "top up", "vend", "080", "081", "090", "091", "070",
                    "mtn", "airtel", "glo", "9mobile", "etisalat"]
        return sum(1 for kw in keywords if kw in text)

    def _score_power(self, text: str) -> int:
        """Score text for power domain."""
        keywords = ["electricity", "power", "light", "nepa", "phcn", "token", "meter", "bill", "units",
                    "kwh", "ekedc", "ikedc", "aedc", "phedc", "ibedc", "disco"]
        return sum(1 for kw in keywords if kw in text)

    def _score_data(self, text: str) -> int:
        """Score text for data domain."""
        keywords = ["data", " mb", " gb", "internet", "browsing", "bundle", "hotspot", "wifi"]
        return sum(1 for kw in keywords if kw in text)

    def _detect_intent(self, text: str) -> str:
        """Detect customer intent from text."""
        if any(word in text for word in ["buy", "purchase", "need", "want", "get me", "send"]):
            return "purchase"
        elif any(word in text for word in ["failed", "not working", "error", "problem", "issue"]):
            return "technical_issue"
        elif any(word in text for word in ["wrong", "refund", "overcharged", "dispute"]):
            return "billing_issue"
        elif any(word in text for word in ["?", "how", "what", "when", "where", "which", "tell me"]):
            return "inquiry"
        elif any(word in text for word in ["complain", "poor", "terrible", "bad", "disappointed"]):
            return "complaint"
        else:
            return "inquiry"

    def _detect_priority(self, text: str) -> str:
        """Detect priority level."""
        if any(word in text for word in ["urgent", "emergency", "critical", "lawyer", "police", "sue"]):
            return "CRITICAL"
        elif any(word in text for word in ["failed", "lost money", "deducted", "not received"]):
            return "HIGH"
        else:
            return "MEDIUM"

    def _detect_sentiment(self, text: str) -> str:
        """Detect sentiment."""
        if any(word in text for word in ["scam", "fraud", "terrible", "worst", "useless", "never again"]):
            return "VERY_NEGATIVE"
        elif any(word in text for word in ["disappointed", "frustrated", "poor", "bad", "not happy"]):
            return "NEGATIVE"
        elif any(word in text for word in ["thanks", "thank you", "great", "excellent", "appreciate"]):
            return "POSITIVE"
        else:
            return "NEUTRAL"

    def _extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract entities from text."""
        entities = {
            "phone_numbers": [],
            "meter_numbers": [],
            "amounts": [],
            "networks": [],
            "discos": []
        }

        # Phone numbers (Nigerian format)
        phone_pattern = r'(\+?234|0)[789]\d{9}'
        entities["phone_numbers"] = re.findall(phone_pattern, text.replace(" ", ""))

        # Amounts (naira)
        amount_pattern = r'₦?(\d{1,3}(?:,\d{3})*|\d+)(?:\s*(?:naira|NGN|₦))?'
        amounts = re.findall(amount_pattern, text)
        entities["amounts"] = [float(amt.replace(",", "")) for amt in amounts if amt]

        # Networks
        for network in ["MTN", "Airtel", "Glo", "9Mobile", "Etisalat"]:
            if network.lower() in text.lower():
                entities["networks"].append(network)

        # DISCOs
        discos = ["EKEDC", "IKEDC", "AEDC", "PHEDC", "IBEDC", "EEDC", "KEDCO", "BEDC", "JEDC", "KAEDCO"]
        for disco in discos:
            if disco.lower() in text.lower():
                entities["discos"].append(disco)

        return entities


# ============================================================
# TESTING
# ============================================================

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()

    llm_config = {
        "config_list": [{
            "model": "gpt-4o-mini",
            "api_key": os.getenv("OPENAI_API_KEY")
        }],
        "temperature": 0.1
    }

    classifier = ClassifierAgent(llm_config)

    # Test cases
    test_messages = [
        "I need 1000 naira MTN airtime for 08012345678",
        "Please buy me 5000 naira EKEDC token, meter number 12345678901",
        "Send me 2GB data on my Airtel line",
        "My transaction failed but money was deducted! This is a scam!",
        "How much is 10GB data bundle on MTN?",
    ]

    print("=" * 80)
    print("CLASSIFIER AGENT TESTING")
    print("=" * 80)

    for i, msg in enumerate(test_messages, 1):
        print(f"\n[Test {i}] Message: {msg}")
        print("-" * 80)

        response = classifier.process_message(msg)

        if response.success:
            classification = response.result["classification"]
            print(f"Domain: {classification['service_domain']}")
            print(f"Intent: {classification['intent']}")
            print(f"Priority: {classification['priority']}")
            print(f"Sentiment: {classification['sentiment']}")
            print(f"Confidence: {classification['confidence']}")
            print(f"Entities: {classification['entities']}")
            print(f"Method: {response.result['method']}")
        else:
            print(f"ERROR: {response.error}")

    print("\n" + "=" * 80)
    print("AGENT METRICS")
    print("=" * 80)
    print(classifier.get_metrics())
