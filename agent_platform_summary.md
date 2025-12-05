# Multi‑Tenant AI Agent Platform – Project Summary

## 1. Executive Summary

This project is transforming an existing, Nigeria‑specific telecom/utility customer service chatbot into a **multi‑tenant, industry‑agnostic AI agent platform**. The new platform will allow any business (e‑commerce, fintech, banking, healthcare, SaaS, logistics, etc.) to onboard and configure their own conversational agent without core code changes.  

The platform solves the problem of **hard‑coded, single‑business AI assistants** by introducing a tenant‑driven architecture where behaviour is determined by configuration, knowledge bases, and vector search rather than domain‑specific code. Each tenant gets isolated data, custom domains/intents/entities, validation rules, escalation policies, and branding, all running on a shared, scalable infrastructure.  

The end result is a configurable, secure, and observable AI assistant platform that supports omnichannel customer support, guided workflows, and knowledge‑driven answers, while preserving the strengths of the current MVP (pipeline abstraction, agent layering, and existing UIs/APIs).

## 2. Architectural Design

### 2.1 High‑Level Components

- **User Interfaces**
  - CLI client for development and debugging.
  - Web UIs (Gradio/Streamlit) for interactive demos and internal tooling.
  - REST API surface (FastAPI) for integration with external channels (web widgets, WhatsApp, contact‑center tools, etc.).

- **Conversation Orchestration**
  - `SimpleCustomerServicePipeline` as the core orchestration layer, coordinating classification, routing, specialist agents, research, and response generation.
  - `ConversationContext` and `AgentResponse` abstractions encapsulate conversation state and agent outputs.
  - `Navigator` and `build_escalation_summary` handle conversation flow and escalation/meta‑summary logic.

- **LLM Layer**
  - Uses OpenAI models (via AutoGen and custom wrappers) for:
    - Intent/domain/entity classification.
    - Natural‑language response generation.
    - KB‑augmented answer synthesis.
  - Prompt templates and builders are parameterised by tenant configuration (domains, entities, branding, examples) rather than hard‑coded per industry.

### 2.2 Tenant Management & Configuration

- **Tenant Model**
  - Each business is represented as a **tenant** with unique `tenant_id`.
  - Tenant lifecycle: create, update, suspend, delete, with associated configuration and KB assets.

- **Tenant Configuration Schema**
  - Defined via JSON/YAML or Pydantic models and loaded through a `TenantConfigStore`.
  - Key sections:
    - Tenant metadata: `tenant_id`, company name, industry, region, supported languages.
    - Domains & intents: e.g., `PRODUCT_INQUIRY`, `ORDER_SUPPORT`, `CLAIMS`, `APPOINTMENTS`, `PAYMENT_FLOW`, `TROUBLESHOOTING`.
    - Entities: e.g., `order_id`, `policy_number`, `account_number`, `patient_id`, `meter_number`, `msisdn`.
    - Validation rules: regex patterns, ranges, required fields, business constraints.
    - Escalation configuration: triggers, sentiment thresholds, keywords, high‑risk flows.
    - Branding & tone: greeting/closing templates, formality level, persona hints.
    - Integrations: webhooks, external API keys, callback endpoints, URLs for CTAs.

- **Tenant Isolation**
  - **Database level:** all persisted entities (customers, enquiries, messages, transactions, KB documents, logs) are scoped by `tenant_id` through foreign keys and enforced filters.
  - **Knowledge base level:** KB content stored in tenant‑scoped namespaces/collections and filtered by `tenant_id` at query time.
  - **API level:** authentication and authorization ensure each token/session is associated with a single tenant; APIs require tenant context (e.g., header, subdomain, or token claim).

### 2.3 Knowledge Base, Search, and RAG

- **Dynamic, Tenant‑Aware KB**
  - Files and documents are ingested per tenant through an ingestion pipeline:
    - Handles PDFs, Word docs, Markdown, and text.
    - Normalises, chunks, and writes content with metadata including `tenant_id`, `document_id`, and semantic tags (domain, product, etc.).
  - Storage initially uses filesystem + relational DB indices; designed to evolve into a full vector DB–backed RAG setup.

- **Semantic Search & RAG (Planned/Phased)**
  - Vector database (e.g., ChromaDB or similar) used for multi‑tenant embeddings.
  - Embeddings computed for each chunk and stored with `tenant_id`, `embedding`, and metadata.
  - `TenantKnowledgeBase.search(query, tenant_id, top_k)` performs vector + lexical search filtered by `tenant_id`, then ranks and returns context to the LLM.
  - Guardrails: control `top_k`, context window size, and caching to manage cost and latency.

### 2.4 Agent Layer

- **ClassifierAgent (Tenant‑Driven)**
  - Replaces hard‑coded Nigerian telecom/utility classification with config‑driven classification.
  - Builds prompts from tenant configuration (domains, entities, example queries) using templates (e.g., Jinja2).
  - Optionally combines LLM‑based classification with rule‑based fallbacks derived from tenant validation patterns.

- **Specialist Business Agents**
  - Legacy domain specialists (`AirtimeSalesAgent`, `PowerSalesAgent`, `DataSalesAgent`) are being phased into **generic, reusable agents**:
    - `ProductInquiryAgent` – product and service discovery, FAQs, eligibility questions.
    - `TransactionGuidanceAgent` – step‑by‑step guidance and validation for payments, top‑ups, orders, renewals.
    - `TroubleshootingAgent` – structured diagnostics and resolution flows based on KB and rules.
  - All inherit from `BaseBusinessAgent` v2, accept `tenant_id`, and load `tenant_config` plus tenant‑specific KB content.
  - Business logic (allowed values, ranges, validation, CTA templates, escalation thresholds) is defined in config instead of being hard‑coded in the agent classes.

- **ResearchAgent**
  - Orchestrates tenant‑scoped KB and RAG queries.
  - Aggregates relevant passages and passes them to the LLM for grounded answer generation.

### 2.5 Data Model and Persistence

- **Core Entities (planned/wired)**
  - Customers, conversations, enquiries, messages, transactions, KB documents, and ingestion jobs.
  - All entities scoped by `tenant_id` to guarantee isolation and enable per‑tenant analytics.

- **Usage & Analytics**
  - Capture per‑tenant metrics such as volume, CSAT proxies (e.g., sentiment, user feedback flags), resolution rates, escalation rates, and LLM token usage.
  - Provide a foundation for dashboards and optimisations (e.g., identify gaps in KB, tune prompts/configs per tenant).

### 2.6 Security, Observability, and Operations

- **Security & Isolation**
  - API keys, OAuth/JWT with `tenant_id` claims; strict enforcement of tenant scoping at API, DB, KB, and vector store layers.
  - PII masking for logs (e.g., phone numbers, IDs).

- **Observability**
  - Structured logging with correlation IDs and `tenant_id`.
  - Metrics (e.g., Prometheus) tracking request counts, latency, errors, and token usage per tenant.
  - Load and chaos testing across many tenants to validate resilience and isolation.

### 2.7 Tenant Onboarding and Tooling

- Admin UI/console (Streamlit or similar) for:
  - Creating and managing tenants.
  - Uploading KB documents.
  - Editing tenant configuration (JSON editor initially; wizards later).
- Onboarding wizard to capture core metadata, domains/intents, initial documents, and at least basic escalation and CTA rules.
- Sandbox mode allowing tenants to test agents in non‑production environments, with sandbox traffic tracked separately.

## 3. Core Capabilities

- **Multi‑Tenant, Config‑Driven Behaviour**
  - Host many businesses on a single platform while keeping data and behaviour isolated by `tenant_id`.
  - Customise domains, intents, entities, validation rules, and escalation policies per tenant without changing core code.

- **Tenant‑Aware Classification & Routing**
  - Classify user messages into tenant‑specific domains/intents using LLM prompts built from tenant config.
  - Route conversations to appropriate specialist agents (`ProductInquiryAgent`, `TransactionGuidanceAgent`, `TroubleshootingAgent`, etc.) based on classification and config mappings.

- **Knowledge‑Driven Responses (RAG‑Ready)**
  - Ingest and index tenant documents (FAQs, policies, product catalogues, playbooks).
  - Perform tenant‑scoped search (lexical now, RAG/vector search planned) and ground LLM responses in retrieved context.

- **Workflow and Transaction Guidance**
  - Guide users through complex workflows such as purchases, payments, orders, claims, and troubleshooting flows.
  - Validate inputs according to tenant‑defined rules and surface clear next steps or corrective instructions.

- **Escalation and Handoff**
  - Detect high‑risk or unresolved cases based on config (keywords, sentiment, intents) and generate escalation summaries.
  - Support handoff to human agents or external systems with structured context.

- **Omnichannel Integration**
  - Expose a FastAPI backend to integrate with web widgets, chat frontends, and potential messaging platforms.
  - Provide CLI and web UI surfaces for testing, demos, and internal operations.

- **Analytics and Observability (Per Tenant)**
  - Track interaction metrics, errors, and token usage by tenant for monitoring and billing scenarios.
  - Enable insights into unresolved queries, KB gaps, and performance trends.

- **Secure, Isolated Operation**
  - Enforce tenant isolation at all layers with proper auth, scoping, and PII handling.
  - Support scalable operation across many tenants with resilience testing and observability.

