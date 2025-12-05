"""
Multi-Agent Research Mode for complex queries.

Phase 6 Implementation:
- Parallel research coordination
- Result synthesis from multiple agents
- Consensus building
- Conflict resolution
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed


class ResearchStrategy(Enum):
    """Strategy for multi-agent research."""
    PARALLEL = "parallel"       # All agents research simultaneously
    SEQUENTIAL = "sequential"   # Agents research in order
    HIERARCHICAL = "hierarchical"  # Lead agent coordinates sub-agents


@dataclass
class ResearchTask:
    """A task assigned to a research agent."""
    task_id: str
    query: str
    focus_area: Optional[str] = None
    priority: int = 1
    timeout_seconds: float = 30.0
    
    # Results
    status: str = "pending"  # pending, running, completed, failed, timeout
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "query": self.query,
            "focus_area": self.focus_area,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


@dataclass
class ResearchFinding:
    """A finding from research."""
    source_agent: str
    content: str
    confidence: float = 0.5
    sources: List[str] = field(default_factory=list)
    entities: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source_agent": self.source_agent,
            "content": self.content,
            "confidence": self.confidence,
            "sources": self.sources,
            "entities": self.entities,
        }


@dataclass
class SynthesizedResult:
    """Synthesized result from multiple research findings."""
    summary: str
    key_points: List[str]
    findings: List[ResearchFinding]
    consensus_confidence: float
    conflicts: List[Dict[str, Any]]
    sources: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "summary": self.summary,
            "key_points": self.key_points,
            "findings": [f.to_dict() for f in self.findings],
            "consensus_confidence": self.consensus_confidence,
            "conflicts": self.conflicts,
            "sources": self.sources,
        }


class ResearchAgent:
    """
    Base class for research sub-agents.
    
    Specialized for different aspects of research:
    - KB search
    - FAQ lookup
    - Product info
    - Pricing details
    - Policy/rules
    """
    
    def __init__(
        self,
        name: str,
        focus_areas: List[str],
        search_fn: Optional[Callable] = None,
    ) -> None:
        self.name = name
        self.focus_areas = focus_areas
        self.search_fn = search_fn
    
    def research(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ResearchFinding:
        """
        Conduct research on the query.
        
        Override this in specialized sub-agents.
        """
        # Default implementation - keyword search
        results = []
        confidence = 0.0
        sources = []
        
        if self.search_fn:
            search_results = self.search_fn(query, limit=3)
            for r in search_results:
                results.append(r.get("content", ""))
                sources.append(r.get("doc_id", ""))
                confidence = max(confidence, r.get("relevance_score", 0) / 10)
        
        content = "\n".join(results) if results else "No relevant information found."
        
        return ResearchFinding(
            source_agent=self.name,
            content=content,
            confidence=min(1.0, confidence),
            sources=sources,
        )
    
    def can_handle(self, query: str, focus_area: Optional[str] = None) -> bool:
        """Check if this agent can handle the query focus area."""
        if not focus_area:
            return True
        return focus_area.lower() in [fa.lower() for fa in self.focus_areas]


class MultiAgentCoordinator:
    """
    Coordinator for multi-agent research.
    
    Features:
    - Parallel execution with thread pool
    - Timeout handling
    - Result synthesis
    - Conflict detection and resolution
    """
    
    def __init__(
        self,
        agents: Optional[List[ResearchAgent]] = None,
        strategy: ResearchStrategy = ResearchStrategy.PARALLEL,
        max_workers: int = 4,
        default_timeout: float = 30.0,
    ) -> None:
        self.agents = agents or []
        self.strategy = strategy
        self.max_workers = max_workers
        self.default_timeout = default_timeout
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
    
    def add_agent(self, agent: ResearchAgent) -> None:
        """Add a research agent."""
        self.agents.append(agent)
    
    def research(
        self,
        query: str,
        focus_areas: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> SynthesizedResult:
        """
        Conduct multi-agent research.
        
        Args:
            query: Research query
            focus_areas: Optional list of focus areas to research
            context: Additional context for agents
            timeout: Timeout in seconds
        
        Returns:
            SynthesizedResult with combined findings
        """
        timeout = timeout or self.default_timeout
        
        # Create tasks
        tasks = self._create_tasks(query, focus_areas)
        
        # Execute based on strategy
        if self.strategy == ResearchStrategy.PARALLEL:
            findings = self._execute_parallel(tasks, context, timeout)
        elif self.strategy == ResearchStrategy.SEQUENTIAL:
            findings = self._execute_sequential(tasks, context, timeout)
        else:
            findings = self._execute_hierarchical(tasks, context, timeout)
        
        # Synthesize results
        return self._synthesize(query, findings)
    
    def _create_tasks(
        self,
        query: str,
        focus_areas: Optional[List[str]] = None,
    ) -> List[ResearchTask]:
        """Create research tasks."""
        tasks = []
        
        if focus_areas:
            # Create task for each focus area
            for i, area in enumerate(focus_areas):
                task = ResearchTask(
                    task_id=f"task_{i}",
                    query=query,
                    focus_area=area,
                    priority=len(focus_areas) - i,
                )
                tasks.append(task)
        else:
            # Single task without focus
            task = ResearchTask(
                task_id="task_0",
                query=query,
            )
            tasks.append(task)
        
        return tasks
    
    def _execute_parallel(
        self,
        tasks: List[ResearchTask],
        context: Optional[Dict[str, Any]],
        timeout: float,
    ) -> List[ResearchFinding]:
        """Execute tasks in parallel."""
        findings = []
        futures = {}
        
        for task in tasks:
            # Find agents that can handle this task
            eligible_agents = [
                a for a in self.agents
                if a.can_handle(task.query, task.focus_area)
            ]
            
            for agent in eligible_agents:
                future = self._executor.submit(
                    self._run_agent_task,
                    agent,
                    task,
                    context,
                )
                futures[future] = (agent, task)
        
        # Collect results with timeout
        import time
        start = time.time()
        
        for future in as_completed(futures, timeout=timeout):
            agent, task = futures[future]
            try:
                finding = future.result()
                findings.append(finding)
                task.status = "completed"
            except Exception as e:
                task.status = "failed"
                task.error = str(e)
            
            # Check overall timeout
            if time.time() - start > timeout:
                break
        
        return findings
    
    def _execute_sequential(
        self,
        tasks: List[ResearchTask],
        context: Optional[Dict[str, Any]],
        timeout: float,
    ) -> List[ResearchFinding]:
        """Execute tasks sequentially."""
        import time
        findings = []
        start = time.time()
        
        # Sort by priority
        tasks = sorted(tasks, key=lambda t: -t.priority)
        
        for task in tasks:
            if time.time() - start > timeout:
                task.status = "timeout"
                continue
            
            # Find first eligible agent
            for agent in self.agents:
                if agent.can_handle(task.query, task.focus_area):
                    try:
                        finding = self._run_agent_task(agent, task, context)
                        findings.append(finding)
                        task.status = "completed"
                        break
                    except Exception as e:
                        task.status = "failed"
                        task.error = str(e)
        
        return findings
    
    def _execute_hierarchical(
        self,
        tasks: List[ResearchTask],
        context: Optional[Dict[str, Any]],
        timeout: float,
    ) -> List[ResearchFinding]:
        """Execute with lead agent coordination."""
        # For hierarchical, first agent is the lead
        if not self.agents:
            return []
        
        lead = self.agents[0]
        sub_agents = self.agents[1:]
        
        # Lead gets initial context
        lead_finding = lead.research(tasks[0].query if tasks else "", context)
        findings = [lead_finding]
        
        # Sub-agents get lead's context
        enriched_context = {
            **(context or {}),
            "lead_finding": lead_finding.content,
        }
        
        # Execute sub-agents in parallel
        sub_tasks = tasks[1:] if len(tasks) > 1 else tasks
        sub_findings = self._execute_parallel(sub_tasks, enriched_context, timeout / 2)
        findings.extend(sub_findings)
        
        return findings
    
    def _run_agent_task(
        self,
        agent: ResearchAgent,
        task: ResearchTask,
        context: Optional[Dict[str, Any]],
    ) -> ResearchFinding:
        """Run a single agent task."""
        import time
        start = time.time()
        
        task.status = "running"
        
        # Enrich context with task info
        task_context = {
            **(context or {}),
            "focus_area": task.focus_area,
        }
        
        finding = agent.research(task.query, task_context)
        
        task.duration_ms = int((time.time() - start) * 1000)
        
        return finding
    
    def _synthesize(
        self,
        query: str,
        findings: List[ResearchFinding],
    ) -> SynthesizedResult:
        """Synthesize findings into a coherent result."""
        if not findings:
            return SynthesizedResult(
                summary="No research findings available.",
                key_points=[],
                findings=[],
                consensus_confidence=0.0,
                conflicts=[],
                sources=[],
            )
        
        # Collect all sources
        all_sources = []
        for f in findings:
            all_sources.extend(f.sources)
        unique_sources = list(set(all_sources))
        
        # Calculate consensus confidence
        confidences = [f.confidence for f in findings]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        # Variance indicates disagreement
        variance = sum((c - avg_confidence) ** 2 for c in confidences) / len(confidences) if confidences else 0
        consensus_confidence = avg_confidence * (1 - min(1, variance))
        
        # Detect conflicts (simplified - looks for contradictory statements)
        conflicts = self._detect_conflicts(findings)
        
        # Extract key points
        key_points = self._extract_key_points(findings)
        
        # Generate summary
        summary = self._generate_summary(query, findings, key_points)
        
        return SynthesizedResult(
            summary=summary,
            key_points=key_points,
            findings=findings,
            consensus_confidence=consensus_confidence,
            conflicts=conflicts,
            sources=unique_sources,
        )
    
    def _detect_conflicts(
        self,
        findings: List[ResearchFinding],
    ) -> List[Dict[str, Any]]:
        """Detect conflicting information in findings."""
        conflicts = []
        
        # Simple conflict detection - look for numeric differences
        numbers_by_agent: Dict[str, List[Tuple[str, float]]] = {}
        
        import re
        for finding in findings:
            # Extract numbers with context
            matches = re.findall(r'([\w\s]+)[:\s]+([₦N]?\d+(?:,\d+)*(?:\.\d+)?)', finding.content)
            for context, number in matches:
                key = context.strip().lower()
                try:
                    value = float(number.replace('₦', '').replace('N', '').replace(',', ''))
                    if key not in numbers_by_agent:
                        numbers_by_agent[key] = []
                    numbers_by_agent[key].append((finding.source_agent, value))
                except ValueError:
                    continue
        
        # Check for significant differences
        for key, values in numbers_by_agent.items():
            if len(values) > 1:
                nums = [v[1] for v in values]
                if max(nums) > 0 and (max(nums) - min(nums)) / max(nums) > 0.1:
                    conflicts.append({
                        "type": "numeric_conflict",
                        "context": key,
                        "values": values,
                    })
        
        return conflicts
    
    def _extract_key_points(
        self,
        findings: List[ResearchFinding],
    ) -> List[str]:
        """Extract key points from findings."""
        key_points = []
        
        for finding in findings:
            # Split into sentences
            sentences = finding.content.split('.')
            
            # Take first substantive sentence from each finding
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 20 and sentence not in key_points:
                    key_points.append(sentence)
                    break
        
        return key_points[:5]  # Limit to 5 key points
    
    def _generate_summary(
        self,
        query: str,
        findings: List[ResearchFinding],
        key_points: List[str],
    ) -> str:
        """Generate a summary from findings."""
        # Simple summary - combine high-confidence findings
        high_confidence = [f for f in findings if f.confidence > 0.5]
        
        if high_confidence:
            # Use highest confidence finding as base
            best = max(high_confidence, key=lambda f: f.confidence)
            summary = f"Based on {len(findings)} sources: {best.content[:200]}"
            
            if len(high_confidence) > 1:
                summary += f" (Corroborated by {len(high_confidence) - 1} other sources)"
        elif findings:
            summary = f"Limited information found: {findings[0].content[:200]}"
        else:
            summary = f"No relevant information found for: {query}"
        
        return summary
    
    def shutdown(self) -> None:
        """Shutdown the executor."""
        self._executor.shutdown(wait=False)


# ============================================================
# Pre-configured Research Agents
# ============================================================

def create_kb_research_agent(search_fn: Callable) -> ResearchAgent:
    """Create a KB search focused research agent."""
    return ResearchAgent(
        name="kb_searcher",
        focus_areas=["knowledge_base", "documentation", "faq"],
        search_fn=search_fn,
    )


def create_pricing_research_agent(search_fn: Callable) -> ResearchAgent:
    """Create a pricing focused research agent."""
    return ResearchAgent(
        name="pricing_researcher",
        focus_areas=["pricing", "rates", "fees", "costs"],
        search_fn=search_fn,
    )


def create_policy_research_agent(search_fn: Callable) -> ResearchAgent:
    """Create a policy/rules focused research agent."""
    return ResearchAgent(
        name="policy_researcher",
        focus_areas=["policy", "rules", "terms", "conditions", "limits"],
        search_fn=search_fn,
    )


def create_product_research_agent(search_fn: Callable) -> ResearchAgent:
    """Create a product info focused research agent."""
    return ResearchAgent(
        name="product_researcher",
        focus_areas=["product", "service", "features", "bundles", "plans"],
        search_fn=search_fn,
    )


def build_default_coordinator(search_fn: Callable) -> MultiAgentCoordinator:
    """Build a default multi-agent coordinator."""
    coordinator = MultiAgentCoordinator(
        strategy=ResearchStrategy.PARALLEL,
        max_workers=4,
    )
    
    coordinator.add_agent(create_kb_research_agent(search_fn))
    coordinator.add_agent(create_pricing_research_agent(search_fn))
    coordinator.add_agent(create_policy_research_agent(search_fn))
    coordinator.add_agent(create_product_research_agent(search_fn))
    
    return coordinator
