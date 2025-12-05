"""
Context engine and case state implementation.

Implements Phase 3: persistent CaseState and ContextPackBuilder.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents.base_agent_v2 import ConversationContext


@dataclass
class CaseState:
    tenant_id: str
    conversation_id: str
    enquiry_id: str
    user_goal: Optional[str] = None
    workflow_step: Optional[str] = None
    slots: Dict[str, Any] = field(default_factory=dict)
    last_tool_summaries: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class CaseStateStore:
    def __init__(self, base_dir: Optional[str] = None) -> None:
        root = os.path.dirname(__file__)
        self.base_dir = base_dir or os.path.join(root, "logs", "case_state")
        os.makedirs(self.base_dir, exist_ok=True)

    def _path_for(self, tenant_id: str, conversation_id: str) -> str:
        safe_tenant = tenant_id.replace("/", "_")
        safe_conv = conversation_id.replace("/", "_")
        tenant_dir = os.path.join(self.base_dir, safe_tenant)
        os.makedirs(tenant_dir, exist_ok=True)
        return os.path.join(tenant_dir, f"{safe_conv}.json")

    def load(self, tenant_id: str, conversation_id: str) -> Optional[CaseState]:
        path = self._path_for(tenant_id, conversation_id)
        if not os.path.isfile(path):
            return None
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return CaseState(**payload)

    def save(self, state: CaseState) -> None:
        state.updated_at = datetime.utcnow().isoformat() + "Z"
        path = self._path_for(state.tenant_id, state.conversation_id)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(asdict(state), handle, ensure_ascii=False, indent=2)


class ContextPackBuilder:
    def __init__(self, max_tokens_per_section: int = 1024) -> None:
        self.max_tokens_per_section = max_tokens_per_section

    def build(
        self,
        tenant_rules: Dict[str, Any],
        conversation: ConversationContext,
        case_state: Optional[CaseState],
        kb_summaries: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        rules_section = tenant_rules.get("operating_rules", "")
        history_summary = self._build_history_summary(conversation, case_state)
        kb_section = "\n".join(kb_summaries or [])[: self.max_tokens_per_section]

        return {
            "tenant_rules": rules_section[: self.max_tokens_per_section],
            "history_summary": history_summary[: self.max_tokens_per_section],
            "kb_context": kb_section,
        }

    def _build_history_summary(
        self,
        conversation: ConversationContext,
        case_state: Optional[CaseState],
    ) -> str:
        lines: List[str] = []
        lines.append(f"Enquiry ID: {conversation.enquiry_id}")
        lines.append(f"Domain: {conversation.service_domain or '-'}")
        lines.append(f"Intent: {conversation.intent or '-'}")
        lines.append(f"Resolution status: {conversation.resolution_status}")
        if case_state:
            lines.append(f"Workflow step: {case_state.workflow_step or '-'}")
            if case_state.user_goal:
                lines.append(f"User goal: {case_state.user_goal}")
            if case_state.slots:
                lines.append(f"Known slots: {list(case_state.slots.keys())}")
        return "\n".join(lines)

    def compact_tool_results(self, tool_outputs: List[Dict[str, Any]], max_chars: int = 500) -> List[str]:
        """Compact tool outputs to short summaries for context window."""
        summaries = []
        for output in tool_outputs:
            tool_name = output.get("tool", "unknown")
            status = output.get("status", "ok")
            result = output.get("output", {})
            
            if status == "ok":
                # Create a brief summary
                summary = f"[{tool_name}] Success"
                if isinstance(result, dict):
                    keys = list(result.keys())[:3]
                    summary += f": {', '.join(keys)}"
            else:
                summary = f"[{tool_name}] Failed: {output.get('error', 'unknown error')[:100]}"
            
            summaries.append(summary[:max_chars])
        return summaries


class ConversationCompactor:
    """Compacts older conversation turns into a rolling summary."""
    
    def __init__(self, max_recent_turns: int = 5, max_summary_chars: int = 1000):
        self.max_recent_turns = max_recent_turns
        self.max_summary_chars = max_summary_chars
    
    def compact(self, messages: List[Dict[str, str]], existing_summary: str = "") -> Dict[str, Any]:
        """
        Compact messages into a summary + recent messages.
        
        Returns:
            {
                "summary": str,  # Summary of older messages
                "recent_messages": List[Dict],  # Recent messages to keep in full
            }
        """
        if len(messages) <= self.max_recent_turns:
            return {
                "summary": existing_summary,
                "recent_messages": messages,
            }
        
        # Keep recent messages
        recent = messages[-self.max_recent_turns:]
        older = messages[:-self.max_recent_turns]
        
        # Build summary of older messages
        summary_parts = [existing_summary] if existing_summary else []
        for msg in older:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:200]
            summary_parts.append(f"[{role}]: {content}...")
        
        combined_summary = "\n".join(summary_parts)
        if len(combined_summary) > self.max_summary_chars:
            combined_summary = combined_summary[:self.max_summary_chars] + "..."
        
        return {
            "summary": combined_summary,
            "recent_messages": recent,
        }


class ReflectStep:
    """
    Post-tool reflection step (Phase 3.4).
    
    After retrieval/tool calls, check:
    - Do we have enough info to answer?
    - What is the best next action?
    - Any policy/escalation triggers?
    """
    
    POLICY_TRIGGERS = [
        ("legal", ["lawyer", "sue", "lawsuit", "court", "police"]),
        ("safety", ["emergency", "danger", "urgent medical"]),
        ("fraud", ["scam", "fraud", "stolen", "hacked"]),
        ("escalation_request", ["speak to human", "talk to manager", "supervisor"]),
    ]
    
    def __init__(self, llm_config: Optional[Dict[str, Any]] = None):
        self.llm_config = llm_config
    
    def reflect(
        self,
        user_message: str,
        classification: Dict[str, Any],
        retrieval_results: List[Dict[str, Any]],
        tool_results: List[Dict[str, Any]],
        case_state: Optional[CaseState] = None,
    ) -> Dict[str, Any]:
        """
        Perform reflection after gathering information.
        
        Returns:
            {
                "has_sufficient_info": bool,
                "missing_info": List[str],
                "suggested_next_action": str,
                "policy_triggers": List[str],
                "should_escalate": bool,
                "reasoning": str,
            }
        """
        result = {
            "has_sufficient_info": False,
            "missing_info": [],
            "suggested_next_action": "generate_response",
            "policy_triggers": [],
            "should_escalate": False,
            "reasoning": "",
        }
        
        # Check for policy triggers in user message
        message_lower = user_message.lower()
        for trigger_name, keywords in self.POLICY_TRIGGERS:
            if any(kw in message_lower for kw in keywords):
                result["policy_triggers"].append(trigger_name)
                if trigger_name in ["legal", "safety", "escalation_request"]:
                    result["should_escalate"] = True
        
        # Check if we have retrieval results
        has_retrieval = len(retrieval_results) > 0
        has_tool_results = len(tool_results) > 0
        
        # Check for required entities based on intent
        intent = classification.get("intent", "")
        entities = classification.get("entities", {})
        
        if "purchase" in intent:
            # For purchase intents, we need amount and recipient info
            if not entities.get("amounts") and not entities.get("phone_numbers"):
                result["missing_info"].append("amount or recipient details")
            else:
                result["has_sufficient_info"] = True
        elif "inquiry" in intent or "question" in intent.lower():
            # For inquiries, retrieval results are helpful
            result["has_sufficient_info"] = has_retrieval
            if not has_retrieval:
                result["missing_info"].append("relevant knowledge base information")
        else:
            # Default: assume we have enough if we have any results
            result["has_sufficient_info"] = has_retrieval or has_tool_results
        
        # Determine next action
        if result["should_escalate"]:
            result["suggested_next_action"] = "escalate"
        elif not result["has_sufficient_info"] and result["missing_info"]:
            result["suggested_next_action"] = "ask_user"
        else:
            result["suggested_next_action"] = "generate_response"
        
        # Build reasoning
        reasons = []
        if result["has_sufficient_info"]:
            reasons.append("Have sufficient information to respond")
        if result["missing_info"]:
            reasons.append(f"Missing: {', '.join(result['missing_info'])}")
        if result["policy_triggers"]:
            reasons.append(f"Policy triggers: {', '.join(result['policy_triggers'])}")
        result["reasoning"] = "; ".join(reasons)
        
        return result


def build_tenant_rules_text(tenant_cfg: Dict[str, Any]) -> str:
    """
    Build a compact textual description of tenant operating rules
    (tone, greetings, escalation hints) from config.
    """
    if not tenant_cfg:
        return ""

    branding = tenant_cfg.get("branding", {})
    lines: List[str] = []

    tone = branding.get("tone")
    if tone:
        lines.append(f"Tone: {tone}")

    greeting = branding.get("greeting")
    if greeting:
        lines.append(f"Greeting pattern: {greeting}")

    closing = branding.get("closing")
    if closing:
        lines.append(f"Closing pattern: {closing}")
    
    # Add escalation rules if present
    escalation = tenant_cfg.get("escalation", {})
    if escalation:
        triggers = escalation.get("triggers", [])
        if triggers:
            lines.append(f"Escalation triggers: {', '.join(triggers)}")

    return "\n".join(lines)
