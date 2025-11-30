# agents/base_agent.py
"""
Base Business Agent
Provides common wrapper, logging, and metrics for all agents.
"""

from typing import Any, Dict, Optional
import logging
from datetime import datetime
try:
    from autogen import ConversableAgent
except Exception:  # Allow environments without autogen at creation time
    ConversableAgent = object  # type: ignore


class BaseBusinessAgent:
    """
    Base class that wraps an AutoGen ConversableAgent for consistency,
    but exposes a simple .process_message(message, context) API and metrics.
    """

    def __init__(self, name: str, system_message: str, llm_config: Dict[str, Any], description: str = ""):
        self.name = name
        self.description = description or name
        self.system_message = system_message
        self.llm_config = llm_config

        # Logger
        self.logger = logging.getLogger(f"agent.{self.name}")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(fmt)
            self.logger.addHandler(handler)
        # Avoid double-print via root logger
        self.logger.propagate = False
        self.logger.setLevel(logging.INFO)

        # Conversable agent instance (used for group chat / future LLM replies)
        try:
            self.agent = ConversableAgent(
                name=self.name,
                system_message=self.system_message,
                llm_config=self.llm_config,
                human_input_mode="NEVER"
            )
        except Exception:
            # Fallback placeholder if autogen isn't available yet
            class _DummyAgent:
                def __init__(self, name): self.name = name
            self.agent = _DummyAgent(self.name)

        # Metrics
        self._metrics = {
            "total_messages": 0,
            "successes": 0,
            "failures": 0,
            "last_used": None,
        }

    # --- Metrics ---
    def get_metrics(self) -> Dict[str, Any]:
        total = self._metrics["total_messages"] or 1
        rate = (self._metrics["successes"] / total) * 100.0
        return {
            **self._metrics,
            "success_rate": rate,
        }

    def reset_metrics(self) -> None:
        self._metrics.update({
            "total_messages": 0,
            "successes": 0,
            "failures": 0,
            "last_used": None,
        })

    # --- Main processing entrypoint used by the system ---
    def process_message(self, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self._metrics["total_messages"] += 1
        self._metrics["last_used"] = datetime.now().isoformat()

        try:
            result = self._process_specific(message, context or {})
            self._metrics["successes"] += 1
            return {
                "success": True,
                "result": result,
                "agent": self.name,
                "timestamp": self._metrics["last_used"],
            }
        except Exception as e:
            self._metrics["failures"] += 1
            self.logger.exception(f"Error in {self.name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.name,
                "timestamp": self._metrics["last_used"],
            }

    # --- To be implemented by subclasses ---
    def _process_specific(self, message: str, context: Dict[str, Any]) -> Any:
        raise NotImplementedError("Subclasses must implement _process_specific()")
