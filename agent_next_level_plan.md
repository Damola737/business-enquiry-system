# Taking Your Multi‑Tenant Agent Platform to the Next Level  
*(Detailed implementation plan + DoD checklists, and includes the earlier recommendations.)*

## Context (what you already have)
From your project summary, your platform already has: multi-tenant config + isolation, a pipeline-style orchestrator (`SimpleCustomerServicePipeline`), structured conversation state (`ConversationContext`, `AgentResponse`), tenant-scoped KB ingestion/search (RAG-ready), escalation summarization, and observability foundations (structured logs + per-tenant metrics goals). fileciteturn0file0

That’s a strong base: you can now focus on **reliability, reproducibility, and scaling quality** rather than just adding features.

---

## Earlier recommendations (carried forward)
You’ve already got the right foundation: a **workflow-style, multi‑tenant orchestration layer** (`SimpleCustomerServicePipeline`, `ConversationContext`, routing to specialist agents, tenant-scoped KB, observability, onboarding tooling) where behavior is driven by config rather than hard-coded domain logic.

To take it to the next level, evolve it into an **eval-driven, context-engineered, tool-first agent platform** (keeping complexity only where it pays off).

### 1) Make “evals + tracing” your core loop (before adding more agents)
- Trace every run: prompt+config version, tool calls/results, retrieved chunks, final output, latency, token cost, outcome labels per tenant.
- Start with small eval packs and run them on every prompt/config change.
- Add an LLM-as-judge rubric for end-to-end quality and spot-check with humans.
- Add continuous “canary evals” in production-like settings to catch regressions.

### 2) Build a Context Engine (treat tokens like scarce RAM)
- A `ContextPack` builder that deterministically assembles: tenant “operating manual”, conversation summary + open slots, minimal KB/tool results needed now.
- Compaction + tool-result clearing rules.
- Structured note-taking / casefile (`case_state.json`) persisted outside model context.
- Add an internal “reflect step” after tool results to check sufficiency, policy, and next action.

### 3) Upgrade your tool layer into a product (ergonomics win reliability)
- Namespace tools; return high-signal fields; pagination/truncation/errors that teach the model.
- Tool-use examples for tricky schemas.
- Tool discovery (`search_tools`) so only core tools are always loaded.

### 4) Make RAG actually great: Contextual Retrieval + hybrid search + reranking
- Contextual Retrieval preprocessing; hybrid (BM25 + vector) with reranking; aggressive top_k/context-size control.
- A final citation/attribution step mapping claims → sources.

### 5) Add multi-agent only where it pays off (research/breadth + hard cases)
- Orchestrator-worker for high-value queries; explicit effort scaling; parallel tool calling with budgets.

### 6) Security: sandbox tools/code so you can safely increase autonomy
- FS + network isolation; host allowlists; audit logs.

### 7) Tenant-facing “skills” as your scaling lever
- Per-tenant (or per-domain) playbooks (“skills”) loaded progressively and mapped to routing outputs.

### Scoreboard
- Resolution vs escalation rate per tenant
- Groundedness/citation accuracy
- Pass^k-style workflow reliability
- Token cost + latency per route/toolchain

---

# Detailed delivery plan (with DoD tasks)

## Global Definition of Done (applies to every epic)
A work item is “done” only if:
- **Reproducible:** runs record `tenant_id`, `conversation_id`, model, prompt bundle hash, config version, toolset version.
- **Tested:** unit tests + at least one integration test (or eval) covering the happy path and a failure mode.
- **Observable:** emits structured logs + metrics; failures are discoverable and debuggable.
- **Documented:** README or internal doc explaining how to use/extend it; includes an example.
- **Safe by default:** redaction for PII in logs/traces; tool permissions respected; secrets never logged.

---

## Phase 0 — Platform foundations (versioning + contracts)
**Goal:** make every run replayable and every interface explicit.

### 0.1 Add artifact versioning across prompts/config/tools
**Tasks**
- Introduce a `PromptBundle` concept (templates + few-shot examples + policy snippets).
- Add `prompt_bundle_hash` (e.g., SHA256 of rendered templates + key config parts).
- Add `config_version` for tenant config (monotonic counter or git hash).
- Add `toolset_version` for tool registry (hash of tool specs).

**DoD**
- A single run record contains `tenant_id`, `conversation_id`, `model_id`, `prompt_bundle_hash`, `config_version`, `toolset_version`.
- You can replay an interaction by pinning these versions (even if outputs differ due to sampling).

### 0.2 Standardize structured outputs between pipeline stages
**Tasks**
- Define typed schemas (Pydantic) for:
  - `ClassificationResult` (domain/intent/entities + confidence + rationale-for-debugging (not shown to user))
  - `RetrievalResult` (chunk_id/document_id/source/snippet/score)
  - `ToolCallRecord` (tool name, input, output summary, error category)
  - `EscalationDecision` (trigger, severity, summary)
- Update pipeline stages to return these types.

**DoD**
- No stage passes raw dicts across boundaries without validation.
- Schema validation failures are surfaced with actionable error messages.

---

## Phase 1 — Tracing & run records (the “black box recorder”)
**Goal:** see exactly what happened in a run and why.

### 1.1 Implement a TraceStore
**Tasks**
- Create `TraceStore` interface: `start_run()`, `append_span()`, `append_event()`, `finish_run()`.
- Back it with your existing DB (or start with SQLite locally).
- Add indexes on `tenant_id`, `conversation_id`, `route`, `timestamp`.

**DoD**
- Each user message creates exactly one `run` with spans for major steps:
  - classification → retrieval → tool use → response generation → escalation
- You can query traces by `tenant_id` and export them to JSON.

### 1.2 Add span-level instrumentation to `SimpleCustomerServicePipeline`
**Tasks**
- Wrap each pipeline step with timing and structured metadata.
- Record:
  - top_k retrieval + chosen chunks
  - tool calls + tool errors
  - escalation triggers
- Add correlation IDs to logs.

**DoD**
- A single trace view shows step durations and the data artifacts used (without leaking PII).
- You can quickly answer: “Why did it route to X?”, “What did it retrieve?”, “What tool failed?”

### 1.3 Add PII redaction rules for traces/logs
**Tasks**
- Implement a `redact(text)->text` function (regex + tenant-defined sensitive entity patterns).
- Redact at the boundary before persisting traces.

**DoD**
- Test cases prove phone numbers/IDs/etc. are redacted.
- Traces remain useful for debugging after redaction.

---

## Phase 2 — Eval harness (turn changes into measurable progress)
**Goal:** every prompt/config/tool change is gated by evals.

### 2.1 Create an eval dataset format + loader
**Tasks**
- Define `EvalCase` JSON schema:
  - `tenant_id`, `input_messages`, optional `tools_available`, expected `route`, expected `tool_usage` (optional), expected `must_include`/`must_not_include`.
- Build loader that can sample by tenant, route, and difficulty.

**DoD**
- You can run `python -m eval.run --tenant X --suite smoke` and get a report.

### 2.2 Build evaluation metrics (starter set)
**Tasks**
- Implement:
  - **Routing accuracy** (expected route vs predicted)
  - **Entity extraction accuracy** (expected entity keys)
  - **RAG groundedness proxy** (answer cites at least one retrieved chunk when retrieval used)
  - **Escalation correctness** (triggered vs expected)
  - **Tool efficiency** (tool calls <= budget)
- Add a simple HTML/Markdown report.

**DoD**
- Report includes pass/fail per test, aggregated metrics, and links to traces for failures.

### 2.3 Add LLM-judge rubric (carefully scoped)
**Tasks**
- Create a judge prompt + scoring rubric (0–5) for:
  - correctness, completeness, tone fit, safety/policy compliance, groundedness when sources exist
- Store judge scores alongside deterministic metrics.

**DoD**
- Judge is used only as an additional signal; deterministic assertions still gate regressions.
- Spot-check script prints the worst 10 cases for human review.

### 2.4 CI gate + “canary evals” in staging-like mode
**Tasks**
- Add a fast “smoke” suite to PR CI (10–30 cases).
- Add nightly full suite (per tenant or representative tenants).
- Add canary suite that runs against current production config snapshots.

**DoD**
- CI fails if key metrics regress beyond thresholds.
- Canary results are visible in dashboard/logs.

---

## Phase 3 — Context Engine (deterministic, minimal, high-signal prompts)
**Goal:** reduce token bloat and hallucinations while improving consistency.

### 3.1 Implement persistent Case State (outside the model)
**Tasks**
- Create `CaseState` store keyed by `(tenant_id, conversation_id)`:
  - slots/entities, user goal, workflow step, constraints, “what we already tried”, last tool outputs summary
- Provide merge/update rules per pipeline stage.

**DoD**
- Agent can resume a conversation with minimal context and still know what step it’s on.
- CaseState never stores raw PII unless explicitly allowed; store hashed/last-4 where possible.

### 3.2 Build a `ContextPackBuilder`
**Tasks**
- Deterministically assemble:
  - tenant operating rules (tone/escalation/validations)
  - compact conversation summary + open slots
  - only the *relevant* KB snippets + tool result summaries
  - a small “plan stub” (next action candidates)
- Add budgets: max tokens per section; truncate by priority.

**DoD**
- For the same state, builder produces identical context (no randomness).
- Token usage decreases measurably (tracked in traces) without eval regression.

### 3.3 Add compaction + tool-result clearing
**Tasks**
- Summarize older conversation turns into a rolling summary.
- Store bulky tool outputs in trace store; keep only a short extraction in CaseState/context.

**DoD**
- Context never includes multi-page dumps.
- Debugging is still possible via trace links.

### 3.4 Add a post-tool “reflect step” (internal)
**Tasks**
- After retrieval/tool calls, run a short internal check:
  - Do we have enough info to answer?
  - If not, what is the single best next question/tool call?
  - Any policy/escalation triggers?
- Store result in trace metadata (not shown to end-user).

**DoD**
- Reduction in “answering too early” errors in evals.
- Increased tool-call correctness (fewer irrelevant calls).

---

## Phase 4 — Tool platform (reliable integrations + discoverability)
**Goal:** tools become standardized building blocks, not one-off code paths.

### 4.1 Introduce ToolSpec + ToolRegistry
**Tasks**
- Define `ToolSpec`:
  - `name`, `description`, `input_schema`, `output_schema`
  - `examples[]`
  - `error_taxonomy` (e.g., auth, not_found, validation, rate_limit, transient)
  - `permissions` (read/write), `tenant_scoped: bool`
- Implement `ToolRegistry` to list and fetch specs.

**DoD**
- Every tool has a spec and at least 2 examples.
- Tools are tenant-scoped by default and enforced in code.

### 4.2 Implement `search_tools(query)` and progressive tool loading
**Tasks**
- Keep only 3–5 essential tools always loaded.
- Allow the agent to call `search_tools` to discover additional tools on demand.
- Cache tool spec results.

**DoD**
- End-to-end demo: agent discovers and uses a non-core tool correctly.
- Tool discovery reduces prompt/tool clutter (measured by token counts).

### 4.3 Build tool budgets + safe retry policy
**Tasks**
- Add per-run budgets:
  - max tool calls
  - max total tool wall time
  - max retries (only for transient errors)
- Add tool idempotency keys for write operations.

**DoD**
- Agent stops escalating tool spam; instead asks user for missing info or escalates cleanly.
- Write tools are safe from accidental duplicates.

### 4.4 Improve tool error messages for “model repair”
**Tasks**
- Standardize tool errors:
  - `error_category`, `human_message`, `model_fix_hint`, `retryable`
- Ensure schema validation errors include exact missing fields / wrong types.

**DoD**
- When a tool call fails due to bad input, the next attempt succeeds >80% on an eval set of “tool failure” cases.

---

## Phase 5 — Retrieval upgrade (Contextual Retrieval + hybrid + rerank + citations)
**Goal:** high-recall retrieval + high-precision context, with auditability.

### 5.1 Add contextual chunk headers during ingestion
**Tasks**
- During ingestion, create `chunk_context` (short, chunk-specific, clarifying metadata).
  - Start with deterministic heuristics (doc title, section headings).
  - Optionally add an LLM-generated 1–2 sentence chunk context (offline job).
- Embed/index `chunk_context + chunk_text`.

**DoD**
- Retrieval improves on a “known-answer” eval set (higher hit rate for correct doc/chunk).
- Ingestion is reproducible and cached (no re-LLM unless source changed).

### 5.2 Implement hybrid retrieval + reranking
**Tasks**
- Add BM25 (lexical) in addition to vector similarity.
- Merge top candidates, then rerank (start with lightweight reranker; optionally upgrade later).

**DoD**
- Measured improvement in retrieval precision/recall on eval suite.
- Latency stays within your target; reranker has a strict budget.

### 5.3 Add citation mapping and “claim → source” checks
**Tasks**
- Keep chunk IDs through the whole pipeline.
- Add a “citation pass” that ensures major claims are supported by retrieved chunks.
- If no support, agent either asks clarification or says it can’t confirm.

**DoD**
- Answers include citations (or source references) whenever retrieval is used.
- “Unsupported claim” rate drops on eval set.

### 5.4 Add retrieval caching + invalidation
**Tasks**
- Cache retrieval results per (tenant_id, normalized_query, KB_version).
- Invalidate cache on ingestion changes.

**DoD**
- Token/cost reduction observable; no stale retrieval after KB updates.

---

## Phase 6 — Multi-agent research mode (only for hard/high-value cases)
**Goal:** better breadth + depth without runaway cost/complexity.

### 6.1 Implement “Research Orchestrator” with bounded workers
**Tasks**
- Add a planner step that creates 2–5 subquestions max.
- Spawn worker agents (parallel) with strict budgets and restricted tools.
- Aggregate into a single answer with deduplication + citations.

**DoD**
- Research mode improves “hard question” eval suite without increasing cost for easy questions.
- Workers never exceed budgets; orchestration is traced.

### 6.2 Add routing rules for when to use multi-agent
**Tasks**
- Trigger only when:
  - ambiguity remains after one retrieval attempt
  - user explicitly asks for comparison/deep research
  - the route is tagged “research-heavy” in tenant config

**DoD**
- Multi-agent is used rarely and intentionally (track % of runs).

---

## Phase 7 — Security sandbox for tools (unlock safe autonomy)
**Goal:** increase capability without risking data exfiltration or unsafe operations.

### 7.1 Create a “Tool Runner” isolation boundary
**Tasks**
- Move tool execution behind a single interface (local service/process):
  - filesystem sandbox: only allow a workspace directory per tenant
  - network egress: deny by default; allowlist per tool
  - timeouts and resource limits
- Store secrets in environment/secret store; never pass secrets into LLM-visible text.

**DoD**
- A malicious prompt cannot read arbitrary files or reach non-allowlisted hosts.
- Audit logs record tool invocations with redacted payloads.

### 7.2 Add permissioning and human-in-the-loop for risky actions (optional but recommended)
**Tasks**
- Mark tools as `read_only`, `write_low_risk`, `write_high_risk`.
- Require explicit confirmation step for `write_high_risk` (or always escalate).

**DoD**
- Writes that could cost money or alter data require safe gating.

---

## Phase 8 — Skills system (tenant playbooks that scale)
**Goal:** scale across tenants without prompt spaghetti.

### 8.1 Define a Skill format + loader
**Tasks**
- Create `skills/{tenant_id}/{skill_name}/`:
  - `SKILL.md` (purpose, when to load, do/don’t, links)
  - optional `forms.json` (slot schema)
  - optional `tool_hints.yaml` (preferred tools, budgets)
- Add loader and a way to map route → skills.

**DoD**
- For a given route, the correct skill is loaded automatically.
- Skills are versioned and referenced in traces (skill_hash).

### 8.2 Update onboarding UI to author skills
**Tasks**
- Admin UI: create/edit a skill, validate required fields, preview the behavior.
- Include “seed templates” for common domains (orders, claims, appointments, refunds, troubleshooting).

**DoD**
- A new tenant can be onboarded with at least 3 skills and a minimal KB without touching core code.

---

## Phase 9 — Scoreboard + dashboards (operationalize quality)
**Goal:** know what’s working, per tenant, and why.

### 9.1 Implement KPI metrics from traces
**Tasks**
- Compute and store:
  - resolution rate, escalation rate
  - average latency, p95 latency
  - average token cost
  - groundedness proxy score (when retrieval used)
  - tool failure rate
  - pass^k workflow reliability (run same test N times; track success rate)

**DoD**
- Metrics are queryable by tenant, route, and time window.

### 9.2 Build a minimal dashboard (Streamlit is fine)
**Tasks**
- Views:
  - Overview per tenant: KPIs, trends
  - Failure analysis: top failing eval cases + trace links
  - KB gaps: frequent queries with low retrieval support
  - Tool health: error categories and hotspots

**DoD**
- Dashboard helps you answer “what should we fix next?” in <5 minutes.

---

# Suggested build order (fastest path to “next level”)
If you want the highest leverage sequence:
1) **Phase 1 (Tracing)** → unlocks debuggability  
2) **Phase 2 (Evals)** → unlocks safe iteration  
3) **Phase 3 (Context Engine)** → unlocks consistency + cost reduction  
4) **Phase 4 (Tools)** and **Phase 5 (Retrieval)** in parallel  
5) Then **Phase 6–9** as you expand autonomy + tenant scale

---

## Appendix: initial “starter eval packs” (what to collect first)
- 20–50 real conversations per tenant (anonymized)
- Balanced across routes: product inquiry, transaction guidance, troubleshooting, escalation cases
- Add “tool failure” cases (missing fields, invalid IDs, rate limit)
- Add “retrieval required” cases (policy, pricing, eligibility)

