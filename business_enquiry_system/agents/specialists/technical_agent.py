# agents/specialists/technical_agent.py
"""
Technical Support Agent Module
Handles technical issues, troubleshooting, and integration problems
"""

from typing import Dict, Any, List
import re
from datetime import datetime, timedelta
from agents.base_agent import BaseBusinessAgent


class TechnicalAgent(BaseBusinessAgent):
    SYSTEM_MESSAGE = """You are the Technical Support Agent for TechCorp Solutions.
    Troubleshoot issues, provide step-by-step solutions, escalate if critical.
    """

    def __init__(self, llm_config: Dict[str, Any]):
        super().__init__(
            name="technical_agent",
            system_message=self.SYSTEM_MESSAGE,
            llm_config=llm_config,
            description="Resolves technical issues, bugs, and integration problems"
        )
        self.known_issues = self._load_known_issues()
        self.system_status = self._check_system_status()
        self.resolution_history: List[Dict[str, Any]] = []

    def _load_known_issues(self) -> Dict[str, Any]:
        return {
            "LOGIN_FAILED": {
                "symptoms": ["cannot login", "authentication failed", "invalid credentials"],
                "solutions": ["Reset password via email link", "Clear browser cache and cookies", "Check if account is locked (3 failed attempts)", "Verify 2FA device is synced"],
                "workaround": "Use incognito/private browsing mode",
                "status": "resolved"
            },
            "API_RATE_LIMIT": {
                "symptoms": ["429 error", "too many requests", "rate limit exceeded"],
                "solutions": ["Implement exponential backoff", "Upgrade to higher tier for more API calls", "Optimize API usage with batch requests", "Implement caching"],
                "workaround": "Reduce request frequency temporarily",
                "status": "ongoing"
            }
        }

    def _check_system_status(self) -> Dict[str, Any]:
        return {
            "api": "operational",
            "web_app": "operational",
            "database": "operational",
            "cdn": "operational",
            "last_incident": {
                "date": (datetime.now() - timedelta(days=7)).isoformat(),
                "description": "Brief API outage",
                "duration": "15 minutes"
            }
        }

    def diagnose_issue(self, symptoms: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        info: Dict[str, Any] = {}

        # Extract HTTP status codes (e.g., 429)
        status_matches = re.findall(r'\b([1-5]\d{2})\b', symptoms)
        if status_matches:
            info["http_status"] = status_matches[0]

        # Initialize matched BEFORE any use
        matched = []
        # Keyword-based issue detection
        for issue_id, issue in self.known_issues.items():
            if any(s in symptoms.lower() for s in issue["symptoms"]):
                matched.append(issue_id)

        # Map known HTTP codes to issues (e.g., 429 => API_RATE_LIMIT)
        if info.get("http_status") == "429" and "API_RATE_LIMIT" not in matched:
            matched.append("API_RATE_LIMIT")

        # Severity heuristic
        sev_tokens_hi = ["down", "crashed", "data loss", "security breach", "cannot access", "urgent"]
        severity = "critical" if any(k in symptoms.lower() for k in sev_tokens_hi) \
                else "high" if "error" in symptoms.lower() else "medium"

        diagnosis = {
            "summary": f"Technical issue detected: {matched[0] if matched else 'Unknown'}",
            "severity": severity,
            "matched_issues": matched,
            "error_info": info,
            "system_status": self.system_status,
            "recommended_actions": []
        }

        if matched:
            issue = self.known_issues[matched[0]]
            diagnosis["recommended_actions"].extend(issue["solutions"])
            if issue.get("workaround"):
                diagnosis["workaround"] = issue["workaround"]
            if issue.get("status"):
                diagnosis["issue_status"] = issue["status"]
        else:
            diagnosis["recommended_actions"] = [
                "Gather more details (endpoint, request rate, timestamps)",
                "Check server/client logs",
                "Try basic troubleshooting (cache, auth, network)"
            ]

        if severity == "critical":
            diagnosis["escalation"] = True

        return diagnosis


    def provide_solution(self, issue_id: str, attempted_solutions: List[str] = None) -> Dict[str, Any]:
        if issue_id not in self.known_issues:
            return {"status": "unknown_issue", "message": "Issue not in database. Escalating.", "escalation": True}
        attempted = attempted_solutions or []
        remaining = [s for s in self.known_issues[issue_id]["solutions"] if s not in attempted]
        if not remaining:
            return {"status": "solutions_exhausted", "message": "All standard solutions attempted. Escalate.", "escalation": True}
        next_step = remaining[0]
        detailed = {
            "Reset password via email link": [
                "1. Go to https://techcorp.com/reset-password",
                "2. Enter your registered email address",
                "3. Click 'Send Reset Link'"
            ],
            "Implement exponential backoff": [
                "1. After 429, wait 1s and retry",
                "2. Double wait each time up to 60s",
                "3. Add jitter to avoid bursts"
            ]
        }.get(next_step, [next_step])
        return {"issue": issue_id, "next_step": next_step, "detailed_steps": detailed}

    def _process_specific(self, message: str, context: Dict[str, Any] = None) -> Any:
        diagnosis = self.diagnose_issue(message, context or {})
        if diagnosis.get("escalation"):
            return {"diagnosis": diagnosis, "status": "ESCALATION_REQUIRED"}
        if diagnosis["matched_issues"]:
            solution = self.provide_solution(diagnosis["matched_issues"][0], (context or {}).get("attempted_solutions"))
            return {"diagnosis": diagnosis, "solution": solution}
        return {"diagnosis": diagnosis, "next_steps": ["Please provide error details and steps to reproduce."]}
