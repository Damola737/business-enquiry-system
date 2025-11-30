# main.py
"""
Main Business Enquiry System
Orchestrates multi-agent collaboration for handling business enquiries
"""

import json
import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

from autogen import GroupChat, GroupChatManager  # noqa: F401  (used indirectly)
from agents.orchestrator import OrchestratorAgent
from agents.classifier import ClassifierAgent
from agents.research_agent import ResearchAgent
from agents.qa_agent import QAAgent
from agents.response_generator import ResponseGeneratorAgent
from agents.specialists.sales_agent import SalesAgent
from agents.specialists.technical_agent import TechnicalAgent
from agents.specialists.billing_agent import BillingAgent


# Root logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('business_enquiry_system.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


class BusinessEnquirySystem:
    """
    Main system for handling business enquiries using multi-agent collaboration
    """

    def __init__(self, config_path: str = "config/llm_config.json"):
        self.config = self._load_config(config_path)
        self.llm_config = self.config["llm_config"]
        self.agents: Dict[str, Any] = {}
        self.group_chat = None
        self.group_chat_manager = None
        self.enquiry_history: List[Dict[str, Any]] = []

        self._initialize_agents()
        self._setup_group_chat()
        logger.info("Business Enquiry System initialized successfully")

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        with open(config_path, 'r') as f:
            config = json.load(f)
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            for llm in config["llm_config"]["config_list"]:
                llm["api_key"] = api_key
        return config

    def _initialize_agents(self):
        logger.info("Initializing agents...")
        self.agents["orchestrator"] = OrchestratorAgent(self.llm_config)
        self.agents["classifier"] = ClassifierAgent(self.llm_config)
        self.agents["research_agent"] = ResearchAgent(self.llm_config, knowledge_base_path="./knowledge_base")
        self.agents["qa_agent"] = QAAgent(self.llm_config)
        self.agents["response_generator"] = ResponseGeneratorAgent(self.llm_config)
        self.agents["sales_agent"] = SalesAgent(self.llm_config)
        self.agents["technical_agent"] = TechnicalAgent(self.llm_config)
        self.agents["billing_agent"] = BillingAgent(self.llm_config)
        logger.info(f"Initialized {len(self.agents)} agents")

    def _setup_group_chat(self):
        # We do not need GroupChat for our Python-orchestrated pipeline.
        # Skip it to avoid pyautogen graph validation differences across 0.2.x.
        self.group_chat = None
        self.group_chat_manager = None
        logger.info("Group chat skipped (direct agent orchestration is enabled).")


    def process_enquiry(self, enquiry_text: str, customer_info: Dict[str, Any] = None, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        enquiry_id = f"ENQ-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        logger.info(f"Processing enquiry {enquiry_id}: {enquiry_text[:100]}...")

        result: Dict[str, Any] = {
            "enquiry_id": enquiry_id,
            "enquiry_text": enquiry_text,
            "customer_info": customer_info,
            "metadata": metadata,
            "timestamp": datetime.now().isoformat(),
            "agents_involved": [],
            "processing_steps": [],
            "final_response": None,
            "status": "processing"
        }

        try:
            classification = self._classify_enquiry(enquiry_text, enquiry_id, result)
            routing = self._route_enquiry(enquiry_id, classification, result)
            agent_responses = self._process_with_specialists(enquiry_text, classification, routing, result)
            qa_result = self._quality_review(agent_responses, enquiry_text, result)
            final_response = self._generate_final_response(enquiry_text, classification, agent_responses, qa_result, customer_info, result)

            result["final_response"] = final_response
            result["status"] = "completed"
            self.enquiry_history.append(result)
            logger.info(f"Enquiry {enquiry_id} processed successfully")

        except Exception as e:
            logger.error(f"Error processing enquiry {enquiry_id}: {e}")
            result["status"] = "error"
            result["error"] = str(e)
            result["final_response"] = self._generate_fallback_response(enquiry_text, str(e))

        return result

    # --- pipeline steps ---
    def _classify_enquiry(self, enquiry_text: str, enquiry_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
        classification = self.agents["classifier"].classify_enquiry(enquiry_text)
        result["agents_involved"].append("classifier")
        result["processing_steps"].append({"step": "classification", "agent": "classifier", "result": classification, "timestamp": datetime.now().isoformat()})
        return classification

    def _route_enquiry(self, enquiry_id: str, classification: Dict[str, Any], result: Dict[str, Any]) -> List[str]:
        routing = self.agents["orchestrator"].route_enquiry(
            enquiry_id,
            classification["category"],
            classification["priority"],
            classification.get("intent", "")
        )
        result["agents_involved"].append("orchestrator")
        result["processing_steps"].append({"step": "routing", "agent": "orchestrator", "result": routing, "timestamp": datetime.now().isoformat()})
        return routing

    def _process_with_specialists(self, enquiry_text: str, classification: Dict[str, Any], routing: List[str], result: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"Processing with specialists: {routing}")
        agent_responses: Dict[str, Any] = {}
        context = {"classification": classification, "enquiry_text": enquiry_text}

        for agent_name in routing:
            if agent_name in self.agents:
                logger.info(f"Processing with {agent_name}")
                try:
                    resp = self.agents[agent_name].process_message(enquiry_text, context)
                    agent_responses[agent_name] = resp
                    result["agents_involved"].append(agent_name)
                    result["processing_steps"].append({"step": f"process_{agent_name}", "agent": agent_name, "result": resp, "timestamp": datetime.now().isoformat()})
                    context[agent_name] = resp
                except Exception as e:
                    logger.error(f"Error processing with {agent_name}: {e}")
                    agent_responses[agent_name] = {"success": False, "error": str(e)}
        return agent_responses

    def _quality_review(self, agent_responses: Dict[str, Any], enquiry_text: str, result: Dict[str, Any]) -> Dict[str, Any]:
        prelim = self._compile_preliminary_response(agent_responses)
        qa_result = self.agents["qa_agent"].review_response(prelim, enquiry_text, {"agent_responses": agent_responses})
        result["agents_involved"].append("qa_agent")
        result["processing_steps"].append({"step": "quality_review", "agent": "qa_agent", "result": qa_result, "timestamp": datetime.now().isoformat()})
        return qa_result

    def _generate_final_response(
        self,
        enquiry_text: str,
        classification: Dict[str, Any],
        agent_responses: Dict[str, Any],
        qa_result: Dict[str, Any],
        customer_info: Optional[Dict[str, Any]],
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate the final customer response (FLATTEN specialist outputs)."""
        logger.info("Generating final response")

        # --- Flatten wrappers {"success":..., "result": {...}} ---
        flat_inputs: Dict[str, Any] = {}
        for name, payload in (agent_responses or {}).items():
            if name in ("qa_agent", "response_generator"):
                continue
            data = None
            if isinstance(payload, dict):
                if payload.get("success") and "result" in payload:
                    data = payload["result"]
                elif "result" in payload:
                    data = payload["result"]
                else:
                    data = payload
            else:
                data = payload

            # Normalize SalesAgent → expose as pricing.recommendations
            if name == "sales_agent" and isinstance(data, dict):
                if "pricing" not in data and "recommendations" in data:
                    data = {**data, "pricing": {"recommendations": data["recommendations"]}}

            if data is not None:
                flat_inputs[name] = data

        flat_inputs["classifier"] = classification
        flat_inputs["qa_agent"] = qa_result

        context = {
            "enquiry": {
                "text": enquiry_text,
                "id": result["enquiry_id"],
                **classification
            },
            "agent_inputs": flat_inputs,
            "customer_info": customer_info or {},
            "qa_feedback": qa_result
        }

        final_response = self.agents["response_generator"].process_message("Generate final response", context)

        result["agents_involved"].append("response_generator")
        result["processing_steps"].append({
            "step": "generate_response",
            "agent": "response_generator",
            "result": final_response,
            "timestamp": datetime.now().isoformat()
        })
        return final_response

    def _compile_preliminary_response(self, agent_responses: Dict[str, Any]) -> str:
        parts: List[str] = []
        for agent_name, response_data in agent_responses.items():
            if isinstance(response_data, dict) and response_data.get("success") and "result" in response_data:
                r = response_data["result"]
                if agent_name == "sales_agent" and "recommendations" in r:
                    parts.append(str(r["recommendations"]))
                elif agent_name == "technical_agent" and "solution" in r:
                    parts.append(str(r["solution"]))
                elif agent_name == "research_agent" and "findings" in r:
                    parts.append(str(r["findings"].get("summary", "")))
        return "\n\n".join(parts) if parts else "Processing your enquiry..."

    def _generate_fallback_response(self, enquiry_text: str, error: str) -> Dict[str, Any]:
        return {
            "response": f"""
We apologize, but we encountered an issue processing your enquiry.

Your enquiry: {enquiry_text[:200]}...

We've logged this issue and our team will investigate immediately. 
Please contact us directly at support@techcorp.com or call 1-800-TECH-HELP for immediate assistance.

Reference: {datetime.now().strftime('%Y%m%d%H%M%S')}

Thank you for your patience and understanding.
            """.strip(),
            "type": "error_fallback",
            "error": error,
            "timestamp": datetime.now().isoformat()
        }


def main():
    system = BusinessEnquirySystem()
    tests = [
        {"text": "I'm interested in your Enterprise plan. Can you tell me about the pricing and features?", "customer_info": {"name": "John Doe", "email": "john@example.com"}},
        {"text": "I'm getting an API rate limit error (429) when trying to access the analytics endpoint. How can I fix this?", "customer_info": {"name": "Jane Smith", "tier": "professional"}},
        {"text": "I want to upgrade to Enterprise but I can't login and I need the last invoice too.", "customer_info": {"name": "Bob Wilson", "account_type": "basic"}}
    ]
    for t in tests:
        print(f"\n{'='*60}\nProcessing: {t['text'][:80]}...\n{'='*60}")
        result = system.process_enquiry(t["text"], t.get("customer_info"))
        fr = result.get("final_response")
        if isinstance(fr, dict) and "result" in fr:
            print(fr["result"].get("response", "No response generated"))
        elif isinstance(fr, dict):
            print(json.dumps(fr, indent=2))
        else:
            print(fr)
        print("\nAgents involved:", ", ".join(result["agents_involved"]))
        print("Status:", result["status"])

if __name__ == "__main__":
    main()
