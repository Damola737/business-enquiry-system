# agents/orchestrator.py
"""
Orchestrator Agent Module
Manages the group chat workflow and routes enquiries to appropriate specialists
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from agents.base_agent import BaseBusinessAgent
from autogen import GroupChat, GroupChatManager


class OrchestratorAgent(BaseBusinessAgent):
    """
    Orchestrator agent that manages the multi-agent workflow
    Routes enquiries, manages state, and ensures completion
    """

    SYSTEM_MESSAGE = """You are the Orchestrator Agent for a business enquiry system.

    Your responsibilities:
    1. Analyze incoming business enquiries and determine the appropriate specialist agents
    2. Coordinate multi-agent collaboration for complex queries
    3. Ensure all enquiries receive timely and complete responses
    4. Monitor conversation flow and intervene when necessary
    5. Escalate issues that cannot be resolved by the specialist agents

    Speaking Order Guidelines (conceptual):
    1. Classifier → 2. Research → 3. Specialist(s) → 4. QA → 5. Response Generator

    Terminate conversation when:
    - Response has been generated and approved
    - Issue has been escalated
    - Maximum rounds reached without resolution
    """

    def __init__(self, llm_config: Dict[str, Any]):
        super().__init__(
            name="orchestrator",
            system_message=self.SYSTEM_MESSAGE,
            llm_config=llm_config,
            description="Orchestrates the multi-agent workflow and routes enquiries"
        )
        self.active_enquiries: Dict[str, Any] = {}
        self.escalation_queue: List[Dict[str, Any]] = []
        self.routing_patterns = self._initialize_routing_patterns()

    def _initialize_routing_patterns(self) -> Dict[str, List[str]]:
        """Initialize routing patterns for different enquiry types"""
        return {
            "sales": ["sales_agent"],
            "technical": ["technical_agent", "research_agent"],
            "billing": ["billing_agent"],
            "product": ["sales_agent"],
            "support": ["technical_agent"],
            "complex": ["classifier", "research_agent"]  # then multiple specialists as needed
        }

    def create_group_chat(
        self,
        agents: List[Any],
        max_round: int = 20,
        speaker_selection_method: str = "auto"
    ) -> tuple:
        """
        Create and configure the group chat with all agents.

        NOTE: We do NOT pass allowed_speaker_transitions_dict here to avoid
        pyautogen version mismatches like:
        "allowed_speaker_transitions_dict has values that are not lists of Agents."
        """
        self.logger.info(f"Creating group chat with {len(agents)} agents")

        group_chat = GroupChat(
            agents=agents,
            messages=[],
            max_round=max_round,
            speaker_selection_method=speaker_selection_method,
            allow_repeat_speaker=False,
            admin_name=self.name
        )

        manager = GroupChatManager(
            groupchat=group_chat,
            llm_config=self.llm_config,
            system_message="Manage the group discussion efficiently."
        )

        self.logger.info("Group chat created successfully")
        return group_chat, manager

    def route_enquiry(
        self,
        enquiry_id: str,
        category: str,
        priority: str,
        content: str
    ) -> List[str]:
        """
        Determine which agents should handle the enquiry.
        """
        self.logger.info(f"Routing enquiry {enquiry_id} - Category: {category}, Priority: {priority}")

        self.active_enquiries[enquiry_id] = {
            "id": enquiry_id,
            "category": category,
            "priority": priority,
            "content": content,
            "status": "routing",
            "assigned_agents": [],
            "timestamp": datetime.now().isoformat()
        }

        # Determine agents by category (fallback to support)
        agents = self.routing_patterns.get(category.lower(), self.routing_patterns["support"]).copy()

        # High/Critical: ensure research joins early
        if str(priority).lower() in {"high", "critical"} and "research_agent" not in agents:
            agents.insert(0, "research_agent")

        # Do NOT append QA or Response here; the main pipeline calls them once, centrally.

        self.active_enquiries[enquiry_id]["assigned_agents"] = agents
        self.active_enquiries[enquiry_id]["status"] = "processing"

        self.logger.info(f"Enquiry {enquiry_id} routed to agents: {agents}")
        return agents

    # (monitoring, escalation, etc. left as in your current version)
