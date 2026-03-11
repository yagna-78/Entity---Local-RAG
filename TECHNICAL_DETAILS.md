# Entity — Technical Deep Dive

This doc covers every internal detail of how Entity works under the hood — database connections, vector storage, embeddings, token limits, caching, scoring formulas, SQL generation, and everything in between. If it's a number, config value, or design choice baked into the code, it's here.

---

## Table of Contents

- [Database Layer](#database-layer)
- [Vector Database (ChromaDB)](#vector-database-chromadb)
- [Embeddings](#embeddings)
- [Document Chunking](#document-chunking)
- [SQL Agent](#sql-agent)
- [LLM Configuration & Token Limits](#llm-configuration--token-limits)
- [Query Cache](#query-cache)
- [KPI Engine](#kpi-engine)
- [Simulation Engine](#simulation-engine)
- [Financial Engine](#financial-engine)
- [Risk Engine](#risk-engine)
- [Pattern Engine](#pattern-engine)
- [Forecasting Engine](#forecasting-engine)
- [Memory Engine](#memory-engine)
- [Humanizer](#humanizer)
- [Intent Router](#intent-router)
- [API Endpoints](#api-endpoints)
- [Interaction Logging](#interaction-logging)

---

## Database Layer

**File**: `app/database.py`

### Connection

| Setting | Value |
|---|---|
| Database | PostgreSQL (Supabase cloud-hosted) |
| ORM | SQLAlchemy |
| Connection string format | `postgresql://user:password@host:port/dbname` |
| Default port | `5432` (overridable via `SUPABASE_PORT` env var) |
| Default DB name | `postgres` (overridable via `SUPABASE_DB_NAME`) |
| Connection pooling | SQLAlchemy default pool with `pool_pre_ping=True` |
| Session management | `sessionmaker(autocommit=False, autoflush=False)` |

### Environment Variables

```
SUPABASE_USER       — Database username (e.g., postgres.your_project_ref)
SUPABASE_PASSWORD   — Database password
SUPABASE_HOST       — Host (e.g., aws-0-region.pooler.supabase.com)
SUPABASE_PORT       — Port (default: 5432)
SUPABASE_DB_NAME    — Database name (default: postgres)
```

If any of `SUPABASE_USER`, `SUPABASE_PASSWORD`, or `SUPABASE_HOST` is missing, the database engine is set to `None` and all DB features are disabled.

### Query Execution

All user-facing queries run through `execute_read_only_query()`:

- Only allows queries starting with `SELECT` or `WITH` (case-insensitive after stripping)
- Blocked keywords: `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `GRANT`, `REVOKE` (validated in the SQL agent layer)
- Results are returned as a list of dictionaries (`dict(zip(keys, row))`)
- Uses `text()` from SQLAlchemy for parameterized execution

---

## Vector Database (ChromaDB)

**File**: `app/knowledge_engine.py`

### Setup

| Setting | Value |
|---|---|
| Client type | `chromadb.PersistentClient` (data saved to disk) |
| Storage directory | `../db/` relative to `app/` |
| Collection name | `entity_knowledge_collection` |
| Persistence | Automatic — survives server restarts |
| Ingestion batch size | 64 documents per batch |

### How It Works

1. On startup, `initialize_resources()` creates/opens the persistent ChromaDB client.
2. If the collection is empty (count = 0), it triggers `ingest_data()` automatically.
3. Documents are stored with metadata containing the source filename.
4. Each chunk gets a unique ID in the format `{filename}_{chunk_index}`.
5. Chunks shorter than 20 characters are discarded as noise.

### Supported File Types

- `.txt` — read directly with UTF-8 encoding
- `.pdf` — extracted page by page using `pypdf.PdfReader`

### Retrieval

| Parameter | Value |
|---|---|
| Default top-k for QA queries | 3 (`RETRIEVAL_K_QA`) |
| Default top-k for advisory queries | 3 (`RETRIEVAL_K_ADVISOR`) |
| Query method | `collection.query(query_texts=[query], n_results=k)` |
| Output format | Chunks joined with `\n\n---\n\n` separator |

Sources are extracted from chunk metadata and returned as a deduplicated list.

### Force Re-ingestion

Calling `ingest_data(force=True)` clears all existing documents from the collection and re-ingests everything from the `data/` directory.

---

## Embeddings

**File**: `app/knowledge_engine.py` (also duplicated in `app/memory_engine.py`)

### Model

| Setting | Value |
|---|---|
| Primary model | `nomic-embed-text` via Ollama |
| Fallback model | `qwen2.5:7b` (if nomic-embed-text fails) |
| Last-resort fallback | Zero vector of 1024 dimensions (`[0.0] * 1024`) |
| API | `ollama.embeddings(model=..., prompt=text)` |

### How Embedding Works

ChromaDB normally handles embeddings internally, but Entity overrides this with a custom `LocalEmbeddingFunction` class:

```python
class LocalEmbeddingFunction(chromadb.EmbeddingFunction):
    def __call__(self, input: List[str]) -> List[List[float]]:
        # Loops through each text, calls Ollama for embedding
        # Falls back to qwen2.5:7b, then to zero vector
```

This function is passed to `get_or_create_collection()` so ChromaDB calls it whenever documents are added or queries are run.

### Embedding Flow

```
Text Input → Ollama API (nomic-embed-text) → Vector (float array)
                    ↓ (if fails)
              Ollama API (qwen2.5:7b) → Vector
                    ↓ (if fails)
              Zero vector [0.0] * 1024
```

Embeddings are generated one at a time (not batched at the API level) because Ollama's embedding endpoint takes a single prompt.

---

## Document Chunking

**File**: `app/knowledge_engine.py` → `recursive_chunk_text()`

### Parameters

| Parameter | Value |
|---|---|
| Chunk size | 600 characters (`CHUNK_SIZE_CHARS`) |
| Chunk overlap | 200 characters (`CHUNK_OVERLAP_CHARS`) |
| Minimum chunk length | 20 characters (anything shorter is discarded) |

### Splitting Strategy

The chunker tries to break text at natural boundaries, in this order of priority:

1. **Double newlines** (`\n\n`) — paragraph boundaries
2. **Single newlines** (`\n`) — line breaks
3. **Periods followed by space** (`.`) — sentence boundaries
4. **Spaces** (` `) — word boundaries
5. **Character-level** (`""`) — forced break if nothing else works

### How It Works

1. Start from position 0, look ahead `chunk_size` characters.
2. Search backwards from the end of the window for the highest-priority separator.
3. Break at that separator (text after the separator goes into the next chunk).
4. Move the start position forward by `(break_point - overlap)` to create overlap.
5. If no progress is made (overlap >= chunk size), force advance by `chunk_size / 2`.
6. Repeat until all text is chunked.

### Anti-Infinite-Loop Guard

```python
if next_start <= start:
    next_start = start + chunk_size // 2
start = max(start + 1, next_start)
```

This makes sure the chunker always moves forward, even in edge cases.

---

## SQL Agent

**File**: `app/sql_agent.py`

### Two-Attempt Strategy

| Attempt | Model | API Type | Purpose |
|---|---|---|---|
| 1st | `sqlcoder:7b` | Completion (`ollama.generate`) | Primary SQL generation — trained on text-to-SQL |
| 2nd (retry) | `qwen2.5:7b` | Chat (`ollama.chat`) | Fallback — uses stronger reasoning to fix failures |

### Schema Format

`sqlcoder:7b` receives the schema as `CREATE TABLE` DDL statements (the format it was trained on):

```sql
CREATE TABLE employees (
  id INTEGER PRIMARY KEY,
  name VARCHAR,
  role VARCHAR,
  department VARCHAR,
  monthly_salary NUMERIC,
  hire_date DATE,
  status VARCHAR
);
-- ... (7 tables total)
```

The DDL includes inline comments with example values and valid column values to guide the model.

`qwen2.5:7b` (retry) receives a more descriptive schema with column descriptions and SQL pattern hints for common query types.

### Prompt Template (sqlcoder)

```
### Task
Generate a PostgreSQL query to answer: `{question}`

### Instructions
- Use PostgreSQL syntax. Use ILIKE for case-insensitive matching.
- ...

### Database Schema
{DDL}

### SQL
```

Includes few-shot examples for common patterns (overtime, budget overrun, etc.).

### SQL Output Cleaning (`clean_sql_output`)

The cleaner handles messy LLM output by:

1. Extracting SQL from markdown code blocks (```sql ...```)
2. Stripping trailing English text/commentary
3. Removing line-by-line non-SQL content
4. Joining multi-line queries

### Query Validation (`validate_query`)

Before execution, every generated SQL query is checked:

- Must start with `SELECT` or `WITH`
- Cannot contain: `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `GRANT`, `REVOKE`
- If validation fails, the query is rejected and the retry model kicks in

---

## LLM Configuration & Token Limits

All LLM calls go through `ollama.AsyncClient` connected to `http://127.0.0.1:11434`.

### Token Limits by Context

| Context | Model | `num_predict` | `temperature` | `repeat_penalty` | File |
|---|---|---|---|---|---|
| Core logic (Layer 1) | mistral:latest | 1024 | 0.1 | 1.1 | router.py |
| Standard streaming | mistral:latest | 1024 | 0.3 | 1.1 | router.py |
| Humanization | mistral:latest | 1024 | 0.5 | 1.1 | humanizer.py |
| SQL generation (primary) | sqlcoder:7b | 500 | 0.1 | — | sql_agent.py |
| SQL generation (retry) | qwen2.5:7b | 500 | 0.1 | — | sql_agent.py |
| Pronoun resolution | qwen2.5:7b | 100 | 0.0 | — | router.py |

### Why These Values?

- **`num_predict: 1024`** — big enough for full-length answers; prevents mid-sentence cutoffs that happened at lower values (early versions used 500 and responses got truncated).
- **`temperature: 0.1`** — keeps SQL and data-driven answers deterministic. Higher temps (0.3–0.5) are only used where natural language variation is okay.
- **`repeat_penalty: 1.1`** — prevents the model from falling into repetitive loops where it keeps generating the same phrase.

### SQL Agent Token Config

```python
# sqlcoder:7b (completion API)
options = {"num_predict": 500, "temperature": 0.1}

# qwen2.5:7b retry (chat API)
options = {"num_predict": 500, "temperature": 0.1}
```

500 tokens is enough for SQL queries — they rarely exceed 200 tokens.

---

## Query Cache

**File**: `app/query_cache.py`

### Design

| Setting | Value |
|---|---|
| Type | In-memory Python dictionary |
| Storage format | `{key: (value, expiry_timestamp)}` |
| Default TTL | 300 seconds (5 minutes) |
| Thread safety | Simple dict + timestamp check (no locks) |
| Persistence | None — cleared on server restart |

### API

```python
query_cache.get(key)                      # Returns value or None if expired
query_cache.set(key, value, ttl=300)      # Stores with TTL
query_cache.get_or_compute(key, fn, ttl)  # Returns cached or computes + caches
query_cache.invalidate(key)               # Remove specific key
query_cache.invalidate_all()              # Clear everything
```

### What Gets Cached

Baseline metrics and frequently repeated SQL results used by the KPI and simulation engines. The 5-minute TTL is aligned with the KPI computation cycle.

---

## KPI Engine

**File**: `app/kpi_engine.py`

### 10 Core KPIs

Each KPI maps to a hardcoded SQL query in `KPI_QUERY_MAP`. No dynamic SQL generation.

| # | KPI Code | SQL Logic | Unit |
|---|---|---|---|
| 1 | `NET_PROFIT_MARGIN` | `(revenue - expenses - salaries) / revenue * 100` | Percentage |
| 2 | `SALARY_TO_REVENUE_RATIO` | `total_salaries / total_revenue * 100` | Percentage |
| 3 | `EMPLOYEE_UTILIZATION` | `AVG(hours_logged / hours_allocated) * 100` | Percentage |
| 4 | `AVG_CLIENT_RATING` | `AVG(rating)` from client_feedback | Rating (1-5) |
| 5 | `ON_TIME_DELIVERY` | Count of on-time projects / total projects * 100 | Percentage |
| 6 | `REVENUE_CONCENTRATION` | Max single-industry revenue / total revenue * 100 | Percentage |
| 7 | `ESCALATION_FREQUENCY` | Count of projects with `actual_cost > estimated_budget` AND delayed | Count |
| 8 | `CHURN_RISK_INDEX` | Count of clients with `AVG(rating) <= 2` / total clients * 100 | Score (0-100) |
| 9 | `REVENUE_PER_EMPLOYEE` | Current month revenue / employee count | Currency (INR) |
| 10 | `RUNWAY_MONTHS` | `(revenue - expenses - salaries) * 0.2 * months / burn_rate` | Count |

### Date Handling

The engine auto-detects the data window:

- `dataset_end_date` = max date across revenue and expense tables
- `active_month_start` = first day of the month containing `dataset_end_date`

All date-sensitive KPIs (margins, revenue per employee, runway) use these boundaries so they pick up the latest actual month of data, not today's date.

### Validation Pipeline

1. **Primary computation** — run the KPI SQL query
2. **Verification query** — run an independent SQL that should produce the same result
3. **Mismatch check** — if the difference between computed and verified values exceeds **1%**, log a warning
4. **Sanity bounds** — catch impossible values:
   - Utilization > 1000% → flagged
   - Margin < -100% → flagged
   - Negative revenue per employee → flagged
5. **Self-learning check** — query `kpi_corrections` table for human-verified overrides. If a correction exists, use it instead of the computed value.

### Status Evaluation

Each KPI has `target_min` and `target_max` thresholds stored in `kpi_definitions`:

- Value within range → `on_track`
- Value slightly outside → `at_risk`
- Value far outside → `critical`

### Company Health Score

Computed from KPI statuses using weighted scoring:

- `on_track` = 100 points
- `at_risk` = 50 points
- `critical` = 0 points

Weighted average produces a 0-100 company health score.

---

## Simulation Engine

**File**: `app/simulation_engine.py`

### Scenario Detection

Uses regex-based pattern matching on the user query:

```python
# Fire patterns:
r"(?:fire|remove|terminate|let go|lay off)\s+(.+)"

# Hire patterns:
r"(?:hire|recruit|onboard)\s+(\d+)?\s*(?:new\s+)?(?:employee|people|person)"

# Cancel patterns:
r"(?:cancel|lose|drop|end)\s+(?:contract|client)\s+(.+)"
```

Each pattern extracts the target entity (employee name, client name, hire count).

### Engine Dispatch

```
Detected Scenario
    ├── fire_employee  → financial_engine.fire_employee()
    │                  → operational_engine.fire_impact()
    │                  → risk_engine.risk_assessment()
    │
    ├── hire_employee  → financial_engine.hire_employee()
    │                  → operational_engine.hire_impact()
    │                  → risk_engine.risk_assessment()
    │
    ├── cancel_client  → financial_engine.cancel_client()
    │                  → operational_engine.cancel_impact()
    │                  → risk_engine.risk_assessment()
    │
    └── general_what_if → financial_engine.general_what_if()
                          (revenue/expense percentage changes)
```

All three sub-engines run in sequence. Their outputs are merged into a single JSON object that gets passed to the LLM for humanization.

---

## Financial Engine

**File**: `app/financial_engine.py`

### Core Principle

All math is deterministic Python code. The LLM never touches numbers.

### Revenue Causality Lock

```python
def validate_revenue_lock(scenario_type, original_revenue, new_revenue):
    if scenario_type in ["fire_employee", "hire_employee"]:
        if abs(new_revenue - original_revenue) > 0.01:
            raise ValueError("Revenue Lock Violation")
```

This is a hard stop — if any employee-related scenario changes revenue by more than ₹0.01, the entire simulation aborts.

### Safe Division

```python
def safe_divide(a, b):
    if b == 0 or b is None:
        return None
    return a / b
```

Used everywhere to prevent division-by-zero crashes.

### Key Calculations

**Fire Employee:**

- Salary savings = employee's `monthly_salary`
- New total cost = original costs − salary savings
- New margin = `(revenue − new_costs) / revenue * 100`
- Revenue change = **always 0** (enforced by revenue lock)

**Hire Employee:**

- Salary added = `salary_per_hire * count`
- New total cost = original costs + salary added
- New margin = `(revenue − new_costs) / revenue * 100`
- Revenue change = **always 0**

**Cancel Client:**

- Revenue removed = sum of all revenue records for that client
- Costs removed = actual costs of projects linked to that client
- Net impact = revenue removed − costs removed

### Burn Rate Analysis

```
Monthly Burn = Total Expenses + Total Salaries − Total Revenue
Runway = Estimated Cash / Monthly Burn
Estimated Cash = (Total Revenue − Total Expenses) * 0.2  (20% profit retention)
```

Risk levels:

- Runway < 3 months → `CRITICAL`
- Runway < 6 months → `WARNING`
- Runway ≥ 6 months → `SAFE`

---

## Risk Engine

**File**: `app/risk_engine.py`

### Scenario Risk Assessment

Triggered after every simulation. Uses thresholds on operational output:

**Delivery Risk:**

| Capacity Drop | Risk Level |
|---|---|
| 100% | Severe |
| ≥ 50% | High |
| ≥ 25% | Moderate |
| < 25% | Low |

**Churn Risk (team overload):**

| Utilization | Risk Level |
|---|---|
| > 120% | Critical |
| > 100% | High |
| > 80% | Elevated |
| ≤ 80% | Controlled |

**SLA Risk:**

- High: > 2 affected projects AND ≥ 50% capacity drop
- Moderate: > 0 affected projects AND ≥ 25% capacity drop
- Low: everything else

### Dashboard Risk Profile

Weighted scores for the `/risk` endpoint:

**Financial Risk (0-100):**

- Net margin < 10% → +40 points
- Net margin < 20% → +20 points
- Salary ratio > 70% → +30 points
- Salary ratio > 50% → +15 points
- Runway < 6 months → +30 points
- Runway < 12 months → +15 points

**Operational Risk (0-100):**

- On-time delivery < 60% → +50 points
- On-time delivery < 80% → +25 points
- Churn index > 50 → +50 points
- Churn index > 30 → +25 points

**Client Risk (0-100):**

- Revenue concentration > 50% → +60 points
- Revenue concentration > 30% → +30 points

**Overall Score:**

```
overall = (financial * 0.4) + (operational * 0.35) + (client * 0.25)
```

Risk levels:

- ≥ 60 → Critical
- ≥ 40 → High
- ≥ 20 → Moderate
- < 20 → Low

---

## Pattern Engine

**File**: `app/pattern_engine.py`

Five deterministic pattern detectors that run SQL queries against live data:

### 1. Escalation Risk

- **Trigger**: Project `actual_cost > estimated_budget * 1.15` (15% overrun) AND status = 'Delayed'
- **Severity**: High
- **Data pulled**: Project name, client name, budget, actual cost, overrun percentage

### 2. Revenue Concentration

- **Trigger**: Any single industry contributes > 60% of total revenue
- **Severity**: High
- **Data pulled**: Industry name, revenue amount, percentage of total

### 3. Overload Risk

- **Trigger**: Employee `hours_logged > hours_allocated * 1.15` (15% over allocated)
- **Severity**: Medium
- **Data pulled**: Employee name, allocated hours, logged hours, overtime percentage

### 4. Churn Risk

- **Trigger**: Client average rating ≤ 2.0
- **Severity**: Critical
- **Data pulled**: Client name, average rating, number of feedback entries

### 5. Governance Breakdown

- **Trigger**: Project past deadline AND status ≠ 'Completed'
- **Severity**: Medium
- **Data pulled**: Project name, client name, deadline date, current status

### Logging

All detected patterns are inserted into the `detected_patterns` table with:

- Pattern name
- Severity
- Trigger signals (JSON)
- Detection timestamp

---

## Forecasting Engine

**File**: `app/forecasting_engine.py`

### Method

Linear regression using `numpy.polyfit(x, y, deg=1)`.

### Data

- Pulls last 12 months of revenue and expense history
- X axis = month index (0, 1, 2, ...)
- Y axis = monthly total amount

### Projections

Generates 3-month forward projections:

```
projected_revenue[month_i] = (slope_rev * (last_idx + i)) + intercept_rev
projected_expense[month_i] = (slope_exp * (last_idx + i)) + intercept_exp

total_cost = projected_expense + current_salary_load
margin = ((revenue - total_cost) / revenue) * 100
```

Current salary load (sum of all employee `monthly_salary`) is assumed constant across projections.

### Runway Calculation

```
estimated_cash = (total_all_time_revenue - total_all_time_expenses) * 0.2
monthly_burn = avg_projected_costs - avg_projected_revenue
runway_months = estimated_cash / monthly_burn
```

The 0.2 multiplier estimates that 20% of historical profit has been retained as cash.

---

## Memory Engine

**File**: `app/memory_engine.py`

### Design

Conversation memory is stored in a **separate ChromaDB collection** from the knowledge base:

| Setting | Value |
|---|---|
| Collection name | `entity_conversation_memory` |
| Storage | Same `../db/` directory as knowledge collection |
| Embedding model | Same as knowledge engine (nomic-embed-text) |

### Storage Format

Each conversation turn is stored as:

```
"User: {query}\nAssistant: {response}"
```

Metadata includes:

- `timestamp`: ISO format datetime
- `type`: always `"conversation"`
- Any additional metadata passed by the caller (e.g., intent)

Document ID format: `mem_{unix_timestamp}`

### Retrieval

```python
retrieve_relevant_history(query, n_results=3)
```

Uses semantic similarity search — the current query is embedded and matched against past conversation embeddings. Returns top 3 most relevant past exchanges, formatted as:

```
### Relevant Past Conversations:
- User: ... | Assistant: ...
- User: ... | Assistant: ...
```

This is injected into the system prompt as context.

---

## Humanizer

**File**: `app/humanizer.py`

### Purpose

Takes structured data (JSON, bullet points) from the core logic layer and rewrites it as natural, executive-style text.

### LLM Config

| Setting | Value |
|---|---|
| Model | mistral:latest |
| `num_predict` | 1024 |
| `temperature` | 0.5 |
| `repeat_penalty` | 1.1 |
| Streaming | Yes (async generator) |

### Prompt Rules

The humanizer prompt enforces:

1. No robotic headers (## Analysis, ### Conclusion)
2. No bullet point lists unless necessary for data
3. **Numbers must not change** — if input says 50%, output must say 50%
4. No new assumptions
5. No generic openers ("Based on the data provided...")
6. Tone: direct, authoritative, "COO-style"

### Number Verification

`verify_numbers()` is a safety check that extracts numbers from both the original structured data and the humanized output via regex, then confirms all significant figures are preserved. Currently uses a simplified implementation (placeholder for future strict validation).

### Fallback

If humanization fails (LLM error), the raw structured data is returned as-is.

---

## Intent Router

**File**: `app/router.py`

### Routing Method

Pure keyword matching — no LLM classification involved. Routes are determined in < 5ms.

### Route Priority (checked in order)

| Route | Trigger Keywords |
|---|---|
| `SCENARIO` | "what if", "simulate", "if we fire", "if we hire", "can we afford", "burn rate", "runway", "increase by", "decrease by", etc. (30+ triggers) |
| `INSIGHT` | "risk", "problem", "issue", "why", "diagnose" |
| `KPI` | "kpi", "utilization", "concentration" |
| `STRATEGIC` | "what should we do", "how to handle", "best practice", "advice", "strategy", "framework", etc. (25+ triggers) |
| `DATABASE` | Everything else (catch-all default) |

### Pronoun Resolution

When a follow-up query contains pronouns (she, he, they, this person, etc.), the router rewrites the query by resolving references using conversation history:

```
"Which department does she belong to?"
    ↓ (with context: previous question was about Riya Patel)
"Which department does Riya Patel belong to?"
```

Uses `qwen2.5:7b` at `temperature: 0.0` and `num_predict: 100` for deterministic rewriting. Only the last 3 conversation turns are used as context.

### Processing Modes

The router adapts the system prompt tone based on query type:

- **CONVERSATIONAL**: COO-level, natural speech
- **ANALYTICAL**: Data operations lead, strictly factual
- **STRATEGIC**: Chief Operating Officer, execution-focused

---

## API Endpoints

**File**: `app/api_routes.py`

### Dashboard Data

| Endpoint | Method | Returns |
|---|---|---|
| `/revenue` | GET | Current month revenue total + breakdown by client |
| `/team` | GET | Employee list with roles and project assignments |
| `/expenses` | GET | Current month expense total + breakdown by category |
| `/projects` | GET | Active projects and their clients |

### Advanced Features

| Endpoint | Method | Returns |
|---|---|---|
| `/simulate` | POST | Runs in-memory simulation with revenue/salary/client/hire changes |
| `/forecast` | GET | 3-month revenue/expense/margin projection + runway |
| `/risk` | GET | Weighted risk scores (financial, operational, client, overall) |
| `/summary` | GET | 4-point executive narrative (Financial, Ops, Client, Action) |
| `/insights` | GET | Severity-ranked issue cards with root causes and solutions |

### Chat

| Endpoint | Method | Returns |
|---|---|---|
| `/chat` | POST (streaming) | Server-Sent Events stream from the routing controller |

### Simulation Request Schema

```python
class SimulationRequest(BaseModel):
    revenue_pct_change: float = 0.0
    salary_pct_change: float = 0.0
    clients_removed: List[str] = []
    new_employees: int = 0
    salary_per_hire: float = 0.0
    marketing_spend_increase: float = 0.0
```

All parameters are applied together in a single pass — combined changes (e.g., revenue change + new hires) are computed simultaneously.

---

## Interaction Logging

**File**: `app/router.py` → `_log_interaction()`

Every query is logged to the `interaction_logs` table:

```sql
INSERT INTO interaction_logs
  (user_query, detected_intent, route_taken, execution_time_ms,
   patterns_detected, error_message)
VALUES (:query, :intent, :route, :exec_time, :patterns, :error)
```

### Performance Monitoring

- Queries taking > 10,000ms are logged as `WARNING` with the `⚠️ SLOW QUERY` prefix
- Route determination time is logged separately (target: < 5ms)
- SQL execution time is logged per query
- All timing is in milliseconds

### Memory Storage

After each successful response, the exchange is stored in the memory engine:

```python
if full_response_text and len(full_response_text) > 10:
    memory_engine.store_exchange(query, full_response_text, {"intent": intent})
```

Only responses longer than 10 characters are stored (filters out error messages and empty responses).
