# agents/base_agent_v2.py
"""
Enhanced Base Business Agent with Pydantic models and improved metrics tracking.
This is the NEW base class for all agents in the multi-service system.

This module includes graceful fallbacks when optional dependencies are missing
so that agents can run in limited environments (no autogen/pydantic installed).
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import time

# Optional: autogen ConversableAgent
try:
    from autogen import ConversableAgent  # type: ignore
except Exception:  # Fallback dummy agent
    class ConversableAgent:  # type: ignore
        def __init__(self, *args, **kwargs):
            self.name = kwargs.get("name", "Agent")

        def generate_reply(self, messages=None, **kwargs):
            return "(LLM disabled in this environment)"

# Optional: pydantic BaseModel/Field
try:
    from pydantic import BaseModel, Field  # type: ignore
except Exception:  # Minimal shim
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


# ============================================================
# PYDANTIC MODELS
# ============================================================

class AgentMetrics(BaseModel):
    """Track agent performance metrics."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_processing_time_ms: int = 0

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if getattr(self, "total_requests", 0) == 0:
            return 0.0
        return round((self.successful_requests / self.total_requests) * 100, 2)

    @property
    def average_processing_time_ms(self) -> float:
        """Calculate average processing time in milliseconds."""
        if getattr(self, "total_requests", 0) == 0:
            return 0.0
        return round(self.total_processing_time_ms / self.total_requests, 2)


class AgentResponse(BaseModel):
    """Standardized response format from all agents."""
    success: bool
    agent_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    processing_time_ms: int = 0

    # Result data (flexible)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    # Metadata
    confidence: float = 1.0  # 0-1 scale
    fallback_used: bool = False

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()} if "json_encoders" else {}


class ConversationContext(BaseModel):
    """Shared context passed between agents."""
    # Identifiers
    tenant_id: Optional[str] = None
    enquiry_id: str
    customer_id: Optional[str] = None
    session_id: str

    # Customer info
    customer_phone: str
    customer_email: Optional[str] = None
    customer_name: Optional[str] = None
    customer_tier: str = "BRONZE"

    # Classification
    service_domain: Optional[str] = None  # AIRTIME, POWER, DATA, MULTI
    intent: Optional[str] = None
    priority: str = "MEDIUM"
    sentiment: str = "NEUTRAL"

    # Processing state
    agents_involved: List[str] = Field(default_factory=list)
    current_agent: Optional[str] = None
    processing_steps: List[Dict[str, Any]] = Field(default_factory=list)

    # Results
    recommended_actions: List[str] = Field(default_factory=list)
    transaction_id: Optional[str] = None
    resolution_status: str = "PENDING"

    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def add_step(self, agent_name: str, action: str, result: Any):
        """Add a processing step to the history."""
        self.processing_steps.append({
            "agent": agent_name,
            "action": action,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        })
        if agent_name not in self.agents_involved:
            self.agents_involved.append(agent_name)
        self.updated_at = datetime.utcnow()


# ============================================================
# ENHANCED BASE AGENT
# ============================================================

class BaseBusinessAgent(ConversableAgent):
    """
    Enhanced base class for all business agents.

    Features:
    - Inherits from AutoGen's ConversableAgent for GroupChat compatibility
    - Standardized metrics tracking with Pydantic models
    - Consistent logging and error handling
    - Response timing and confidence scoring
    - Context-aware processing
    """

    def __init__(
        self,
        name: str,
        system_message: str,
        llm_config: Dict[str, Any],
        human_input_mode: str = "NEVER",
        max_consecutive_auto_reply: Optional[int] = None,
        description: str = "",
        **kwargs
    ):
        """
        Initialize the base agent.

        Args:
            name: Agent name (e.g., "ClassifierAgent")
            system_message: System prompt defining agent behavior
            llm_config: OpenAI configuration dictionary
            human_input_mode: When to ask for human input
            max_consecutive_auto_reply: Max auto-replies in conversation
            description: Human-readable agent description
            **kwargs: Additional AutoGen parameters
        """
        super().__init__(
            name=name,
            system_message=system_message,
            llm_config=llm_config,
            human_input_mode=human_input_mode,
            max_consecutive_auto_reply=max_consecutive_auto_reply,
            **kwargs
        )

        self.description = description or f"{name} - Business Agent"

        # Set up logging
        self.logger = logging.getLogger(f"agents.{name}")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

        # Initialize metrics
        self.metrics = AgentMetrics()

        # Agent metadata
        self.created_at = datetime.utcnow()

        self.logger.info(f"{self.name} initialized successfully")

    # ========================================
    # Core Processing Methods
    # ========================================

    def process_message(
        self,
        message: str,
        context: Optional[ConversationContext] = None
    ) -> AgentResponse:
        """
        Main entry point for processing messages.

        This method:
        1. Tracks timing
        2. Calls _process_specific (implemented by subclasses)
        3. Records metrics
        4. Returns standardized AgentResponse

        Args:
            message: The message/query to process
            context: Optional conversation context

        Returns:
            AgentResponse with success status and results
        """
        start_time = time.time()

        try:
            self.logger.info(f"{self.name} processing message: {message[:100]}...")

            # Call subclass-specific processing
            result = self._process_specific(message, context)

            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)

            # Record success
            self.record_success(processing_time_ms)

            # Update context if provided
            if context:
                context.add_step(
                    agent_name=self.name,
                    action="process_message",
                    result=result
                )

            return AgentResponse(
                success=True,
                agent_name=self.name,
                processing_time_ms=processing_time_ms,
                result=result
            )

        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            error_msg = str(e)

            self.logger.error(f"{self.name} error: {error_msg}", exc_info=True)
            self.record_failure(error_msg, processing_time_ms)

            return AgentResponse(
                success=False,
                agent_name=self.name,
                processing_time_ms=processing_time_ms,
                error=error_msg
            )

    def _process_specific(
        self,
        message: str,
        context: Optional[ConversationContext]
    ) -> Dict[str, Any]:
        """
        Subclass-specific processing logic.
        MUST be implemented by all subclasses.

        Args:
            message: The message to process
            context: Conversation context

        Returns:
            Dictionary with processing results

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement _process_specific()"
        )

    # ========================================
    # Metrics Recording
    # ========================================

    def record_success(self, processing_time_ms: int = 0):
        """Record a successful operation."""
        self.metrics.total_requests += 1
        self.metrics.successful_requests += 1
        self.metrics.total_processing_time_ms += processing_time_ms

        self.logger.debug(
            f"{self.name} - Success (Total: {self.metrics.total_requests}, "
            f"Success Rate: {self.metrics.success_rate}%)"
        )

    def record_failure(self, error: str = "", processing_time_ms: int = 0):
        """Record a failed operation."""
        self.metrics.total_requests += 1
        self.metrics.failed_requests += 1
        self.metrics.total_processing_time_ms += processing_time_ms

        self.logger.warning(
            f"{self.name} - Failure: {error} "
            f"(Failures: {self.metrics.failed_requests}/{self.metrics.total_requests})"
        )

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get agent performance metrics.

        Returns:
            Dictionary with all metrics and calculated values
        """
        return {
            "agent_name": self.name,
            "total_requests": self.metrics.total_requests,
            "successful_requests": self.metrics.successful_requests,
            "failed_requests": self.metrics.failed_requests,
            "success_rate": self.metrics.success_rate,
            "average_processing_time_ms": self.metrics.average_processing_time_ms,
            "total_processing_time_ms": self.metrics.total_processing_time_ms,
            "uptime_seconds": (datetime.utcnow() - self.created_at).total_seconds()
        }

    def reset_metrics(self):
        """Reset all metrics (useful for testing)."""
        self.metrics = AgentMetrics()
        self.logger.info(f"{self.name} - Metrics reset")

    # ========================================
    # Utility Methods
    # ========================================

    def get_llm_response(self, prompt: str, temperature: Optional[float] = None) -> str:
        """
        Get response from LLM.

        Args:
            prompt: The prompt to send to LLM
            temperature: Optional temperature override

        Returns:
            LLM response as string
        """
        # Optionally override temperature
        if temperature is not None:
            original_temp = self.llm_config.get("temperature", 0.7)
            self.llm_config["temperature"] = temperature

        try:
            response = self.generate_reply(
                messages=[{"role": "user", "content": prompt}]
            )
            return response if isinstance(response, str) else str(response)
        finally:
            # Restore original temperature
            if temperature is not None:
                self.llm_config["temperature"] = original_temp

    def __repr__(self) -> str:
        """String representation of agent."""
        return (
            f"<{self.__class__.__name__}(name='{self.name}', "
            f"requests={self.metrics.total_requests}, "
            f"success_rate={self.metrics.success_rate}%)>"
        )


# ============================================================
# EXAMPLE USAGE
# ============================================================

if __name__ == "__main__":
    # Example of creating a simple agent

    class ExampleAgent(BaseBusinessAgent):
        """Example agent demonstrating usage."""

        def _process_specific(self, message: str, context: Optional[ConversationContext]) -> Dict[str, Any]:
            """Process the message."""
            return {
                "message_received": message,
                "processing_result": "Example processing completed",
                "context_available": context is not None
            }

    # Initialize
    llm_config = {
        "config_list": [{
            "model": "gpt-4o-mini",
            "api_key": "your-key-here"
        }],
        "temperature": 0.3
    }

    agent = ExampleAgent(
        name="ExampleAgent",
        system_message="You are a helpful example agent.",
        llm_config=llm_config,
        description="Demonstrates the base agent pattern"
    )

    # Process a message
    response = agent.process_message("Hello, this is a test message")

    print(f"Success: {response.success}")
    print(f"Result: {response.result}")
    print(f"Processing time: {response.processing_time_ms}ms")

    # Get metrics
    print(f"\nAgent Metrics: {agent.get_metrics()}")
