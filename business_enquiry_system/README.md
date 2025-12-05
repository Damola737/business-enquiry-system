# 🤖 Multi-Service AI Customer Service System

**Enterprise-grade, multi-agent AI platform for Nigerian Airtime, Power, and Data services**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![AutoGen](https://img.shields.io/badge/AutoGen-0.2.27-purple.svg)](https://microsoft.github.io/autogen/)
[![UI Options](https://img.shields.io/badge/UI-3_Options-green.svg)](#user-interfaces)
[![Status](https://img.shields.io/badge/status-Production_Ready-success.svg)](#verification)

---

## 🌟 What Is This?

An intelligent, production-ready multi-agent AI system that provides **professional customer service** for:

- 📱 **Airtime** - Mobile credit for MTN, Airtel, Glo, 9Mobile
- ⚡ **Power/Electricity** - Prepaid tokens for all Nigerian DISCOs
- 📶 **Data Bundles** - Internet packages across all networks

---

## ✨ Key Benefits

### 🏢 Enterprise-Ready Architecture
| Capability | Benefit |
|------------|---------|
| **Multi-Tenant Support** | Serve multiple businesses from a single deployment |
| **Hot-Reload Skills** | Update agent behavior without restart |
| **Comprehensive Tracing** | Full observability with JSONL trace logs |
| **Evaluation Harness** | Automated testing with routing accuracy, entity extraction, and groundedness metrics |

### 🔒 Production-Grade Security
- **Sandboxed Tool Execution** - Tools run with permission controls and rate limits
- **PII Redaction** - Automatic redaction of sensitive data in logs
- **Budget Controls** - Per-request limits on tool calls and execution time

### 📊 Intelligent Processing
- **Hybrid Retrieval** - Combines keyword (BM25) + semantic search for accurate knowledge lookup
- **Cross-Encoder Reranking** - AI-powered result reranking for relevance
- **Contextual Chunking** - Smart document splitting preserving meaning
- **Multi-Agent Research** - Parallel agent coordination for complex queries

### 📈 Observability & Metrics
- **Real-time Scoreboard** - Track latency, success rates, domain distribution
- **Percentile Metrics** - P50, P95, P99 latency tracking
- **Alert System** - Automatic alerts for error rate spikes
- **Session Analytics** - Per-tenant and per-domain statistics

---

## 🚀 Quick Start (2 Minutes)

### 1. Install Dependencies
```bash
pip install -r requirements_ui.txt
```

### 2. Configure Environment
```bash
# Create .env file with your OpenAI API key
echo "OPENAI_API_KEY=your-key-here" > .env
```

### 3. Choose Your Interface

**Enhanced CLI** (Terminal):
```bash
python ui_enhanced_cli.py
```

**Gradio Web UI** (Browser):
```bash
python ui_web_gradio.py
# Opens at http://localhost:7860
```

**Streamlit Dashboard** (Browser):
```bash
streamlit run ui_web_streamlit.py
# Opens at http://localhost:8501
```

### 4. Try an Example
```
I need 1000 naira MTN airtime for 08012345678
```

**Done! Your AI assistant is running!** 🎉

---

## 🏗️ System Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────────┐
│                     OBSERVABILITY LAYER                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ TraceStore  │  │ Scoreboard  │  │  RunMetadata + Hashing  │  │
│  │ (JSONL logs)│  │ (Metrics)   │  │  (Version Control)      │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                      AGENT LAYER                                 │
│  ┌───────────────┐  ┌────────────────┐  ┌────────────────────┐  │
│  │ Classifier    │  │ Multi-Agent    │  │ Specialist Agents  │  │
│  │ (Domain/      │  │ Coordinator    │  │ (Airtime/Power/    │  │
│  │  Intent/      │  │ (Parallel      │  │  Data)             │  │
│  │  Sentiment)   │  │  Research)     │  │                    │  │
│  └───────────────┘  └────────────────┘  └────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                     RETRIEVAL LAYER                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ Contextual  │  │ Hybrid      │  │ Cross-Encoder          │  │
│  │ Chunker     │  │ Retriever   │  │ Reranker               │  │
│  │             │  │ (BM25+      │  │                        │  │
│  │             │  │  Semantic)  │  │                        │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                      TOOL LAYER                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ ToolSpec    │  │ ToolRunner  │  │ ToolBudget              │  │
│  │ (Schema)    │  │ (Sandbox    │  │ (Rate Limits)           │  │
│  │             │  │  + Retry)   │  │                         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                     SKILLS LAYER                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ SkillLoader │  │ SKILL.md    │  │ forms.json              │  │
│  │ (Hot-Reload)│  │ (Playbooks) │  │ (Slot Definitions)      │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    CONTEXT LAYER                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ CaseState   │  │ Context     │  │ Conversation            │  │
│  │ Store       │  │ PackBuilder │  │ Compactor               │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                      EVAL LAYER                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ EvalCase    │  │ EvalRunner  │  │ MetricScores            │  │
│  │ (Test Data) │  │ (Harness)   │  │ (Routing/Entity/        │  │
│  │             │  │             │  │  Groundedness)          │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Agent Flow

```
Customer Query
    ↓
ClassifierAgent (AI-powered classification)
    ↓
OrchestratorAgent (Route to specialist)
    ↓
Specialist Agents (Domain-specific: Airtime/Power/Data)
    ↓
ResearchAgent (Hybrid knowledge base search)
    ↓
Response (Guidance + Navigation links)
```

---

## 📦 Project Structure

```
business_enquiry_system/
├── agents/                          # AI Agents
│   ├── base_agent_v2.py            # Enhanced base agent
│   ├── classifier_v2.py            # LLM-powered classifier
│   ├── retrieval.py                # Hybrid search + reranking
│   ├── multi_agent.py              # Parallel research coordination
│   ├── navigator.py                # Link navigation helper
│   ├── escalation_formatter.py     # Human handoff
│   ├── research_agent.py           # Knowledge base search
│   └── specialists/                # Domain specialists
│       ├── airtime_sales_agent_v2.py
│       ├── power_sales_agent_v2.py
│       └── data_sales_agent_v2.py
│
├── config/                          # Configuration
│   ├── llm_config.json             # LLM settings
│   ├── service_urls.json           # Service portal URLs
│   └── tenants/                    # Multi-tenant configs
│       ├── legacy-ng-telecom.json
│       ├── acme-ecommerce.json
│       └── medicor-health.json
│
├── context_engine.py               # Case state & conversation management
├── pipeline_models.py              # Typed schemas (Pydantic)
│
├── eval/                            # Evaluation harness
│   ├── models.py                   # EvalCase, EvalResult, MetricScores
│   ├── runner.py                   # EvalRunner with metrics
│   └── cases/smoke.json            # Test cases
│
├── observability/                   # Observability & tracing
│   ├── trace_store.py              # JSONL trace logging
│   ├── dashboard.py                # Scoreboard metrics
│   ├── run_metadata.py             # Versioning & hashing
│   └── redaction.py                # PII redaction
│
├── skills/                          # Skill definitions
│   ├── loader.py                   # Hot-reload skill loading
│   └── definitions/                # Per-tenant skill playbooks
│       └── legacy-ng-telecom/
│           ├── airtime_purchase/
│           ├── data_purchase/
│           └── power_purchase/
│
├── tools/                           # Tool platform
│   ├── specs.py                    # ToolSpec, ToolBudget, ToolRegistry
│   └── runner.py                   # Sandboxed execution with retry
│
├── knowledge_base/                  # FAQs and guides
│   ├── airtime/
│   ├── power/
│   └── data/
│
├── tests/                           # Test suite
│   └── test_integration.py         # Integration tests (8 tests)
│
├── ui_enhanced_cli.py              # ⭐ Enhanced CLI
├── ui_web_gradio.py                # ⭐ Gradio Web UI
├── ui_web_streamlit.py             # ⭐ Streamlit Dashboard
│
└── mvp_pipeline.py                 # Main pipeline
```

---

## 🧪 Running Tests

### Integration Tests
```bash
python tests/test_integration.py
```

This runs 8 comprehensive tests covering:
- ✅ Observability (TraceStore, Scoreboard, RunMetadata)
- ✅ Eval Harness (EvalCase, MetricScores, EvalResult)
- ✅ Context Engine (CaseState, ConversationCompactor, ReflectStep)
- ✅ Tool Platform (ToolSpec, ToolBudget, ToolRunner)
- ✅ Retrieval (Chunking, Hybrid Search, Reranking)
- ✅ Multi-Agent (ResearchAgent, MultiAgentCoordinator)
- ✅ Skills (SkillLoader, Playbooks)
- ✅ Pipeline Models (Classification, Escalation, Retrieval)

### Full Test Suite
```bash
python comprehensive_test.py
```

### Single Query Test
```bash
python test_single_query.py
```

---

## 📊 Metrics & Observability

### Scoreboard Metrics
The system tracks real-time metrics:

| Metric | Description |
|--------|-------------|
| `total_requests` | Total requests processed |
| `success_rate` | Percentage of successful responses |
| `avg_latency_ms` | Average response time |
| `p50_latency_ms` | 50th percentile latency |
| `p95_latency_ms` | 95th percentile latency |
| `p99_latency_ms` | 99th percentile latency |
| `domain_distribution` | Breakdown by service domain |
| `error_rate` | Percentage of failed requests |

### Tracing
All requests are traced to JSONL files with:
- Run metadata (tenant, model, config versions)
- Span tracking (start/end times, metadata)
- Event logging (tool calls, decisions)
- Error tracking

### Alerts
Automatic alerts trigger when:
- Error rate exceeds 5%
- P95 latency exceeds 3000ms
- Unusual traffic patterns detected

---

## 🎨 User Interfaces

### 1️⃣ Enhanced CLI (Terminal)
```bash
python ui_enhanced_cli.py
```
- Beautiful colors and emojis
- Progress bars for confidence
- Commands: `help`, `clear`, `stats`, `quit`
- **Best for**: Developers, quick testing

### 2️⃣ Gradio Web UI (Browser)
```bash
python ui_web_gradio.py
# Opens at http://localhost:7860
```
- Modern gradient design
- Chat interface with avatars
- One-click examples
- **Best for**: Demos, presentations

### 3️⃣ Streamlit Dashboard (Browser)
```bash
streamlit run ui_web_streamlit.py
# Opens at http://localhost:8501
```
- Dashboard layout with sidebar
- Real-time metric cards
- Session statistics
- **Best for**: Production, customer service teams

---

## 🎯 Example Queries

### Airtime
```
"I need 1000 naira MTN airtime for 08012345678"
"Send me 2000 naira Airtel airtime"
"Buy 500 naira Glo credit"
```

### Power/Electricity
```
"Buy me 5000 naira EKEDC token for meter 12345678901"
"I need 10000 naira IKEDC electricity"
"How do I purchase prepaid token?"
```

### Data Bundles
```
"I want 10GB MTN data"
"How much is 5GB Airtel bundle?"
"Recommend data plan for heavy usage"
```

---

## 🛠️ Requirements

### Core
- Python 3.9+ (3.11+ recommended)
- OpenAI API key
- Internet connection

### Dependencies
```bash
pip install -r requirements_ui.txt
```

Key packages:
- `pyautogen` - Multi-agent framework
- `pydantic` - Data validation
- `python-dotenv` - Environment config
- `openai` - LLM API
- `gradio` - Web UI framework
- `streamlit` - Dashboard framework

---

## 🔧 Configuration

### Environment Variables
```bash
# .env file
OPENAI_API_KEY=your-api-key-here
```

### Tenant Configuration
Edit files in `config/tenants/` to customize per-tenant behavior:
- `legacy-ng-telecom.json` - Telecom tenant config
- `acme-ecommerce.json` - E-commerce tenant config

### Skills (Playbooks)
Edit files in `skills/definitions/<tenant>/` to customize agent behavior:
- `SKILL.md` - Natural language playbook
- `forms.json` - Slot definitions
- `config.json` - Skill configuration

---

## 🌐 Deployment

### Local Development
```bash
python ui_enhanced_cli.py      # CLI
python ui_web_gradio.py        # Gradio
streamlit run ui_web_streamlit.py  # Streamlit
```

### Public Access (Gradio)
```python
# In ui_web_gradio.py
demo.launch(share=True)  # Creates public link
```

### Cloud Deployment
- **Hugging Face Spaces** (Gradio)
- **Streamlit Cloud** (Streamlit)
- **AWS/Azure/GCP** (All interfaces)
- **Docker** (Containerized deployment)

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [QUICK_START_UI.md](QUICK_START_UI.md) | 2-minute quick start ⭐ |
| [UI_GUIDE.md](UI_GUIDE.md) | Complete UI reference |
| [ENHANCED_SYSTEM_DESIGN.md](ENHANCED_SYSTEM_DESIGN.md) | Full system design |
| [GET_STARTED.md](GET_STARTED.md) | Comprehensive setup guide |
| [VERIFICATION_RESULTS.md](VERIFICATION_RESULTS.md) | Test results |

---

## 🤝 Contributing

**Areas for contribution**:
- Additional service domains
- Multilingual support (Hausa, Yoruba, Igbo)
- Real API integrations
- Enhanced analytics
- Mobile app integration

**How to contribute**:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run `python tests/test_integration.py`
5. Submit a pull request

---

## 📞 Contact

**Project Status**: ✅ Production Ready  
**Version**: 2.0  
**Last Updated**: December 5, 2025

---

## 🌟 Star This Project

If you find this useful, please star the repository!

**Built with ❤️ for Nigerian tech ecosystem** 🇳🇬

---

**Ready to start?** → [QUICK_START_UI.md](QUICK_START_UI.md)

**Want to customize?** → [UI_GUIDE.md](UI_GUIDE.md)

**Need full details?** → [ENHANCED_SYSTEM_DESIGN.md](ENHANCED_SYSTEM_DESIGN.md)