# Entity — AI Business Intelligence Engine

> A hybrid AI-powered operations assistant that combines SQL analytics, financial simulation, KPI monitoring, PDF knowledge retrieval, and conversational intelligence into a single locally-hosted platform.

Entity is built for executives and operators who need instant, data-grounded answers about their business — not dashboards to stare at. It connects directly to your PostgreSQL database, interprets natural language questions, runs deterministic financial simulations, and delivers answers in a decisive, COO-style voice.

---

## Why Entity Exists

Traditional BI tools require analysts to write queries, build dashboards, and interpret results. Entity eliminates that overhead by providing:

- **Direct answers** from structured company data — no SQL knowledge required
- **Scenario simulation** — "What if we fire X?" computed deterministically, not hallucinated
- **KPI monitoring** with anomaly detection and threshold-based alerts
- **Strategic context** from ingested business documents (PDFs)
- **Revenue causality enforcement** — employees don't own revenue; clients do

The system enforces **financial layer isolation**: employee changes affect costs only, client changes affect revenue. This rule is hardcoded, not prompt-engineered.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                         React Frontend                           │
│  Chat Interface │ KPI Dashboard │ Simulation │ Forecast │ Insights│
└──────────────────────────┬───────────────────────────────────────┘
                           │ HTTP / Streaming
┌──────────────────────────▼───────────────────────────────────────┐
│                      FastAPI Backend                              │
│                                                                   │
│  ┌─────────────────┐                                              │
│  │  Intent Router   │ ← Deterministic keyword routing             │
│  └──┬──┬──┬──┬──┬──┘                                              │
│     │  │  │  │  │                                                  │
│     │  │  │  │  └──► Strategic RAG ──► Knowledge Engine (ChromaDB) │
│     │  │  │  └─────► Insight Engine ──► KPI Thresholds + Rules     │
│     │  │  └────────► KPI Engine ──────► Hardcoded SQL Queries      │
│     │  └───────────► Scenario Engine ─► Financial + Ops + Risk     │
│     └──────────────► Database Engine ─► SQL Agent (sqlcoder:7b)    │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │                  Shared Infrastructure                      │  │
│  │  Humanizer │ Pattern Engine │ Memory │ Query Cache │ Tip    │  │
│  └────────────────────────────────────────────────────────────┘   │
│                           │                                       │
└───────────────────────────┼───────────────────────────────────────┘
                            │
              ┌─────────────▼─────────────┐
              │   Supabase PostgreSQL      │
              │   (Cloud-hosted)           │
              └───────────────────────────┘
```

### Processing Layers

| Layer | Responsibility | LLM Involvement |
|---|---|---|
| **Financial** | Revenue, expenses, margins, runway | None — pure SQL + arithmetic |
| **Operational** | Capacity, workload, project assignments | None — deterministic |
| **Risk** | Delivery risk, churn risk, SLA risk | None — rule-based scoring |
| **Humanization** | Convert structured output to natural language | Yes — Mistral |

---

## Technology Stack

### Backend

| Component | Technology |
|---|---|
| Framework | **FastAPI** with async streaming |
| Database | **Supabase PostgreSQL** (cloud) |
| ORM | **SQLAlchemy** (raw SQL via `text()`) |
| Vector Store | **ChromaDB** (persistent, local) |
| Query Cache | In-memory TTL cache (5 min) |
| LLM Runtime | **Ollama** (local) |

### Frontend

| Component | Technology |
|---|---|
| Framework | **React 19** with Vite |
| Styling | **TailwindCSS 3** |
| Charts | **Recharts** |
| Animations | **Framer Motion** |
| Icons | **Lucide React** |
| Routing | **React Router DOM 7** |
| Markdown | **react-markdown** |

### LLM Models (via Ollama)

| Role | Model | Purpose |
|---|---|---|
| SQL Generation | `sqlcoder:7b` | Natural language → PostgreSQL |
| SQL Retry | `qwen2.5:7b` | Fallback SQL generation via chat API |
| Reasoning & Chat | `mistral:latest` | Response generation, humanization |
| Embeddings | `nomic-embed-text` | Document and conversation embeddings |

---

## Early Experimentation: Local RAG & LLM Benchmarking

Before Entity became what it is now, it started as a **basic local RAG chatbot** — just a simple setup where PDFs were loaded into ChromaDB, and a local LLM (running through Ollama) would answer questions based on whatever it found in those documents. There was no database, no SQL agent, no simulation engine, no KPI tracking — nothing. Just PDFs in, answers out.

The whole point of this early version was to **figure out which LLM to use**. Since the rest of the system didn't exist yet, we could test different models under the exact same conditions and see which one actually worked best.

### Why Start With Just a RAG Setup?

Keeping things simple at the start made it easy to compare models fairly:

- **The LLM was the only thing changing** — no SQL, no routing, no other engines. So if one model gave better answers than another, we knew it was because of the model itself, not something else in the system.
- **Super easy to set up** — just Ollama, ChromaDB, and some test PDFs. No database to configure, no frontend to build.
- **Quick to swap models** — changing the model was literally just changing one string in the code. Same prompts, same documents, same everything else.

### Models We Tested

We picked three models that could all run locally on normal hardware:

| Model | Size | Why We Picked It |
|---|---|---|
| `qwen2.5:7b` | 7B | Good reputation for reasoning, does well on benchmarks for its size |
| `mistral:latest` | 7B | Known for being fast and giving clean, reliable answers |
| `gemma3:4b` | 4B | Smallest of the three — wanted to see if a lighter model could still do the job |

All three run fine on a regular GPU (8–16 GB VRAM) and are easy to pull through Ollama. We picked them because they each take a different approach — Qwen leans into reasoning, Mistral focuses on being fast and reliable, and Gemma tries to do as much as possible with fewer parameters.

### What We Looked For

We asked each model the same set of questions based on the documents we'd loaded in. We weren't running formal benchmarks — just paying attention to what actually mattered for our use case:

| What We Checked | What It Means |
|---|---|
| **Answer Quality** | Did it give correct answers based on the documents? Did it make stuff up? Could it pull info from multiple chunks? |
| **Reasoning** | Could it handle questions that need multiple steps to answer? Could it connect the dots? |
| **Following Instructions** | Did it stick to the rules we set in the system prompt (like "only answer from the given context")? |
| **Speed** | How fast did it start generating? How long for a full answer? |
| **Readability** | Were the answers well-written and easy to read? |

### What We Found

#### `qwen2.5:7b`

- **Good at**: Reasoning and structured answers. It gave the most well-organized responses and handled tricky multi-part questions the best out of all three.
- **Not so good at**: Speed. It was noticeably slower than Mistral. It also had a habit of over-explaining things or adding extra info that wasn't in the source documents.

#### `mistral:latest` (Mistral 7B)

- **Good at**: The best mix of speed and quality. Fast responses, clean and to-the-point answers, rarely made things up. It followed system prompt rules well without needing a lot of prompt tweaking.
- **Not so good at**: On really deep analytical questions, Qwen edged it out slightly in reasoning — but honestly the difference was small and didn't matter much for what we were building.

#### `gemma3:4b`

- **Good at**: It was the fastest since it's the smallest model. Worked fine for simple, direct questions.
- **Not so good at**: Fell apart on harder questions that needed multiple reasoning steps. Answers were often too short or missed important details. It also didn't follow system prompt rules consistently. The quality gap between this and the 7B models was too big to ignore.

### Why We Went With Mistral 7B

We picked **Mistral 7B (`mistral:latest`)** as the main model for Entity. Here's why:

1. **Fast enough for real-time chat** — Users don't want to wait. Mistral gives answers almost as good as Qwen but noticeably faster, which matters a lot when you're streaming responses in a chat interface.
2. **Follows rules well** — Entity needs the LLM to never make up numbers and to stick to specific output formats (especially when turning simulation data into readable text). Mistral was the most reliable at doing this.
3. **Leaves room for other models** — The final system runs multiple models at the same time (SQL generation, embeddings, reasoning). Mistral uses less memory, so there's enough room for `sqlcoder:7b` and `nomic-embed-text` to run alongside it.
4. **Sounds right** — We wanted the chatbot to sound like a sharp, no-nonsense business advisor. Mistral's output naturally fits that tone — concise and professional. Qwen tended to be too wordy, and Gemma was sometimes too brief.

> **Note**: We didn't throw away `qwen2.5:7b` — it got a different job. It's now the **SQL retry model**. When the primary SQL model fails to generate a working query, Qwen steps in as a backup. Its stronger reasoning actually makes it better suited for fixing broken SQL. So both top models ended up in the final system, just doing different things.

### How the Project Grew From Here

Once we settled on Mistral, the project grew from the simple RAG prototype into the full system:

- **Database connected** — Supabase PostgreSQL hooked up through SQLAlchemy for real company data
- **SQL Agent built** — `sqlcoder:7b` turns plain English into SQL queries, with `qwen2.5:7b` as backup
- **Math engines added** — Financial, operational, and risk calculations done with code, not LLM guessing
- **Router added** — Keyword-based routing sends each question to the right engine
- **KPI system built** — 10 hardcoded KPIs with validation and self-correcting logic
- **Frontend built** — React dashboard with live chat, KPI cards, forecasting, and simulation panels

The original RAG engine from this experimentation phase didn't go to waste — it became the **Strategic RAG** route in the final system. The same ChromaDB pipeline still handles PDF-based questions for strategy and advisory topics.

---

## Database Design

### Core Tables

```
employees ──────────────┐
  id, name, role,       │
  department,           │
  monthly_salary,       │     project_assignments
  hire_date, status     ├────── employee_id
                        │       project_id
projects ───────────────┤       hours_allocated
  id, project_name,     │       hours_logged
  client_id (FK),       │
  status, deadline,     │
  estimated_budget,     │
  actual_cost           │
                        │
clients ────────────────┤     revenue
  id, name, industry,   ├────── client_id, project_id
  contract_type,        │       amount, revenue_date
  acquisition_channel   │
                        │     expenses
                        ├────── project_id, category
                        │       amount, expense_date
                        │
tasks ──────────────────┘     client_feedback
  project_id,                   client_id, project_id
  assigned_to (FK),             rating, feedback_text
  status, priority
```

### Supporting Tables

| Table | Purpose |
|---|---|
| `kpi_definitions` | KPI metadata: code, name, unit type, thresholds, time scope |
| `kpi_results` | Computed KPI values with timestamps and status |
| `interaction_logs` | Query logs: intent, route, execution time, patterns |
| `detected_patterns` | Pattern engine findings with severity scores |
| `daily_tips` | One executive tip per day, data-grounded |
| `kpi_corrections` | Self-learning: human-verified KPI corrections |

### Relationships

- **Revenue belongs to Clients and Projects** — never to Employees
- **Employees connect to Projects** through `project_assignments`
- **Expenses map to Projects** by category
- **Client feedback** links to both Clients and Projects

### Performance Indexes

Indexes exist on all foreign keys and frequently queried columns:

```sql
CREATE INDEX idx_revenue_client ON revenue(client_id);
CREATE INDEX idx_revenue_date ON revenue(revenue_date);
CREATE INDEX idx_expenses_date ON expenses(expense_date);
CREATE INDEX idx_pa_employee ON project_assignments(employee_id);
CREATE INDEX idx_tasks_assigned ON tasks(assigned_to);
CREATE INDEX idx_kpi_results_calc ON kpi_results(calculated_at);
```

---

## SQL Agent Design

The SQL Agent translates natural language to PostgreSQL queries using a two-attempt strategy:

### Attempt 1: `sqlcoder:7b` (Completion Model)

```
### Task
Generate a PostgreSQL query to answer: `{question}`

### Database Schema
{DDL_SCHEMA}

### SQL
```

The schema is provided as `CREATE TABLE` DDL statements — the format `sqlcoder` was trained on.

### Attempt 2: `qwen2.5:7b` (Chat Model — Retry)

If Attempt 1 returns empty results, the system retries with a chat-based model that includes:

- Explicit table/column definitions inline
- SQL pattern hints for common queries (workload, overtime, revenue)
- Strict output rules: `SELECT` only, no explanations

### Safety

- **Validation**: Only `SELECT` and `WITH` (CTE) statements are allowed
- **Forbidden keywords**: `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `GRANT`, `REVOKE`
- **Output cleaning**: Markdown blocks, trailing commentary, and explanatory text are stripped
- **Read-only execution**: All queries run through `execute_read_only_query()`

### Workload/Overtime Calculation

```sql
SELECT e.name, e.role,
       SUM(pa.hours_allocated) AS total_allocated,
       SUM(pa.hours_logged) AS total_logged,
       SUM(pa.hours_logged) - SUM(pa.hours_allocated) AS overtime_hours
FROM employees e
JOIN project_assignments pa ON e.id = pa.employee_id
WHERE e.name ILIKE '%target%'
GROUP BY e.name, e.role
```

Overtime is pre-computed in the SQL layer — the LLM never performs arithmetic.

---

## KPI Engine

### 10 Core KPIs

| # | KPI Code | Unit | Time Scope |
|---|---|---|---|
| 1 | `NET_PROFIT_MARGIN` | Percentage | Monthly |
| 2 | `SALARY_TO_REVENUE_RATIO` | Percentage | Monthly |
| 3 | `EMPLOYEE_UTILIZATION` | Percentage | All-time |
| 4 | `AVG_CLIENT_RATING` | Rating (1-5) | All-time |
| 5 | `ON_TIME_DELIVERY` | Percentage | All-time |
| 6 | `REVENUE_CONCENTRATION` | Percentage | All-time |
| 7 | `ESCALATION_FREQUENCY` | Count | All-time |
| 8 | `CHURN_RISK_INDEX` | Score (0-100) | All-time |
| 9 | `REVENUE_PER_EMPLOYEE` | Currency | Monthly |
| 10 | `RUNWAY_MONTHS` | Count | Monthly |

### Design Principles

- **Hardcoded SQL**: Every KPI maps to a deterministic SQL query in `KPI_QUERY_MAP`. No dynamic SQL generation.
- **Validation**: Each computed value is cross-checked by `validate_kpi_value()` against an independent verification query. Mismatches > 1% trigger warnings.
- **Sanity bounds**: `check_sanity_bounds()` catches impossible values (e.g., utilization > 1000%, negative margins below -100%).
- **Safe math**: All division uses `NULLIF(..., 0)` to prevent division-by-zero errors.
- **Status evaluation**: Values are compared against `target_min` / `target_max` thresholds to produce `on_track`, `at_risk`, or `critical` statuses.

### Self-Learning

The KPI engine checks `kpi_corrections` before computing. If a human has submitted a verified correction for a KPI, the corrected value is used instead of the computed one.

---

## Scenario Simulation Engine

### Architecture

```
User Query ("What if we fire Aditya Singh?")
    │
    ▼
┌─ Scenario Detector ─────────────────────┐
│  Regex-based classification:             │
│  fire_employee │ hire_employee │ cancel   │
│  Extract: target name, salary, count     │
└─────────┬───────────────────────────────┘
          │
    ┌─────▼─────┐     ┌──────────────┐     ┌──────────────┐
    │ Financial  │     │ Operational  │     │    Risk      │
    │ Engine     │────►│ Engine       │────►│  Engine      │
    └───────────┘     └──────────────┘     └──────────────┘
          │                  │                    │
          └──────────────────┼────────────────────┘
                             ▼
                     Combined JSON Result
                             │
                             ▼
                   LLM Humanization (Mistral)
                     (read-only — no math)
```

### Supported Scenarios

| Scenario | Revenue Impact | Cost Impact | Operational Impact |
|---|---|---|---|
| Fire Employee | **Locked at zero** | Salary removed | Capacity loss, project risk |
| Hire Employee | **Locked at zero** | Salary added | Capacity gain |
| Cancel Client | Revenue removed | Project costs removed | Project assignments ended |

### Revenue Causality Lock

```python
def validate_revenue_lock(scenario_type, original_revenue, new_revenue):
    """
    IMMUTABLE GUARD: For employee-change scenarios,
    revenue must NOT change. If violated, abort execution.
    """
    if scenario_type in ["fire_employee", "hire_employee"]:
        if abs(new_revenue - original_revenue) > 0.01:
            raise ValueError("Revenue Lock Violation")
```

### Example Output (Fire Employee)

```json
{
  "scenario_type": "fire_employee",
  "target": "Aditya Singh",
  "financial": {
    "salary_removed": 75000,
    "original_margin": 18.5,
    "new_margin": 22.3,
    "revenue_change": 0
  },
  "operational": {
    "capacity_drop_pct": 33,
    "affected_projects": ["Project Alpha", "Project Beta"],
    "overload_risk": 115
  },
  "risk": {
    "delivery_risk": "High",
    "churn_risk": "High",
    "sla_risk": "Moderate"
  }
}
```

The LLM receives this JSON and translates it into an executive briefing. It cannot modify, recalculate, or invent numbers.

---

## RAG Engine (PDF Knowledge Base)

### Pipeline

```
PDF Documents → Text Extraction (pypdf) → Recursive Chunking → Ollama Embeddings → ChromaDB
```

### Configuration

| Parameter | Value |
|---|---|
| Chunk size | 600 characters |
| Chunk overlap | 200 characters |
| Retrieval top-k | 3 chunks (QA), 3 chunks (Advisor) |
| Embedding model | `nomic-embed-text` via Ollama |
| Vector store | ChromaDB (persistent, local) |
| Index persistence | Stored on disk, re-used across restarts |

### Chunking Strategy

Recursive splitting respects document structure:

1. Double newlines (paragraph boundaries)
2. Single newlines
3. Sentence boundaries (periods)
4. Word boundaries (spaces)
5. Character-level fallback

### Retrieval Gating

When database data exists for a query, PDF retrieval is **blocked** to prevent the LLM from mixing operational data with generic theory.

```python
if has_data:
    logger.info("Data detected. Blocking PDF retrieval.")
    rag_context = "PDF Retrieval BLOCKED — database data is sufficient."
```

---

## Intent Routing Layer

### Deterministic Routing

The router uses keyword matching — no LLM classification overhead.

```python
def determine_route(query):
    q = query.lower()

    # SCENARIO: Hypothesis framing required
    if any(t in q for t in ["what if", "simulate", "if we fire", "if we hire"]):
        return "SCENARIO"

    # INSIGHT: Diagnostic queries
    if any(k in q for k in ["risk", "problem", "issue", "why", "diagnose"]):
        return "INSIGHT"

    # KPI: Direct metric queries
    if any(k in q for k in ["kpi", "utilization", "concentration"]):
        return "KPI"

    # STRATEGIC: Theory and frameworks
    if any(k in q for k in ["strategy", "positioning", "framework"]):
        return "STRATEGIC"

    # DATABASE: Default catch-all for data queries
    return "DATABASE"
```

### Route → Handler Mapping

| Route | Handler | Data Source | LLM Usage |
|---|---|---|---|
| `SCENARIO` | `handle_simulation` | Financial + Ops + Risk engines | Humanization only |
| `DATABASE` | `handle_database` | SQL Agent → PostgreSQL | Response generation |
| `KPI` | `handle_kpi` | KPI results table | Response generation |
| `INSIGHT` | `handle_insight` | Insight Engine → KPI thresholds | Response generation |
| `STRATEGIC` | `handle_strategic_rag` | ChromaDB → PDF chunks | Response generation |

---

## Performance Optimization

### Caching

| Cache | TTL | Scope |
|---|---|---|
| Query Cache | 5 minutes | Baseline metrics, frequent SQL results |
| KPI Results | Persisted | Materialized in `kpi_results` table |
| Vector Index | Persistent | ChromaDB stored on disk |

### Async & Streaming

- All LLM calls use `ollama.AsyncClient` with async generators
- Responses stream token-by-token to the frontend via Server-Sent Events
- Database queries run synchronously (SQLAlchemy) but are wrapped in async handlers

### LLM Token Limits

| Context | `num_predict` | `temperature` |
|---|---|---|
| SQL Generation | 500 | 0.1 |
| Core Logic | 1024 | 0.1 |
| Humanization | 1024 | 0.5 |
| Chat Streaming | 1024 | 0.3 |

### Performance Targets

| Operation | Target |
|---|---|
| Intent routing | < 5ms |
| SQL generation + execution | < 3s |
| KPI fetch | < 500ms |
| Full response (streaming start) | < 4s |
| Slow query threshold | > 10s (logged as warning) |

---

## Self-Learning System

### Interaction Logging

Every query is logged to `interaction_logs`:

```sql
INSERT INTO interaction_logs
  (user_query, detected_intent, route_taken, execution_time_ms,
   patterns_detected, error_message)
VALUES (:query, :intent, :route, :exec_time, :patterns, :error)
```

### Pattern Recognition Engine

Five deterministic pattern detectors run against live data:

| Pattern | Trigger | Severity |
|---|---|---|
| **Escalation Risk** | Budget overrun > 15% + delayed status | High |
| **Revenue Concentration** | One vertical > 60% of total revenue | High |
| **Overload Risk** | `hours_logged > hours_allocated * 1.15` | Medium |
| **Churn Risk** | Client rating ≤ 2 | Critical |
| **Governance Breakdown** | Projects past deadline, not completed | Medium |

Detected patterns are stored in `detected_patterns` and surfaced during diagnostic queries.

### Conversation Memory

Past exchanges are embedded and stored in ChromaDB. Relevant history is retrieved via semantic similarity and injected into the system prompt as context.

### Limitations

- **No model fine-tuning** — learning is structural (corrections table, pattern logs), not parametric
- **Pattern rules are static** — thresholds are hardcoded, not learned
- **Memory retrieval is approximate** — semantic similarity, not exact recall

---

## Frontend Features

### Chat Interface

- Real-time streaming responses with token-by-token rendering
- Markdown rendering for formatted responses
- Dark/light theme with persistent preference
- Cursor particle effects for visual polish

### Executive Dashboard

| Component | Data Source | Visualization |
|---|---|---|
| **KPI Cards** | `/kpis` | Animated count-up, status badges, trend indicators |
| **Executive Summary** | `/summary` | 4-point narrative (Financial, Ops, Client, Action) |
| **Forecast Panel** | `/forecast` | Line chart (Revenue, Expenses, Net Margin) + Runway |
| **Insight Panel** | `/insights` | Severity-ranked issue cards with root causes |
| **Simulation Panel** | `/simulate` | Interactive parameter sliders + result comparison |
| **Risk Radar** | `/risk` | Weighted risk scores (Financial, Ops, Client) |

### Tip of the Day

Data-grounded executive tips generated from pattern analysis. One tip per day, deterministic, max 3 sentences.

---

## Security

### Query Safety

- SQL injection prevention via parameterized queries (`text()` bindings)
- Whitelist validation: only `SELECT` / `WITH` statements execute
- Forbidden keyword scanning before execution
- Read-only database connection for all user-facing queries

### Revenue Causality Enforcement

```python
# Hardcoded at the engine level — not a prompt suggestion
if "employee" in scenario and revenue_changed:
    raise ValueError("Revenue Lock Violation")

# Self-check in router catches violations post-generation
if "revenue share" in response or "employee generates" in response:
    return "[Self-Check Intervened: Financial layer isolation violated]"
```

### LLM Output Guardrails

- Numbers from the database are passed through; LLM cannot modify them
- Humanizer includes number verification (original vs. output comparison)
- Temperature is kept low (0.1–0.3) for deterministic outputs
- `repeat_penalty: 1.1` prevents repetitive hallucination loops

---

## Deployment

### Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- **Ollama** running locally on port `11434`
- **Supabase** project with PostgreSQL database

### Required Ollama Models

```bash
ollama pull mistral:latest
ollama pull qwen2.5:7b
ollama pull sqlcoder:7b
ollama pull nomic-embed-text
```

### Environment Setup

Create `.env` in the project root:

```env
SUPABASE_USER=postgres.your_project_ref
SUPABASE_PASSWORD=your_password_here
SUPABASE_HOST=aws-0-region.pooler.supabase.com
SUPABASE_PORT=6543
SUPABASE_DB_NAME=postgres
```

### Backend

```bash
cd app
pip install -r requirements.txt
python main.py
# Server starts on http://127.0.0.1:8001
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Dev server starts on http://localhost:5173
```

### Production Build

```bash
cd frontend
npm run build
# Output in frontend/dist/
```

---

## Project Structure

```
├── app/
│   ├── main.py                 # FastAPI server, CORS, startup
│   ├── router.py               # Intent routing + all handlers
│   ├── sql_agent.py            # SQL generation (sqlcoder + retry)
│   ├── database.py             # SQLAlchemy engine + query execution
│   ├── kpi_engine.py           # 10 hardcoded KPIs + validation
│   ├── simulation_engine.py    # Scenario orchestrator
│   ├── financial_engine.py     # Deterministic financial math
│   ├── operational_engine.py   # Capacity + workload impact
│   ├── risk_engine.py          # Risk scoring (financial, ops, client)
│   ├── knowledge_engine.py     # ChromaDB + PDF ingestion + RAG
│   ├── memory_engine.py        # Conversation memory (ChromaDB)
│   ├── pattern_engine.py       # 5 pattern detectors
│   ├── insight_engine.py       # KPI threshold analysis
│   ├── insight_layer.py        # Data analysis utilities
│   ├── forecasting_engine.py   # Linear regression forecasting
│   ├── executive_summary.py    # 4-point executive narrative
│   ├── humanizer.py            # LLM response humanization
│   ├── tip_engine.py           # Daily executive tips
│   ├── query_cache.py          # In-memory TTL cache
│   ├── fast_sql.py             # Fast-path simple queries
│   ├── complexity_classifier.py# Query complexity routing
│   ├── context_detector.py     # Company context detection
│   ├── intent_classifier.py    # Intent classification
│   ├── api_routes.py           # Dashboard API endpoints
│   └── migrations/             # SQL migration scripts
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx             # Main app + routing + theme
│   │   ├── pages/
│   │   │   └── KPIDashboard.jsx# Executive dashboard page
│   │   ├── components/
│   │   │   ├── ChatView.jsx    # Chat interface
│   │   │   ├── Sidebar.jsx     # Navigation + history
│   │   │   ├── MessageBubble.jsx
│   │   │   ├── KpiCard.jsx     # Animated KPI cards
│   │   │   ├── ExecutiveSummaryCard.jsx
│   │   │   ├── ForecastPanel.jsx
│   │   │   ├── InsightPanel.jsx
│   │   │   ├── SimulationPanel.jsx
│   │   │   ├── RiskRadar.jsx
│   │   │   └── ...
│   │   └── context/
│   │       └── ThemeContext.jsx
│   └── package.json
│
├── data/                       # PDF documents for RAG
├── .env                        # Database credentials
└── README.md
```

---

## Future Improvements

| Category | Enhancement |
|---|---|
| **Forecasting** | Replace linear regression with ARIMA/Prophet for seasonal awareness |
| **Anomaly Detection** | Automated statistical anomaly detection on KPI time-series |
| **Predictive Risk** | ML-based churn prediction using historical client behavior |
| **Recommendations** | Automated strategic recommendations based on pattern combinations |
| **Role-Based Access** | Different dashboard views for CEO, CFO, COO, Department Heads |
| **Multi-Tenant** | SaaS deployment with per-organization data isolation |
| **Fine-Tuning** | Domain-specific fine-tuning of SQL and reasoning models |
| **Real-Time** | WebSocket-based live KPI updates and alert notifications |
| **Audit Trail** | Complete decision audit log for compliance and governance |

---

## License

This project is proprietary. All rights reserved.

---

<p align="center">
  <strong>Entity</strong> — Intelligence that operates.
</p>
