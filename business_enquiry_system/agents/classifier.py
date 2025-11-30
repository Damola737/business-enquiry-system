# agents/classifier.py
"""
Classifier Agent Module
Analyzes and categorizes incoming business enquiries
"""

from typing import Dict, Any, List, Optional, Tuple
import re
from datetime import datetime
from agents.base_agent import BaseBusinessAgent


class ClassifierAgent(BaseBusinessAgent):
    """
    Classifier agent that analyzes and categorizes business enquiries
    Determines type, urgency, and extracts key information
    """

    SYSTEM_MESSAGE = """You are the Classifier Agent for a business enquiry system.
    (Responsibilities: categorize, prioritize, extract entities & intent, detect multi-topic.)
    """

    def __init__(self, llm_config: Dict[str, Any]):
        super().__init__(
            name="classifier",
            system_message=self.SYSTEM_MESSAGE,
            llm_config=llm_config,
            description="Analyzes and categorizes incoming business enquiries"
        )
        self.category_patterns = self._initialize_category_patterns()
        self.priority_triggers = self._initialize_priority_triggers()
        self.classification_history: List[Dict[str, Any]] = []

    def _initialize_category_patterns(self) -> Dict[str, List[str]]:
        return {
            "SALES": ["price", "pricing", "cost", "buy", "purchase", "demo", "trial", "discount", "quote", "proposal", "sales"],
            "TECHNICAL": ["error", "bug", "issue", "problem", "not working", "crash", "integration", "api", "technical", "debug", "fix"],
            "BILLING": ["invoice", "payment", "charge", "billing", "subscription", "refund", "credit card", "transaction", "receipt"],
            "PRODUCT": ["feature", "functionality", "how to", "documentation", "guide", "tutorial", "capability", "roadmap"],
            "SUPPORT": ["help", "assist", "support", "account", "password", "login", "access", "settings", "profile"],
            "COMPLAINT": ["complaint", "unhappy", "disappointed", "frustrated", "angry", "terrible", "worst", "unacceptable"]
        }

    def _initialize_priority_triggers(self) -> Dict[str, List[str]]:
        return {
            "HIGH": ["urgent", "emergency", "critical", "asap", "immediately", "down", "not working at all", "security", "breach", "hack", "legal", "lawsuit", "very angry", "cancel everything"],
            "MEDIUM": ["soon", "important", "need help", "problem", "issue", "question", "concern", "waiting"],
            "LOW": ["when you can", "no rush", "just wondering", "curious", "information", "general question", "future"]
        }

    def classify_enquiry(self, enquiry: str) -> Dict[str, Any]:
        self.logger.info(f"Classifying enquiry: {enquiry[:100]}...")

        category_scores = self._score_categories(enquiry)
        priority = self._determine_priority(enquiry)
        sentiment = self._analyze_sentiment(enquiry)
        complexity = self._assess_complexity(enquiry)
        entities = self._extract_entities(enquiry)
        intent = self._extract_intent(enquiry)

        primary_category = max(category_scores, key=category_scores.get)
        secondary_categories = [c for c, s in category_scores.items() if s > 0.3 and c != primary_category]

        if len(secondary_categories) >= 2 or complexity == "complex":
            primary_category = "COMPLEX"

        classification = {
            "category": primary_category,
            "secondary_categories": secondary_categories,
            "priority": priority,
            "intent": intent,
            "entities": entities,
            "sentiment": sentiment,
            "requires_research": self._requires_research(enquiry),
            "complexity": complexity,
            "confidence_scores": category_scores,
            "timestamp": datetime.now().isoformat()
        }

        self.classification_history.append({"enquiry": enquiry, "classification": classification})
        self.logger.info(f"Classification complete: {primary_category} ({priority})")
        return classification

    # --- helpers (unchanged from your working version) ---
    def _score_categories(self, text: str) -> Dict[str, float]:
        text_lower = text.lower()
        scores = {}
        for category, keywords in self.category_patterns.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            scores[category] = min(score / len(keywords), 1.0) if keywords else 0
        if all(s == 0 for s in scores.values()):
            scores["SUPPORT"] = 0.5
        return scores

    def _determine_priority(self, text: str) -> str:
        text_lower = text.lower()
        for priority, triggers in self.priority_triggers.items():
            if any(t in text_lower for t in triggers):
                return priority
        if self._analyze_sentiment(text) == "very negative":
            return "HIGH"
        elif self._analyze_sentiment(text) == "negative":
            return "MEDIUM"
        return "MEDIUM"

    def _analyze_sentiment(self, text: str) -> str:
        t = text.lower()
        very_negative = ["hate", "terrible", "awful", "worst", "disgusting"]
        negative = ["bad", "poor", "unhappy", "disappointed", "frustrated"]
        positive = ["good", "great", "excellent", "happy", "satisfied", "love"]
        if any(w in t for w in very_negative): return "very negative"
        if sum(w in t for w in negative) > sum(w in t for w in positive): return "negative"
        if sum(w in t for w in positive) > sum(w in t for w in negative): return "positive"
        return "neutral"

    def _assess_complexity(self, text: str) -> str:
        wc, qc = len(text.split()), text.count("?")
        multi = sum(1 for w in ["also", "additionally", "furthermore", "and", "plus"] if w in text.lower())
        if wc > 150 or qc > 3 or multi > 2: return "complex"
        if wc > 50 or qc > 1 or multi > 0: return "moderate"
        return "simple"

    def _extract_entities(self, text: str) -> Dict[str, Any]:
        entities: Dict[str, Any] = {}
        import re
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
        phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
        order_pattern = r'\b(?:order|ticket|case|ref)[#:\s]*([A-Z0-9]{6,})\b'
        money_pattern = r'\$?(\d+(?:,\d{3})*(?:\.\d{2})?)'
        date_pattern = r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'
        m = re.findall(email_pattern, text);     entities["email"] = m[0] if m else None
        m = re.findall(phone_pattern, text);     entities["phone"] = m[0] if m else None
        m = re.findall(order_pattern, text, re.IGNORECASE); entities["reference_number"] = m[0] if m else None
        m = re.search(money_pattern, text);      entities["amount"] = float(m.group(1).replace(",", "")) if m else None
        m = re.findall(date_pattern, text);      entities["date"] = m[0] if m else None
        for k in ["premium", "basic", "pro", "enterprise", "standard"]:
            if k in text.lower(): entities["product_tier"] = k; break
        return {k: v for k, v in entities.items() if v is not None}

    def _extract_intent(self, text: str) -> str:
        t = text.lower()
        patterns = {
            "purchase": ["want to buy", "interested in purchasing", "how much for"],
            "cancel": ["want to cancel", "cancel my", "stop my subscription"],
            "refund": ["want a refund", "money back", "refund my"],
            "information": ["how do", "what is", "can you explain"],
            "complaint": ["complain", "not happy", "disappointed with"],
            "technical_help": ["not working", "error", "can't access"],
            "upgrade": ["upgrade", "better plan", "more features"],
            "downgrade": ["downgrade", "cheaper plan", "reduce cost"]
        }
        for intent, pats in patterns.items():
            if any(p in t for p in pats): return intent
        if "?" in text:
            q = text.split("?")[0].lower()
            if "how" in q: return "how_to"
            if "what" in q: return "information"
            if "why" in q: return "explanation"
            if "when" in q: return "timing"
            if "can" in q or "could" in q: return "possibility_check"
        return "general_inquiry"

    def _requires_research(self, text: str) -> bool:
        return any(k in text.lower() for k in [
            "documentation", "guide", "how to", "tutorial",
            "technical details", "specifications", "compatibility",
            "integration", "api", "compare", "difference between"
        ])

    # (validate/get stats remain same as your current version)
