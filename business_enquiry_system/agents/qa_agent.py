# agents/qa_agent.py
"""
Quality Assurance Agent Module
Reviews responses for accuracy, completeness, and professionalism
"""

from typing import Dict, Any, List
import re
from datetime import datetime
from agents.base_agent import BaseBusinessAgent


class QAAgent(BaseBusinessAgent):
    SYSTEM_MESSAGE = """You are the Quality Assurance Agent for TechCorp Solutions.
    Review responses for accuracy, completeness, tone, compliance, and helpfulness.
    """

    def __init__(self, llm_config: Dict[str, Any]):
        super().__init__(
            name="qa_agent",
            system_message=self.SYSTEM_MESSAGE,
            llm_config=llm_config,
            description="Reviews responses for accuracy, completeness, and professionalism"
        )
        self.review_history: List[Dict[str, Any]] = []

    def review_response(self, response: str, original_enquiry: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        self.logger.info("Reviewing response quality")
        # Simplified rubric (same spirit as your file)
        def score_bool(ok: bool, w: float) -> float: return 100.0 * w if ok else 60.0 * w

        issues: List[str] = []
        suggestions: List[str] = []

        # Accuracy / facts (heuristic)
        inaccurate_patterns = [r"24/7.*support.*basic", r"unlimited.*basic", r"free.*enterprise"]
        inaccurate = any(re.search(p, response.lower()) for p in inaccurate_patterns)
        if inaccurate:
            issues.append("Potential factual inconsistency detected")
            suggestions.append("Verify facts against the knowledge base")

        # Completeness (does it reference the enquiry)
        covers_enquiry = len(set(original_enquiry.lower().split()) & set(response.lower().split())) / max(1, len(original_enquiry.split())) > 0.3

        # Professional tone (simple)
        unprofessional = any(w in response.lower().split() for w in ["hey", "yo", "dude", "lol", "wtf"])
        if unprofessional:
            issues.append("Tone not fully professional")
            suggestions.append("Adjust tone to be more professional")

        # Next steps present?
        has_next_steps = any(s in response.lower() for s in ["next step", "please", "you can", "contact", "follow"])

        overall = (
            score_bool(not inaccurate, 0.25) +
            score_bool(covers_enquiry, 0.20) +
            score_bool(not unprofessional, 0.15) +
            score_bool(True, 0.15) +                  # compliance placeholder
            score_bool(True, 0.10) +                  # helpfulness placeholder
            (100.0 * 0.15 if has_next_steps else 80.0 * 0.15)  # clarity/structure proxy
        )

        status = (
            "approved" if overall >= 85 else
            "approved_with_suggestions" if overall >= 70 else
            "revision_required" if overall >= 50 else
            "rejected"
        )

        result = {
            "timestamp": datetime.now().isoformat(),
            "overall_score": overall,
            "status": status,
            "criteria_scores": {},
            "issues_found": issues,
            "suggestions": suggestions,
            "revised_response": None
        }
        self.review_history.append({
            "enquiry": original_enquiry[:100],
            "score": overall,
            "status": status,
            "timestamp": result["timestamp"]
        })
        self.logger.info(f"Review complete. Score: {overall:.1f}, Status: {status}")
        return result

    def _process_specific(self, message: str, context: Dict[str, Any] = None) -> Any:
        if context and "response" in context:
            return self.review_response(context["response"], context.get("enquiry", ""), context)
        return {"error": "No response provided to review", "instruction": "Provide response and original enquiry for QA review"}
