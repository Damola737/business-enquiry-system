"""
Evaluation runner with comprehensive metrics.

Phase 2 Implementation: Eval harness with:
- Routing accuracy scoring
- Entity extraction metrics
- RAG groundedness checks
- Escalation correctness
- Tool efficiency tracking
- Aggregate reporting
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from eval.models import EvalCase, EvalResult, EvalSuiteResult, MetricScores
from mvp_pipeline import SimpleCustomerServicePipeline


def load_cases(path: Path) -> List[EvalCase]:
    """Load evaluation cases from JSON file."""
    cases: List[EvalCase] = []
    if not path.is_file():
        return cases
    with path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    for idx, item in enumerate(raw):
        if "id" not in item:
            item["id"] = f"case_{idx + 1}"
        cases.append(EvalCase(**item))
    return cases


def calculate_metrics(
    case: EvalCase,
    output: Dict[str, Any],
    final_response: str,
) -> MetricScores:
    """
    Calculate detailed metrics for an evaluation case.
    
    Implements Phase 2 metrics:
    - routing_accuracy: 1.0 if correct route, 0.0 otherwise
    - entity_extraction: Jaccard similarity of extracted vs expected entities
    - rag_groundedness: Simple check if KB sources are mentioned/used
    - escalation_correctness: 1.0 if escalation matches expectation
    - tool_efficiency: Ratio of expected to actual tool calls
    - response_quality: Content match score
    """
    metrics = MetricScores()
    classification = output.get("classification", {})
    
    # 1. Routing Accuracy
    if case.expected_route:
        actual_route = output.get("selected_agent", "")
        metrics.routing_accuracy = 1.0 if case.expected_route in actual_route else 0.0
    else:
        metrics.routing_accuracy = 1.0  # No route expectation
    
    # 2. Entity Extraction
    expected_entities = case.expected_entities or {}
    extracted_entities = output.get("extracted_entities", {})
    
    if expected_entities:
        found = 0
        metrics.entities_found = {}
        metrics.entities_missing = []
        
        for key, expected_value in expected_entities.items():
            actual_value = extracted_entities.get(key)
            if actual_value is not None:
                # Flexible matching
                if str(actual_value).lower() == str(expected_value).lower():
                    found += 1
                    metrics.entities_found[key] = actual_value
                elif str(expected_value).lower() in str(actual_value).lower():
                    found += 0.5
                    metrics.entities_found[key] = actual_value
                else:
                    metrics.entities_missing.append(key)
            else:
                metrics.entities_missing.append(key)
        
        metrics.entity_extraction = found / len(expected_entities) if expected_entities else 1.0
    else:
        metrics.entity_extraction = 1.0  # No entity expectations
    
    # 3. RAG Groundedness
    # Check if expected sources appear in the response or were retrieved
    expected_sources = case.rag_sources or []
    retrieved = output.get("kb_results", [])
    response_lower = final_response.lower()
    
    if expected_sources:
        source_matches = 0
        metrics.sources_expected = expected_sources
        metrics.sources_used = []
        
        for source in expected_sources:
            source_lower = source.lower()
            # Check if source content appears in response
            if source_lower in response_lower:
                source_matches += 1
                metrics.sources_used.append(source)
            # Also check retrieved KB results
            elif any(source_lower in str(r).lower() for r in retrieved):
                source_matches += 0.5
                metrics.sources_used.append(source)
        
        metrics.rag_groundedness = source_matches / len(expected_sources)
    else:
        # If no explicit sources expected, check that response isn't hallucinating
        # by looking for KB retrieval in the output
        if retrieved:
            metrics.rag_groundedness = 0.8  # Some retrieval happened
        else:
            metrics.rag_groundedness = 0.5  # No retrieval, neutral score
    
    # 4. Escalation Correctness
    actual_escalation = output.get("escalated", False) or "escalat" in final_response.lower()
    
    if case.expected_escalation is not None:
        if case.expected_escalation == actual_escalation:
            metrics.escalation_correctness = 1.0
        else:
            metrics.escalation_correctness = 0.0
    else:
        metrics.escalation_correctness = 1.0  # No expectation
    
    # 5. Tool Efficiency
    expected_tools = case.expected_tool_calls or []
    actual_tools = output.get("tools_called", [])
    metrics.tools_expected = expected_tools
    metrics.tools_called = actual_tools
    
    if expected_tools:
        expected_set = set(expected_tools)
        actual_set = set(actual_tools)
        
        # Precision: were the called tools expected?
        if actual_set:
            precision = len(expected_set & actual_set) / len(actual_set)
        else:
            precision = 1.0 if not expected_set else 0.0
        
        # Recall: were all expected tools called?
        if expected_set:
            recall = len(expected_set & actual_set) / len(expected_set)
        else:
            recall = 1.0
        
        # F1 score
        if precision + recall > 0:
            metrics.tool_efficiency = 2 * precision * recall / (precision + recall)
        else:
            metrics.tool_efficiency = 0.0
    else:
        # No tools expected - penalize if unnecessary tools were called
        if actual_tools:
            metrics.tool_efficiency = 0.7  # Slight penalty
        else:
            metrics.tool_efficiency = 1.0
    
    # 6. Response Quality
    # Based on must_include/must_not_include matching
    must_include = case.expected_must_include or []
    must_not_include = case.expected_must_not_include or []
    
    include_score = 1.0
    exclude_score = 1.0
    
    if must_include:
        matched = sum(1 for t in must_include if t.lower() in response_lower)
        include_score = matched / len(must_include)
    
    if must_not_include:
        violated = sum(1 for t in must_not_include if t.lower() in response_lower)
        exclude_score = 1.0 - (violated / len(must_not_include))
    
    metrics.response_quality = (include_score + exclude_score) / 2
    
    return metrics


def evaluate_case(
    pipeline: SimpleCustomerServicePipeline,
    case: EvalCase,
) -> EvalResult:
    """
    Evaluate a single test case and return detailed results.
    """
    message = case.input_messages[-1] if case.input_messages else ""
    
    start_time = time.time()
    output = pipeline.process(
        customer_message=message,
        customer_phone="+2348012345678",
        customer_name="Eval User",
        tenant_id=case.tenant_id,
    )
    latency_ms = int((time.time() - start_time) * 1000)
    
    classification: Dict[str, Any] = output.get("classification", {})
    final_response = str(output.get("final_response", ""))
    
    # Calculate comprehensive metrics
    metrics = calculate_metrics(case, output, final_response)
    
    # Legacy checks
    domain_ok = True
    intent_ok = True
    content_ok = True
    route_ok = True
    escalation_ok = True
    entities_ok = True
    tools_ok = True
    
    if case.expected_domain:
        domain_ok = classification.get("service_domain") == case.expected_domain
    
    if case.expected_intent:
        intent_ok = classification.get("intent") == case.expected_intent
    
    if case.expected_route:
        route_ok = metrics.routing_accuracy >= 0.5
    
    if case.expected_escalation is not None:
        escalation_ok = metrics.escalation_correctness >= 0.5
    
    if case.expected_entities:
        entities_ok = metrics.entity_extraction >= 0.5
    
    if case.expected_tool_calls:
        tools_ok = metrics.tool_efficiency >= 0.5
    
    for token in case.expected_must_include:
        if token and token.lower() not in final_response.lower():
            content_ok = False
            break
    
    for token in case.expected_must_not_include:
        if token and token.lower() in final_response.lower():
            content_ok = False
            break
    
    passed = all([
        domain_ok, intent_ok, content_ok, route_ok,
        escalation_ok, entities_ok, tools_ok
    ])
    
    return EvalResult(
        case=case,
        passed=passed,
        domain_ok=domain_ok,
        intent_ok=intent_ok,
        content_ok=content_ok,
        route_ok=route_ok,
        escalation_ok=escalation_ok,
        entities_ok=entities_ok,
        tools_ok=tools_ok,
        metrics=metrics,
        latency_ms=latency_ms,
        details={
            "classification": classification,
            "final_response": final_response,
            "status": output.get("status"),
        },
    )


def aggregate_results(
    suite_name: str,
    results: List[EvalResult],
) -> EvalSuiteResult:
    """
    Aggregate individual results into suite-level metrics.
    """
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    
    suite_result = EvalSuiteResult(
        suite_name=suite_name,
        total_cases=total,
        passed_cases=passed,
        failed_cases=total - passed,
        results=results,
    )
    
    if total == 0:
        return suite_result
    
    # Aggregate metric scores
    routing_scores = []
    entity_scores = []
    rag_scores = []
    escalation_scores = []
    tool_scores = []
    quality_scores = []
    overall_scores = []
    latencies = []
    
    for r in results:
        if r.metrics:
            routing_scores.append(r.metrics.routing_accuracy)
            entity_scores.append(r.metrics.entity_extraction)
            rag_scores.append(r.metrics.rag_groundedness)
            escalation_scores.append(r.metrics.escalation_correctness)
            tool_scores.append(r.metrics.tool_efficiency)
            quality_scores.append(r.metrics.response_quality)
            overall_scores.append(r.metrics.overall_score())
        latencies.append(r.latency_ms)
    
    suite_result.avg_routing_accuracy = sum(routing_scores) / len(routing_scores) if routing_scores else 0
    suite_result.avg_entity_extraction = sum(entity_scores) / len(entity_scores) if entity_scores else 0
    suite_result.avg_rag_groundedness = sum(rag_scores) / len(rag_scores) if rag_scores else 0
    suite_result.avg_escalation_correctness = sum(escalation_scores) / len(escalation_scores) if escalation_scores else 0
    suite_result.avg_tool_efficiency = sum(tool_scores) / len(tool_scores) if tool_scores else 0
    suite_result.avg_response_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
    suite_result.avg_overall_score = sum(overall_scores) / len(overall_scores) if overall_scores else 0
    
    suite_result.avg_latency_ms = sum(latencies) / len(latencies) if latencies else 0
    suite_result.p95_latency_ms = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0
    
    # Results by domain
    for r in results:
        domain = r.case.expected_domain or "unknown"
        if domain not in suite_result.results_by_domain:
            suite_result.results_by_domain[domain] = {"passed": 0, "failed": 0}
        if r.passed:
            suite_result.results_by_domain[domain]["passed"] += 1
        else:
            suite_result.results_by_domain[domain]["failed"] += 1
    
    # Results by difficulty
    for r in results:
        diff = r.case.difficulty or "medium"
        if diff not in suite_result.results_by_difficulty:
            suite_result.results_by_difficulty[diff] = {"passed": 0, "failed": 0}
        if r.passed:
            suite_result.results_by_difficulty[diff]["passed"] += 1
        else:
            suite_result.results_by_difficulty[diff]["failed"] += 1
    
    # Results by tag
    for r in results:
        for tag in r.case.tags:
            if tag not in suite_result.results_by_tag:
                suite_result.results_by_tag[tag] = {"passed": 0, "failed": 0}
            if r.passed:
                suite_result.results_by_tag[tag]["passed"] += 1
            else:
                suite_result.results_by_tag[tag]["failed"] += 1
    
    return suite_result


def print_report(suite_result: EvalSuiteResult) -> None:
    """Print formatted evaluation report."""
    print("\n" + "=" * 60)
    print(f"  EVAL SUITE: {suite_result.suite_name}")
    print("=" * 60)
    
    print(f"\n📊 SUMMARY")
    print(f"   Total Cases: {suite_result.total_cases}")
    print(f"   Passed: {suite_result.passed_cases} ({suite_result.pass_rate() * 100:.1f}%)")
    print(f"   Failed: {suite_result.failed_cases}")
    
    print(f"\n📈 METRICS (averages)")
    print(f"   Routing Accuracy:      {suite_result.avg_routing_accuracy:.3f}")
    print(f"   Entity Extraction:     {suite_result.avg_entity_extraction:.3f}")
    print(f"   RAG Groundedness:      {suite_result.avg_rag_groundedness:.3f}")
    print(f"   Escalation Correct:    {suite_result.avg_escalation_correctness:.3f}")
    print(f"   Tool Efficiency:       {suite_result.avg_tool_efficiency:.3f}")
    print(f"   Response Quality:      {suite_result.avg_response_quality:.3f}")
    print(f"   Overall Score:         {suite_result.avg_overall_score:.3f}")
    
    print(f"\n⏱️  PERFORMANCE")
    print(f"   Avg Latency: {suite_result.avg_latency_ms:.0f}ms")
    print(f"   P95 Latency: {suite_result.p95_latency_ms:.0f}ms")
    
    if suite_result.results_by_domain:
        print(f"\n📁 BY DOMAIN")
        for domain, counts in suite_result.results_by_domain.items():
            total = counts["passed"] + counts["failed"]
            rate = counts["passed"] / total * 100 if total > 0 else 0
            print(f"   {domain}: {counts['passed']}/{total} ({rate:.0f}%)")
    
    if suite_result.results_by_difficulty:
        print(f"\n🎯 BY DIFFICULTY")
        for diff, counts in suite_result.results_by_difficulty.items():
            total = counts["passed"] + counts["failed"]
            rate = counts["passed"] / total * 100 if total > 0 else 0
            print(f"   {diff}: {counts['passed']}/{total} ({rate:.0f}%)")
    
    print(f"\n📝 INDIVIDUAL RESULTS")
    for idx, res in enumerate(suite_result.results, 1):
        status = "✅ PASS" if res.passed else "❌ FAIL"
        case_id = res.case.id or f"case_{idx}"
        domain = res.case.expected_domain or "?"
        score = res.metrics.overall_score() if res.metrics else 0
        
        print(f"   [{idx}] {status} {case_id} (domain={domain}, score={score:.2f})")
        
        if not res.passed:
            checks = []
            if not res.domain_ok: checks.append("domain")
            if not res.intent_ok: checks.append("intent")
            if not res.content_ok: checks.append("content")
            if not res.route_ok: checks.append("route")
            if not res.escalation_ok: checks.append("escalation")
            if not res.entities_ok: checks.append("entities")
            if not res.tools_ok: checks.append("tools")
            print(f"       Failed checks: {', '.join(checks)}")
    
    print("\n" + "=" * 60)


def save_report(suite_result: EvalSuiteResult, output_path: Path) -> None:
    """Save evaluation report to JSON file."""
    report = suite_result.to_summary_dict()
    report["individual_results"] = [r.to_report_dict() for r in suite_result.results]
    
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Report saved to: {output_path}")


def run() -> None:
    """Main entry point for evaluation runner."""
    parser = argparse.ArgumentParser(
        description="Run eval suite against the MVP pipeline with comprehensive metrics."
    )
    parser.add_argument(
        "--suite",
        default="smoke",
        help="Eval suite name (used to pick JSON file in eval/cases).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path to save JSON report (optional).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed output for each case.",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    cases_path = root / "cases" / f"{args.suite}.json"

    cases = load_cases(cases_path)
    if not cases:
        print(f"No eval cases found at {cases_path}")
        return

    print(f"🚀 Running eval suite: {args.suite}")
    print(f"   Loading {len(cases)} cases...")
    
    pipeline = SimpleCustomerServicePipeline()
    results: List[EvalResult] = []

    for idx, case in enumerate(cases, 1):
        print(f"   [{idx}/{len(cases)}] Evaluating {case.id or f'case_{idx}'}...", end=" ")
        result = evaluate_case(pipeline, case)
        results.append(result)
        status = "✅" if result.passed else "❌"
        print(f"{status} ({result.latency_ms}ms)")
        
        if args.verbose and not result.passed:
            print(f"       Response: {result.details.get('final_response', '')[:100]}...")

    # Aggregate and report
    suite_result = aggregate_results(args.suite, results)
    print_report(suite_result)
    
    # Save report if requested
    if args.output:
        save_report(suite_result, Path(args.output))


if __name__ == "__main__":
    run()

