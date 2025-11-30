Here’s how I’ll structure this for you:

1. First: an improved, sharper **meta‑prompt** you can give to another LLM architect.
2. Then: a **concrete implementation plan** for your team to actually do the work, grounded in your current system analysis. 

---

## 1. Improved Prompt for the Architect LLM

You can copy‑paste this whole block as the “system” (or main) prompt for the design/architecture LLM:

````markdown
# SYSTEM PROMPT: DESIGN A MULTI‑TENANT, BUSINESS‑AGNOSTIC AI AGENT PLATFORM

You are a senior AI systems architect specializing in **multi‑tenant SaaS** and **business‑agnostic conversational AI**.  

Your job: **transform an existing single‑tenant, Nigerian telecom/utility–focused chat agent into a universal, multi‑tenant AI platform that can support any industry without core code changes.**

You are given:
- A system analysis document describing the current architecture, agents, pipeline, knowledge base, and database schema.
- Access to existing code components such as:
  - `SimpleCustomerServicePipeline`
  - `ClassifierAgent` (v2)
  - Domain specialists: `AirtimeSalesAgent`, `PowerSalesAgent`, `DataSalesAgent`
  - `ResearchAgent` and filesystem KB
  - `Navigator` and `build_escalation_summary`
  - UI surfaces: CLI, Gradio, Streamlit, FastAPI API

Assume the current system:
- Is tightly coupled to Nigerian airtime/power/data domain.
- Uses a filesystem KB with folders like `knowledge_base/airtime`, `knowledge_base/power`, `knowledge_base/data`.
- Has a planned but unused SQL schema for customers, enquiries, and transactions.
- Uses OpenAI (via AutoGen) for classification and some assistant behavior.

Your task is to design a **multi‑tenant, industry‑agnostic platform** such that:

- Any business (e‑commerce, fintech, banking, healthcare, SaaS, logistics, insurance, manufacturing, etc.) can onboard.
- The platform dynamically adapts to each tenant’s:
  - Domains (e.g., product inquiry, claims, bookings, patient support)
  - Intents, entities, workflows
  - Products/services and pricing
  - Validation rules and escalation policies
- Multiple tenants share the same platform with **strict data isolation**.
- No business‑specific logic is hardcoded into core agents or the pipeline. All variability is driven by **tenant configuration + tenant KB**.

---

## 1. CURRENT STATE SUMMARY (FROM ANALYSIS DOC)

Using the attached “AI Chat Agent System Analysis” document:

1. Summarize in ≤1 page:
   - The active runtime path (UI → `SimpleCustomerServicePipeline` → `ClassifierAgent` → domain specialist → `ResearchAgent` → response).
   - How classification, domain routing, and KB search are currently implemented.
   - Where Nigerian‑specific business logic lives (prompts, regexes, validation, KB folder naming, hardcoded URLs).  
   - Existing DB schema and how it is *not yet wired* into the runtime.

2. Identify **concrete coupling points** to the Nigerian telecom/utility vertical:
   - In code (file paths, class names, enums, validation rules).
   - In prompts (domains/intents/entities, examples).
   - In KB structure.

3. Highlight strengths to preserve:
   - Agent abstraction (`BaseBusinessAgent`, `AgentResponse`, `ConversationContext`).
   - Pipeline pattern.
   - Existing UIs and API.
   - Planned DB schema for analytics and persistence.

---

## 2. TARGET ARCHITECTURE: MULTI‑TENANT, BUSINESS‑AGNOSTIC PLATFORM

Design a new architecture that has the following layers and characteristics:

### 2.1 Tenant Management Layer

Define how the platform manages multiple businesses (“tenants”):

- **Tenant lifecycle**: create, update, suspend, delete tenants.
- **Tenant configuration schema** (JSON/YAML or DB model), including:
  - Tenant metadata: `tenant_id`, company name, industry, region(s), languages.
  - Domains and intents (e.g., `PRODUCT_INQUIRY`, `ORDER_SUPPORT`, `CLAIMS`, `APPOINTMENTS`).
  - Entity types (e.g., `order_id`, `policy_number`, `patient_id`, `booking_reference`, `account_number`).
  - Product/service catalog configuration.
  - Validation rules (phone patterns, ID formats, monetary ranges, region‑specific rules).
  - Escalation configuration (keywords, sentiment thresholds, high‑risk flows).
  - Branding & tone (style, greeting/closing patterns, formality).
  - Integration settings (webhook URLs, external API keys, callback endpoints).
- **Tenant isolation strategy**:
  - At the **database level** (schema design, `tenant_id` foreign keys, row‑level filtering).
  - At the **KB / vector store level** (namespaces/collections per tenant).
  - At the **API level** (auth & scoping per tenant, e.g., via `X‑Tenant‑ID`, tokens, or subdomains).

### 2.2 Dynamic Knowledge Base (KB) & RAG

Redesign the KB to be tenant‑aware and business‑agnostic:

- Folder / storage layout such as:
  ```text
  knowledge_base/
    tenants/
      {tenant_id}/
        products/
        procedures/
        policies/
        faqs/
        workflows/
        metadata.json
````

* Document ingestion pipeline that:

  * Accepts common business formats: PDF, DOCX, MD, TXT, HTML, CSV/Excel, basic web pages.
  * Extracts text, headings, tables, and metadata (category, tags, version, permissions).
  * Splits documents into chunks appropriate for semantic search.
  * Indexes each chunk into:

    * A lexical index (e.g., inverted index / BM25) scoped by `tenant_id`.
    * A vector store (RAG) scoped by `tenant_id`.
* KB metadata model:

  * `tenant_id`, `document_id`, `version`, `category`, `tags`, `access_level`, `created_at`, `updated_at`.
* Retrieval strategy:

  * Tenant‑filtered lexical + semantic search with a **merge‑and‑rank** step.
  * Support for `top_k` retrieval and relevance scoring per tenant.

### 2.3 Business‑Agnostic Agent Framework

Redesign the agent layer to be driven by tenant configuration:

* **ClassifierAgent (tenant‑aware)**:

  * No hardcoded domains like `AIRTIME`, `POWER`, `DATA`.
  * Loads domains, intents, and entities dynamically from current tenant config.
  * Builds its classification prompt dynamically:

    * Insert tenant’s domains and intents.
    * Insert entity definitions and patterns.
    * Optionally include few‑shot examples provided by the tenant.
  * Outputs a structured result with:

    * `service_domain`, `intent`, `entities`, `priority`, `sentiment`, `confidence`.

* **Generic specialist agents**, replacing domain‑specific ones:

  * `ProductInquiryAgent` — for any type of product/service catalog.
  * `TransactionGuidanceAgent` — for guiding the user through any purchase/booking/payment flow; uses tenant‑defined validation rules and CTA templates.
  * `TroubleshootingAgent` — for handling issues, failures, and support cases across domains.
  * Optional: `GeneralQAAgent` that uses the tenant KB for any FAQ/policy question.

* Each agent:

  * Receives `tenant_id` + `tenant_config` + `ConversationContext`.
  * Uses tenant KB and configuration to make decisions (no hardcoded telecom logic).
  * Uses tenant branding to generate responses.

### 2.4 Configuration‑Driven Business Rules

Define a configuration format (JSON/YAML or DB) that controls behavior without code changes:

* Product/service catalog:

  * Items, variants, prices, currencies, availability flags, simple business rules.
* Validation rules:

  * Regexes/patterns for IDs and phone numbers.
  * Min/max values for amounts, quantities, dates.
  * Region‑specific rules (e.g., KYC fields, regulatory constraints).
* Escalation rules:

  * Keywords or patterns that trigger escalation.
  * Sentiment thresholds.
  * Domain/intent combinations that should always escalate.
* Navigation and CTA templates:

  * Purchase links, support URLs, escalation messages.
  * Template strings with placeholders (e.g., `{{product_name}}`, `{{order_id}}`).

Show how agents read and apply these configs at runtime.

### 2.5 Multi‑Tenant Data Model

Extend the existing `database/schema.sql` into a multi‑tenant schema:

* Add a `tenants` table with core tenant metadata.
* Add a `tenant_id` column as foreign key to:

  * Customers, enquiries, transactions, and agent_metrics.
* Define:

  * Row‑level filtering strategy and/or database policies.
  * Tenant‑scoped analytics (e.g., success rate, average response time per tenant).
  * How to store and version tenant config (e.g., `tenant_configs` table or JSONB columns).

---

## 3. IMPLEMENTATION ROADMAP

Propose a **phased implementation plan** (~10–12 weeks) with clear milestones.

At minimum, include:

### Phase 1: Tenant Foundations & Context

* Introduce `tenant_id` into:

  * HTTP API (e.g., `X‑Tenant‑ID` header or token claims).
  * UIs (CLI, Gradio, Streamlit) so they can send `tenant_id`.
  * `ConversationContext` and pipeline signatures.
* Implement tenant CRUD and config storage.
* Create a `TenantContext` or middleware that:

  * Resolves the tenant from the request.
  * Loads tenant config.
  * Injects it into pipeline and agents.

### Phase 2: Tenant‑Aware KB

* Restructure the filesystem KB into `knowledge_base/tenants/{tenant_id}/...`.
* Implement document ingestion, parsing, and indexing for at least:

  * Markdown, TXT, PDF, and CSV.
* Add a tenant‑aware KB API and update `ResearchAgent` to be:

  * Tenant‑aware.
  * Rely on lexical search initially, with hooks for vector search later.

### Phase 3: Dynamic Classification

* Refactor `ClassifierAgent` to:

  * Consume tenant config for domains, intents, entities.
  * Build prompts dynamically from config.
  * Remove Nigerian‑specific instructions and regex assumptions.
* Test with at least 3 distinct business types (e.g., e‑commerce, SaaS, healthcare) using synthetic tenant configs.

### Phase 4: Generic Specialist Agents

* Introduce `ProductInquiryAgent`, `TransactionGuidanceAgent`, and `TroubleshootingAgent`.
* Migrate logic from `AirtimeSalesAgent`, `PowerSalesAgent`, `DataSalesAgent` into:

  * Configurable validation rules.
  * Generic parsing and guidance patterns.
* Map the current Nigerian telecom business to a **“legacy tenant”** configuration that preserves existing behavior.

### Phase 5: RAG & Search Upgrade

* Add vector embeddings per tenant using a multi‑tenant vector store (e.g., ChromaDB).
* Implement hybrid retrieval (lexical + vector) in the tenant KB.
* Enhance `ResearchAgent` and specialists to use semantic search in their workflows.

### Phase 6: Hardening & Production Readiness

* Tenant isolation tests (including red‑team style cross‑tenant leakage tests).
* Security & auth for the API and KB endpoints.
* Load testing per tenant and overall platform (e.g., 50+ tenants).
* Monitoring, logging, and metrics per tenant.

---

## 4. DETAILED DESIGN SPECIFICATIONS

For each component, produce:

### 4.1 Tenant Configuration Schema

Provide an example JSON for a tenant (e.g., e‑commerce):

```json
{
  "tenant_id": "acme-corp-001",
  "company_name": "ACME Corporation",
  "industry": "e-commerce",
  "regions": ["NG", "UK"],
  "languages": ["en"],
  "domains": [
    {
      "name": "PRODUCT_INQUIRY",
      "intents": ["browse", "compare", "check_availability"],
      "entities": ["product_name", "category", "price_range"]
    },
    {
      "name": "ORDER_SUPPORT",
      "intents": ["track_order", "cancel_order", "return_request"],
      "entities": ["order_id", "tracking_number"]
    }
  ],
  "entities": {
    "order_id": {
      "type": "string",
      "patterns": ["[A-Z0-9]{8,12}"]
    },
    "phone_number": {
      "type": "string",
      "patterns": ["^\\+?[0-9]{8,15}$"]
    }
  },
  "products": [...],
  "validation_rules": {...},
  "escalation_config": {...},
  "branding": {
    "tone": "friendly-professional",
    "greeting": "Hi there! 👋",
    "closing": "Is there anything else I can help you with today?"
  }
}
```

### 4.2 Dynamic Prompt Generation

Show how classifier prompts are generated from tenant config (e.g., using Jinja2):

```python
def build_classifier_prompt(tenant_config: dict) -> str:
    template = load_template("classifier_prompt.jinja2")
    return template.render(
        company_name=tenant_config["company_name"],
        domains=tenant_config["domains"],
        entities=tenant_config.get("entities", {}),
        example_queries=tenant_config.get("example_queries", [])
    )
```

Explain how the prompt scales from a few domains to 20+ domains.

### 4.3 Tenant‑Aware KB Architecture

Provide an updated KB layout and data model, including:

```text
knowledge_base/
  tenants/
    acme-corp-001/
      faqs/
      products/
      policies/
      workflows/
      metadata.json
    healthplus-002/
      services/
      procedures/
      compliance/
      metadata.json
```

Define how each folder and file is indexed and searched per tenant.

### 4.4 Generic Agent Pseudocode

Provide pseudocode for `ProductInquiryAgent._process_specific`:

```python
def _process_specific(self, message: str, context: ConversationContext) -> Dict[str, Any]:
    tenant_id = context.tenant_id
    tenant_config = self.tenant_config_store.get(tenant_id)

    kb_results = self.kb.search(message, tenant_id, top_k=5)

    entities = self.entity_extractor.extract(
        message,
        tenant_config.get("entities", {})
    )

    matching_products = self.catalog.query(
        tenant_id=tenant_id,
        filters=entities,
        limit=10
    )

    response_text = self.llm.generate(
        system_prompt=self.build_system_prompt(tenant_config),
        user_message=self.build_user_message(message, kb_results, matching_products)
    )

    return {
        "response": response_text,
        "entities": entities,
        "kb_results": kb_results,
        "products": matching_products
    }
```

Do the same for `TransactionGuidanceAgent` and `TroubleshootingAgent`.

---

## 5. MIGRATION STRATEGY FROM CURRENT TELECOM SYSTEM

Describe how to migrate with minimal disruption:

* Create a **“Nigerian Telecom & Utilities” legacy tenant**:

  * Encode current airtime/power/data logic into config (domains, intents, entities, validation rules).
  * Move hardcoded business rules into this tenant config.
  * Move current KB files into `knowledge_base/tenants/legacy-ng-telecom/`.
* Map old agents:

  * `AirtimeSalesAgent` → `ProductInquiryAgent` + `TransactionGuidanceAgent` with telecom‑specific config.
  * `PowerSalesAgent` → same pattern.
  * `DataSalesAgent` → same pattern.
* Ensure:

  * Existing flows continue working using the new architecture but with the legacy tenant configuration.
  * New tenants can be added without touching core code.

---

## 6. ONBOARDING WORKFLOW FOR NEW TENANTS

Design the **end‑to‑end onboarding flow**:

1. **Registration**

   * Capture company name, industry, contact info, region, languages.
   * Generate `tenant_id` and API credentials.

2. **Document Upload**

   * UI/API for uploading product catalogs, FAQs, policies, pricing sheets, SOPs.
   * Auto‑categorization (products vs policies vs FAQs, etc.).

3. **Configuration Wizard**

   * Guided steps to:

     * Define domains and intents.
     * Register entities and patterns (order IDs, policy numbers, etc.).
     * Define validation rules (phone formats, amount limits, etc.).
     * Configure escalation rules and support channels.
     * Configure branding and tone.

4. **KB Indexing**

   * Process documents, build lexical and vector indices.
   * Allow admins to review auto‑detected entities and domain mappings.

5. **Sandbox & Go‑Live**

   * Provide a sandbox chat UI and API environment.
   * Offer test scenarios and metrics.
   * Promotion to production when tenant is satisfied.

Include configuration examples for at least 3 industries (e.g., e‑commerce, healthcare, and B2B SaaS).

---

## 7. TECHNICAL CHALLENGES & SOLUTIONS

Identify and propose designs for:

1. **Varying business complexity**

   * 3 SKUs vs 10,000+ SKUs.
   * Tiered strategies for KB and catalog (simple lists vs paginated DB search).

2. **Domain‑specific validation**

   * Different ID and number formats per region and industry.
   * Pluggable validator framework keyed by tenant + entity type.

3. **Prompt size limits**

   * Cannot inject entire product catalog.
   * Use retrieval → filter → rank → top‑K context for LLM.

4. **Tenant isolation & security**

   * Strict `tenant_id` scoping at DB, KB, vector store, and cache layers.
   * Per‑tenant auth and API keys.

5. **Performance & scalability**

   * Shared LLMs with tenant‑specific context injection.
   * Caching, connection pooling, and batching strategies.
   * Target p95 latency and cost controls.

---

## 8. OUTPUT FORMAT

Produce your work in four sections:

1. **Executive Summary** (~1 page)
2. **Detailed Architecture Document** (5–10 pages)
3. **Implementation Guide** (10–15 pages)
4. **Onboarding Manual** (3–5 pages)

Each section should be detailed and practical, with diagrams (described in text), example schemas, and code snippets where useful.

Be explicit, implementation‑oriented, and assume your output will be handed directly to a senior engineering team.

````

If you want, you can wrap the above in whatever meta‑instructions your orchestration layer uses.

---

## 2. Concrete Plan for Actually Doing This

Now, here’s a practical plan for *your* team to execute this transformation, grounded in the current codebase and analysis. :contentReference[oaicite:1]{index=1}  

I’ll keep the phases sequential but you can parallelize with a larger team.

---

### Phase 0 – Repo Hygiene & Baseline (1–2 weeks)

**Goals:** Clean up and stabilize the current single‑tenant system so it’s ready to be generalized.

Key steps:

1. **Unify agent base classes**
   - Move `ResearchAgent` to the v2 `BaseBusinessAgent` so all agents share `ConversationContext`, metrics, and error handling. :contentReference[oaicite:2]{index=2}  
   - Make sure all agents accept a `tenant_id` parameter in their public interfaces, even if you hardcode a default for now.

2. **Fix known bugs & tighten prompts**
   - Fix the phone number regex/entity extraction issues in `ClassifierAgent._extract_entities`. :contentReference[oaicite:3]{index=3}  
   - Remove obvious Nigerian examples from any “generic” prompts (e.g., ResearchAgent’s old TechCorp prompt).

3. **Clarify active path**
   - Mark legacy SaaS orchestration (`main.BusinessEnquirySystem`) as deprecated.
   - Ensure all UIs (CLI, Gradio, Streamlit, FastAPI) go through `SimpleCustomerServicePipeline` only.

**Deliverables:**
- Cleaned, well‑documented single‑tenant baseline.
- All agents and pipeline signatures ready to accept a `tenant_id` argument.

---

### Phase 1 – Tenant Concept & Tenant Context (1–2 weeks)

**Goals:** Introduce tenants into the core runtime without breaking current behavior.

Steps:

1. **Schema changes**
   - Extend `database/schema.sql` with a `tenants` table and add `tenant_id` foreign key to:
     - `customers`, `enquiries`, `transactions`, `agent_metrics`. :contentReference[oaicite:4]{index=4}  
   - Add a `tenant_configs` (or similar) table storing JSON configs per tenant, or decide on a file‑based config first (JSON/YAML in `config/tenants/`).

2. **Tenant context in APIs & UIs**
   - FastAPI:
     - Add middleware like your sample:

       ```python
       @app.middleware("http")
       async def tenant_context_middleware(request: Request, call_next):
           tenant_id = request.headers.get("X-Tenant-ID") or extract_from_token(request)
           request.state.tenant_id = tenant_id or "legacy-ng-telecom"
           response = await call_next(request)
           return response
       ```
   - CLI/Gradio/Streamlit:
     - Add a simple tenant selector or config flag so you can run the same UI for different tenants.

3. **Pipeline integration**
   - Update `SimpleCustomerServicePipeline.process(...)` to accept `tenant_id`.
   - Populate `ConversationContext.tenant_id` at pipeline start.
   - Pass `tenant_id` into all agent calls (even though they ignore it initially).

**Deliverables:**
- Tenant table & config storage.
- `tenant_id` plumbed end‑to‑end through API/UI → pipeline → agents.
- Default “legacy” tenant working exactly like the current system.

---

### Phase 2 – Tenant‑Aware Knowledge Base (2–3 weeks)

**Goals:** Move from hardcoded `knowledge_base/airtime|power|data` to tenant‑scoped KB.

Steps:

1. **Restructure folders**
   - Create `knowledge_base/tenants/legacy-ng-telecom/{airtime,power,data}` as the first tenant.
   - For new tenants, expect `knowledge_base/tenants/{tenant_id}/{category}/...`.

2. **Refactor ResearchAgent**
   - Add a `tenant_id` argument to `ResearchAgent.search` or `process_message`.
   - On startup, build a per‑tenant index:
     - either by scanning `knowledge_base/tenants/*`.
   - Ensure search always filters by `tenant_id`.

3. **Design ingestion interface**
   - Build a `kb_ingestion` module that:
     - Accepts file uploads or paths per tenant.
     - Extracts text (use `pypdf`, `python-docx`, etc. later; stub now).
     - Writes normalized chunks + metadata to a small DB or JSON index keyed by `tenant_id`.

4. **API endpoints**
   - Add `/kb/{tenant_id}/upload`, `/kb/{tenant_id}/search` endpoints in FastAPI.
   - Update any admin tooling / scripts to work in terms of tenants.

**Deliverables:**
- Tenant‑scoped KB that still uses lexical search.
- Existing telecom KB migrated into a `legacy-ng-telecom` tenant structure.
- Basic ingestion pipeline ready for future RAG.

---

### Phase 3 – Dynamic Classification & Config‑Driven Domains (2–3 weeks)

**Goals:** Remove telecom‑specific hardcoding from `ClassifierAgent` and make it configuration‑driven.

Steps:

1. **Define tenant config schema**
   - Create a JSON schema (or Pydantic model) for tenant configs:
     - `domains`, `intents`, `entities`, `branding`, `validation_rules`, `escalation_config`.
   - Store one config for `legacy-ng-telecom` that mirrors current domains:
     - e.g., `AIRTIME`, `POWER`, `DATA`, `MULTI`, `OTHER`.

2. **Implement a TenantConfigStore**
   - Simple Python service/class that:
     - Loads configs from DB or `config/tenants/{tenant_id}.json`.
     - Caches them in memory.
     - Exposes `get_config(tenant_id)`.

3. **Refactor ClassifierAgent**
   - Replace hardcoded domain list and entity definitions with values from `tenant_config`.
   - Implement a prompt builder as in the meta‑prompt:

     ```python
     def build_classifier_prompt(tenant_config):
         template = load_template("classifier_prompt.jinja2")
         return template.render(
             company_name=tenant_config["company_name"],
             domains=tenant_config["domains"],
             entities=tenant_config.get("entities", {}),
             example_queries=tenant_config.get("example_queries", [])
         )
     ```
   - Ensure fallback rule‑based classification also uses patterns defined in the config (e.g., regexes for entity types).

4. **Test with multiple pseudo‑tenants**
   - Define 2–3 mock tenants:
     - e.g., `acme-ecommerce`, `medicor-health`, `finvest-bank`.
   - Give each very different domains/intents and entity patterns.
   - Run classification regression tests + manual tests.

**Deliverables:**
- `ClassifierAgent` fully tenant‑driven.
- Multiple test tenants demonstrating business‑agnostic classification.

---

### Phase 4 – Generic Specialist Agents (2–3 weeks)

**Goals:** Replace airtime/power/data specialists with generic agents driven by config + tenant KB.

Steps:

1. **Introduce generic agents**
   - Implement:
     - `ProductInquiryAgent`
     - `TransactionGuidanceAgent`
     - `TroubleshootingAgent`
   - All inherit from `BaseBusinessAgent` v2.
   - All accept `tenant_id` and load `tenant_config` and (eventually) KB.

2. **Lift domain logic into config**
   - For the `legacy-ng-telecom` tenant, move:
     - Phone validation rules.
     - Allowed networks, DISCOs, meter rules.
     - Min/max amounts, bulk discount logic.
     - CTA templates and URLs.
   - Your agent code should:
     - Read rules from config.
     - Apply them generically (e.g., “numeric value between min_amount and max_amount”, “string matching regex pattern”).

3. **Pipeline routing**
   - Replace “if domain == AIRTIME → AirtimeSalesAgent” style routing with:
     - A mapping from `service_domain` to generic agents (configured per tenant).
     - Example: `PRODUCT_INQUIRY` → `ProductInquiryAgent`, `PAYMENT_FLOW` → `TransactionGuidanceAgent`.

4. **Ensure backward compatibility**
   - For the legacy tenant, configure mappings so user experience stays almost identical:
     - Same guidance, similar messaging (possibly improved wording but same business rules).

**Deliverables:**
- Domain‑agnostic specialist agents.
- Legacy telecom tenant functioning purely via config + generic agents.

---

### Phase 5 – RAG & Semantic Search (2–3 weeks)

**Goals:** Upgrade KB to support multi‑tenant semantic search with RAG.

Steps:

1. **Select vector store & embedding model**
   - Use something like ChromaDB or another vector DB (you already have dependencies planned).
   - Choose a shared embedding model (e.g., OpenAI or local) for all tenants initially.

2. **Extend ingestion pipeline**
   - On ingestion, compute embeddings for each chunk and store them with:
     - `tenant_id`, `document_id`, `chunk_id`, `embedding`, `metadata`.

3. **Tenant‑aware search**
   - Implement `TenantKnowledgeBase.search(query, tenant_id, top_k)` that:
     - Performs lexical search and vector search filtered by `tenant_id`.
     - Merges results and ranks them.
   - Update `ResearchAgent` and specialist agents to use this new API.

4. **Guardrails & cost controls**
   - Limit `top_k` and context window sizes.
   - Optionally implement caching for frequent queries per tenant.

**Deliverables:**
- Multi‑tenant RAG in place.
- Noticeable quality improvement for complex FAQ/policy questions.

---

### Phase 6 – Tenant Onboarding Flow & Tooling (2–3 weeks, overlaps with others)

**Goals:** Make it simple to add new tenants without code.

Steps:

1. **Admin UI / simple console**
   - Start with a minimal admin UI (could be Streamlit or a separate React app later):
     - Create tenant.
     - Upload docs.
     - Edit config (JSON editor, later a wizard).

2. **Onboarding wizard v1**
   - Basic steps:
     - Enter company metadata.
     - Define 2–5 initial domains/intents.
     - Upload core docs (FAQ, policies, product list).
     - Configure at least one escalation rule and one CTA.

3. **Sandbox mode**
   - Provide a tenant‑scoped sandbox URL / UI.
   - Tag messages as “sandbox” in DB so they don’t pollute production analytics.

4. **Templates**
   - Provide starter configs for:
     - E‑commerce.
     - Healthcare practice.
     - SaaS B2B support.

**Deliverables:**
- First version of a real onboarding workflow.
- Ability to spin up a new test tenant in under an hour with no code changes.

---

### Phase 7 – Security, Isolation & Observability (continuous, but at least 2 weeks dedicated)

**Goals:** Make the platform safe and monitorable for many tenants.

Steps:

1. **Auth & isolation**
   - Add API keys / OAuth / JWT with `tenant_id` in claims.
   - Enforce `tenant_id` scoping at:
     - API layer.
     - DB queries (repositories should always filter by `tenant_id`).
     - KB and vector store queries.

2. **Logging & PII**
   - Mask PII (phone numbers, IDs) in logs.
   - Add structured logging with correlation IDs and `tenant_id`.

3. **Metrics**
   - Add Prometheus (or similar) metrics tagged by `tenant_id`:
     - Request counts, latency, error rates.
     - LLM token usage per tenant.

4. **Load & chaos testing**
   - Simulate 50+ tenants with realistic load.
   - Test behavior under partial KB outages, vector DB slowdowns, etc.

**Deliverables:**
- Clear operational posture.
- Confidence that one noisy or misconfigured tenant can’t break or leak into others.

---

If you plug the improved meta‑prompt into an architect LLM, and follow the engineering plan above, you’ll move from a Nigeria‑specific MVP to a true multi‑tenant, industry‑agnostic agent platform—while keeping your current strengths (agent abstraction, pipeline, UIs) intact.
````
