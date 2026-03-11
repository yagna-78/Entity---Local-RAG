import re
import logging
import re
import logging
import ollama

try:
    from database import execute_read_only_query
except ImportError:
    from .database import execute_read_only_query

logger = logging.getLogger(__name__)

# Global Singleton for LLM Client
llm_client = ollama.AsyncClient(host='http://127.0.0.1:11434')

# --- Schema Definition ---
# Hardcoded schema for the LLM to understand the database structure
DB_SCHEMA = """
Tables and Columns:

1. employees
   - id (int, pk)
   - name (text) -- Employee full name, e.g. 'Aarav Shah', 'Riya Patel'
   - role (text) -- Job title, e.g. 'Backend Developer', 'Frontend Developer', 'Fullstack Developer', 'UI/UX Designer', 'Project Manager', 'Sales Executive', 'Marketing Manager', 'Video Editor', '3D Artist', 'DevOps Engineer', 'Content Strategist', 'QA Engineer', 'Business Analyst', 'Support Engineer'
   - department (text) -- Values: 'Engineering', 'Design', 'Sales', 'Marketing', 'Operations', 'Production', 'Support'
   - monthly_salary (numeric) -- In INR, e.g. 45000 to 75000
   - hire_date (date)
   - status (text) -- 'active' or 'inactive'

2. clients
   - id (int, pk)
   - name (text) -- Company name, e.g. 'Apollo Care', 'TechNova', 'Dream Homes'
   - industry (text) -- Values: 'Healthcare', 'Real Estate', 'Technology', 'Media', 'FinTech', 'HealthTech'
   - acquisition_channel (text) -- How the client was acquired. Values: 'Referral', 'LinkedIn', 'Cold Email', 'Cold Call', 'Inbound', 'Instagram', 'Outbound'
   - contract_type (text) -- Values: 'recurring', 'project', 'Retainer', 'Fixed-Price'
   - start_date (date)

3. projects
   - id (int, pk)
   - project_name (text) -- e.g. 'Apollo CRM Phase 2', 'TechNova SaaS Core'
   - client_id (int, fk -> clients.id)
   - status (text) -- Values: 'ongoing', 'delayed', 'completed', 'active'
   - estimated_budget (numeric) -- In INR
   - actual_cost (numeric) -- In INR. If actual_cost > estimated_budget, project is over budget
   - start_date (date)
   - deadline (date)

4. project_assignments
   - id (int, pk)
   - project_id (int, fk -> projects.id)
   - employee_id (int, fk -> employees.id)
   - hours_allocated (float) -- Total hours assigned to this employee for this project
   - hours_logged (float) -- Actual hours worked. If hours_logged > hours_allocated, employee is in overtime

5. revenue
   - id (int, pk)
   - client_id (int, fk -> clients.id) -- Revenue belongs to clients, NOT employees
   - project_id (int, fk -> projects.id)
   - amount (numeric) -- In INR
   - revenue_date (date)

6. expenses
   - id (int, pk)
   - project_id (int, fk -> projects.id) -- Can be NULL for company-wide expenses
   - amount (numeric) -- In INR
   - expense_date (date)
   - category (text) -- Values: 'salary', 'software', 'marketing', 'Rent', 'Contractor Fees', 'Cloud Infrastructure', 'SaaS & Tooling', 'Marketing'

7. tasks
   - id (int, pk)
   - project_id (int, fk -> projects.id)
   - assigned_to (int, fk -> employees.id) -- This is an INTEGER employee ID, not a name
   - status (text) -- Values: 'pending', 'completed', 'delayed'
   - priority (text) -- Values: 'high', 'medium', 'low'
   - due_date (date)
   - completed_date (date) -- NULL if not yet completed

8. meetings
   - id (int, pk)
   - project_id (int, fk -> projects.id)
   - meeting_type (text) -- Values: 'internal', 'client', 'Internal', 'Client'
   - meeting_date (timestamp)
   - duration_minutes (int) -- Ranges from 30 to 140 minutes

9. client_feedback
   - id (int, pk)
   - client_id (int, fk -> clients.id)
   - project_id (int, fk -> projects.id)
   - rating (int) -- 1 to 5 scale (1=worst, 5=best)
   - feedback_text (text) -- Client's written feedback
   - feedback_date (date)

Relationships:
- Projects belong to Clients.
- Employees are assigned to Projects via project_assignments.
- Revenue maps to Clients and Projects (NOT to employees).
- Expenses map to Projects (or NULL for company-wide).
- Tasks are assigned to Employees via assigned_to (FK -> employees.id).
"""

# --- Schema as CREATE TABLE DDL (required format for sqlcoder:7b) ---
DB_SCHEMA_DDL = """
CREATE TABLE employees (
  id INTEGER PRIMARY KEY,
  name VARCHAR,              -- Employee full name, e.g. 'Aarav Shah', 'Riya Patel', 'Kunal Mehta'
  role VARCHAR,              -- Job title. Values: 'Backend Developer', 'Frontend Developer', 'Fullstack Developer', 'UI/UX Designer', 'Project Manager', 'Sales Executive', 'Marketing Manager', 'Video Editor', '3D Artist', 'DevOps Engineer', 'Content Strategist', 'QA Engineer', 'Business Analyst', 'Support Engineer'
  department VARCHAR,        -- Values: 'Engineering', 'Design', 'Sales', 'Marketing', 'Operations', 'Production', 'Support'
  monthly_salary NUMERIC,    -- In INR, ranges from 45000 to 75000
  hire_date DATE,            -- When the employee joined
  status VARCHAR             -- 'active' or 'inactive'
);

CREATE TABLE clients (
  id INTEGER PRIMARY KEY,
  name VARCHAR,              -- Company name, e.g. 'Apollo Care', 'TechNova', 'Dream Homes', 'StudioTalk'
  industry VARCHAR,          -- Values: 'Healthcare', 'Real Estate', 'Technology', 'Media', 'FinTech', 'HealthTech'
  acquisition_channel VARCHAR, -- How the client was acquired. Values: 'Referral', 'LinkedIn', 'Cold Email', 'Cold Call', 'Inbound', 'Instagram', 'Outbound'
  contract_type VARCHAR,     -- Values: 'recurring', 'project', 'Retainer', 'Fixed-Price'
  start_date DATE            -- When the client relationship started
);

CREATE TABLE projects (
  id INTEGER PRIMARY KEY,
  client_id INTEGER REFERENCES clients(id),
  project_name VARCHAR,      -- e.g. 'Apollo CRM Phase 2', 'TechNova SaaS Core', 'Dream Homes 3D'
  status VARCHAR,            -- Values: 'ongoing', 'delayed', 'completed', 'active'
  start_date DATE,
  deadline DATE,             -- Project due date. If deadline < today and status != 'completed', project is delayed
  estimated_budget NUMERIC,  -- Planned budget in INR
  actual_cost NUMERIC        -- Actual spend in INR. If actual_cost > estimated_budget, project is over budget
);

CREATE TABLE project_assignments (
  id INTEGER PRIMARY KEY,
  project_id INTEGER REFERENCES projects(id),
  employee_id INTEGER REFERENCES employees(id),
  hours_allocated INTEGER,   -- Total hours assigned to this employee for this project
  hours_logged INTEGER       -- Actual hours worked. If hours_logged > hours_allocated, employee is in overtime
);

CREATE TABLE revenue (
  id INTEGER PRIMARY KEY,
  client_id INTEGER REFERENCES clients(id),  -- Revenue belongs to clients, NOT employees
  project_id INTEGER REFERENCES projects(id),
  amount NUMERIC,            -- Revenue amount in INR
  revenue_date DATE
);

CREATE TABLE expenses (
  id INTEGER PRIMARY KEY,
  category VARCHAR,          -- Values: 'salary', 'software', 'marketing', 'Rent', 'Contractor Fees', 'Cloud Infrastructure', 'SaaS & Tooling'
  amount NUMERIC,            -- Expense amount in INR
  expense_date DATE,
  project_id INTEGER REFERENCES projects(id)  -- Can be NULL for company-wide expenses
);

CREATE TABLE tasks (
  id INTEGER PRIMARY KEY,
  project_id INTEGER REFERENCES projects(id),
  assigned_to INTEGER REFERENCES employees(id),  -- This is an employee ID (integer), not a name. JOIN with employees to get name
  status VARCHAR,            -- Values: 'pending', 'completed', 'delayed'
  priority VARCHAR,          -- Values: 'high', 'medium', 'low'
  due_date DATE,
  completed_date DATE        -- NULL if not yet completed
);

CREATE TABLE meetings (
  id INTEGER PRIMARY KEY,
  project_id INTEGER REFERENCES projects(id),
  meeting_date TIMESTAMP,
  meeting_type VARCHAR,      -- Values: 'internal', 'client' (case may vary: 'Internal', 'Client')
  duration_minutes INTEGER   -- Ranges from 30 to 140 minutes
);

CREATE TABLE client_feedback (
  id INTEGER PRIMARY KEY,
  client_id INTEGER REFERENCES clients(id),
  project_id INTEGER REFERENCES projects(id),
  rating INTEGER,            -- 1 to 5 scale (1=worst, 5=best)
  feedback_text TEXT,        -- Client's written feedback about the project
  feedback_date DATE
);
"""

# Template for sqlcoder:7b — question is injected at call time
SQLCODER_PROMPT_TEMPLATE = """### Task
Generate a PostgreSQL query to answer the following question: `{question}`

### Instructions
- Use PostgreSQL syntax. Use ILIKE for case-insensitive matching.
- Generate ONLY the SQL query. No explanations or commentary.
- Use only SELECT statements. Never use INSERT, UPDATE, DELETE, DROP.
- Use proper JOINs to connect related tables.
- Limit to 100 rows unless specified.
- Revenue belongs to clients and projects, NOT employees.
- To find overtime: hours_logged - hours_allocated from project_assignments.
- To get client names: JOIN revenue with clients table.

### Database Schema
{schema}

### Example Questions and SQL

Question: Which client brings the most revenue?
SQL: SELECT c.name, SUM(r.amount) AS total_revenue FROM clients c JOIN revenue r ON c.id = r.client_id GROUP BY c.id, c.name ORDER BY total_revenue DESC LIMIT 1;

Question: List all employees and their roles
SQL: SELECT name, role, department, monthly_salary FROM employees WHERE status = 'active' ORDER BY name;

Question: Who is the frontend developer?
SQL: SELECT name, role, department, monthly_salary FROM employees WHERE role ILIKE '%frontend%';

Question: Which projects are over budget?
SQL: SELECT p.project_name, c.name AS client_name, p.estimated_budget, p.actual_cost, (p.actual_cost - p.estimated_budget) AS over_budget FROM projects p JOIN clients c ON p.client_id = c.id WHERE p.actual_cost > p.estimated_budget ORDER BY over_budget DESC;

Question: Which employees are working overtime?
SQL: SELECT e.name, e.role, SUM(pa.hours_allocated) AS total_allocated, SUM(pa.hours_logged) AS total_logged, SUM(pa.hours_logged) - SUM(pa.hours_allocated) AS overtime_hours FROM employees e JOIN project_assignments pa ON e.id = pa.employee_id GROUP BY e.id, e.name, e.role HAVING SUM(pa.hours_logged) > SUM(pa.hours_allocated) ORDER BY overtime_hours DESC;

Question: What is the total expense by category?
SQL: SELECT category, SUM(amount) AS total_expense FROM expenses GROUP BY category ORDER BY total_expense DESC;

Question: How many clients were acquired via referral?
SQL: SELECT COUNT(*) AS referral_count FROM clients WHERE acquisition_channel ILIKE '%Referral%';

Question: List active projects
SQL: SELECT p.project_name, c.name AS client_name, p.status, p.start_date, p.deadline FROM projects p JOIN clients c ON p.client_id = c.id WHERE p.status ILIKE '%active%' ORDER BY p.project_name;

Question: Which client is most profitable?
SQL: SELECT c.name, SUM(r.amount) AS total_revenue FROM clients c JOIN revenue r ON c.id = r.client_id GROUP BY c.id, c.name ORDER BY total_revenue DESC LIMIT 1;

Question: Which projects are over budget?
SQL: SELECT p.project_name, c.name AS client, p.estimated_budget, p.actual_cost, (p.actual_cost - p.estimated_budget) AS overrun FROM projects p JOIN clients c ON p.client_id = c.id WHERE p.actual_cost > p.estimated_budget ORDER BY overrun DESC;

Now generate the SQL for the given question.

### SQL
"""

def clean_sql_output(llm_output: str) -> str:
    """
    Cleans the LLM output to extract just the SQL query.
    Handles: markdown blocks, trailing commentary, explanatory text.
    """
    cleaned = llm_output.strip()
    
    # Remove markdown code blocks if present
    match = re.search(r"```(?:sql)?(.*?)```", cleaned, re.DOTALL | re.IGNORECASE)
    if match:
        cleaned = match.group(1).strip()
    
    # Line-by-line: keep only SQL lines, stop at first commentary line
    sql_lines = []
    sql_keywords = {'select', 'from', 'where', 'join', 'left', 'right', 'inner', 'outer',
                    'on', 'and', 'or', 'group', 'order', 'having', 'limit', 'with', 'as',
                    'case', 'when', 'then', 'else', 'end', 'in', 'not', 'is', 'null',
                    'count', 'sum', 'avg', 'max', 'min', 'round', 'coalesce', 'nullif',
                    'cast', 'distinct', 'union', 'exists', 'between', 'like', 'ilike',
                    'asc', 'desc', 'filter', 'over', 'partition', 'by', '(', ')'}
    
    for line in cleaned.split('\n'):
        stripped = line.strip()
        if not stripped:
            sql_lines.append(line)
            continue
        
        first_word = stripped.split()[0].lower().rstrip('(,;')
        
        if (first_word in sql_keywords or 
            stripped.startswith(('(', ')', ',', '--')) or
            first_word.startswith(('(', ')', ','))):
            sql_lines.append(line)
        else:
            break
    
    result = '\n'.join(sql_lines).strip()
    return result if result else cleaned

def validate_query(query: str) -> bool:
    """Validates that the query is safe to run."""
    q = query.lower().strip().rstrip(';').strip()
    
    if not (q.startswith("select") or q.startswith("with")):
        logger.warning(f"Blocked non-SELECT/WITH query: {query}")
        return False
    
    forbidden_keywords = ["insert", "update", "delete", "drop", "alter", "truncate", "grant", "revoke"]
    for word in forbidden_keywords:
        pattern = r"\b" + re.escape(word) + r"\b"
        if re.search(pattern, q):
            logger.warning(f"Blocked query with forbidden keyword '{word}': {query}")
            return False
    return True

async def generate_and_execute_sql(user_query: str, model_name: str = "sqlcoder:7b"):
    """
    Orchestrates the SQL generation and execution flow.
    Uses qwen2.5:7b (primary) with sqlcoder:7b as fallback.
    Includes name typo correction and deterministic shortcuts.
    Returns:
        - success (bool)
        - data (list of dicts) or error message (str)
        - sql_query (str) used
    """

    # --- STEP 0: Fix name typos ---
    try:
        correction_messages = [
            {"role": "system", "content": (
                "You fix typos in names. Given a user query, if any person/company/project name "
                "has a typo, correct it using the known names below. Output ONLY the corrected query, nothing else. "
                "If there are no typos, output the original query unchanged.\n\n"
                "Known employees: Aarav Shah, Riya Patel, Kunal Mehta, Neha Jain, Dev Malhotra, "
                "Ishita Rao, Rahul Kapoor, Simran Kaur, Arjun Verma, Priya Nair, Aditya Singh, "
                "Meera Iyer, Sanjay Desai, Ananya Gupta, Rohan Das\n"
                "Known clients: Apollo Care, City Hospital, Urban Realty, Dream Homes, TechNova, "
                "HealthPlus, StudioTalk, EstatePro, Medico CRM, SaaSify, Arcadia Financial, PulseHealth Network\n"
                "Known projects: Apollo CRM Phase 2, City CRM Setup, Urban 3D Tower, Dream Homes 3D, "
                "TechNova SaaS Core, HealthPlus CRM, StudioTalk Podcast, EstatePro 3D, Medico CRM Expansion, "
                "SaaSify Platform Build, Arcadia Risk Scoring Engine, PulseHealth Telehealth Integration"
            )},
            {"role": "user", "content": user_query}
        ]
        correction_resp = await llm_client.chat(
            model="qwen2.5:7b",
            messages=correction_messages,
            options={"temperature": 0.0, "num_predict": 150}
        )
        corrected = correction_resp['message']['content'].strip()
        if corrected and len(corrected) < 500 and len(corrected) > 5:
            if corrected.lower() != user_query.lower():
                logger.info(f"✏️ Name correction: '{user_query}' -> '{corrected}'")
            user_query = corrected
    except Exception as e:
        logger.error(f"Name correction failed: {e}")

    # --- DETERMINISTIC SHORTCUT: Overtime / Workload Queries ---
    _q = user_query.lower()
    _overtime_keywords = [
        "overtime", "overwork", "over work", "extra hours",
        "more than allocated", "excess hours", "working more",
        "overloaded", "overburdened", "over time",
    ]
    if any(kw in _q for kw in _overtime_keywords):
        logger.info("⚡ Overtime shortcut: bypassing LLM SQL generation")
        _overtime_sql = (
            "SELECT e.name, e.role, e.department, "
            "SUM(pa.hours_allocated) AS total_allocated, "
            "SUM(pa.hours_logged) AS total_logged, "
            "SUM(pa.hours_logged) - SUM(pa.hours_allocated) AS overtime_hours "
            "FROM employees e "
            "JOIN project_assignments pa ON e.id = pa.employee_id "
            "GROUP BY e.id, e.name, e.role, e.department "
            "HAVING SUM(pa.hours_logged) > SUM(pa.hours_allocated) "
            "ORDER BY overtime_hours DESC"
        )
        try:
            results = execute_read_only_query(_overtime_sql)
            logger.info(f"Overtime shortcut returned {len(results)} rows")
            if results and len(results) > 0:
                return True, results, _overtime_sql
        except Exception as e:
            logger.error(f"Overtime shortcut DB error: {e}")
        # If shortcut fails for any reason, fall through to LLM path
    # --- END SHORTCUT ---

    # --- PRIMARY: qwen2.5:7b via chat() API ---
    # Chat models understand natural language -> column mappings much better
    primary_system = (
        "You are a PostgreSQL query generator. Output ONLY a single SQL SELECT query. "
        "NEVER use WITH/CTE. NEVER add explanations. NEVER add text before or after the query. "
        "ALWAYS use ILIKE for text matching (case-insensitive). "
        "ALWAYS JOIN with parent tables to show human-readable names instead of raw IDs in results (e.g. project_name instead of project_id, employee name instead of employee_id, client name instead of client_id). "
        "ALWAYS SELECT multiple relevant columns, NEVER return just a single column. For employees: always include name, role, department, monthly_salary. For projects: always include project_name, client_id/client name, status. For clients: always include name, industry, acquisition_channel. "
        "Available tables and columns:\n"
        "- employees (id INT PK, name TEXT [e.g. 'Aarav Shah','Riya Patel'], role TEXT ['Backend Developer','Frontend Developer','Fullstack Developer','UI/UX Designer','Project Manager','Sales Executive','Marketing Manager','Video Editor','3D Artist','DevOps Engineer','Content Strategist','QA Engineer','Business Analyst','Support Engineer'], department TEXT ['Engineering','Design','Sales','Marketing','Operations','Production','Support'], monthly_salary NUMERIC [INR, 45000-75000], hire_date DATE, status TEXT ['active','inactive'])\n"
        "- clients (id INT PK, name TEXT [e.g. 'Apollo Care','TechNova','Dream Homes','StudioTalk'], industry TEXT ['Healthcare','Real Estate','Technology','Media','FinTech','HealthTech'], acquisition_channel TEXT [how client was acquired: 'Referral','LinkedIn','Cold Email','Cold Call','Inbound','Instagram','Outbound'], contract_type TEXT ['recurring','project','Retainer','Fixed-Price'], start_date DATE)\n"
        "- projects (id INT PK, project_name TEXT [e.g. 'Apollo CRM Phase 2','TechNova SaaS Core'], client_id INT FK->clients.id, status TEXT ['ongoing','delayed','completed','active'], start_date DATE, deadline DATE, estimated_budget NUMERIC [INR], actual_cost NUMERIC [INR, if > estimated_budget then over budget])\n"
        "- project_assignments (id INT PK, project_id INT FK->projects.id, employee_id INT FK->employees.id, hours_allocated FLOAT [assigned hours], hours_logged FLOAT [actual hours worked, if > hours_allocated then overtime])\n"
        "- revenue (id INT PK, client_id INT FK->clients.id [revenue belongs to clients NOT employees], project_id INT FK->projects.id, amount NUMERIC [INR], revenue_date DATE)\n"
        "- expenses (id INT PK, project_id INT FK->projects.id [NULL for company-wide], amount NUMERIC [INR], expense_date DATE, category TEXT ['salary','software','marketing','Rent','Contractor Fees','Cloud Infrastructure','SaaS & Tooling'])\n"
        "- tasks (id INT PK, project_id INT FK->projects.id, assigned_to INT FK->employees.id [INTEGER employee ID, join with employees for name], status TEXT ['pending','completed','delayed'], priority TEXT ['high','medium','low'], due_date DATE, completed_date DATE [NULL if not done])\n"
        "- meetings (id INT PK, project_id INT FK->projects.id, meeting_type TEXT ['internal','client','Internal','Client'], meeting_date TIMESTAMP, duration_minutes INT [30-140])\n"
        "- client_feedback (id INT PK, client_id INT FK->clients.id, project_id INT FK->projects.id, rating INT [1-5, 1=worst 5=best], feedback_text TEXT, feedback_date DATE)\n\n"
        "KEY RELATIONSHIPS: Revenue belongs to clients (JOIN revenue r ON c.id = r.client_id). "
        "Employees are assigned to projects via project_assignments (JOIN on employee_id and project_id). "
        "Overtime = hours_logged - hours_allocated from project_assignments. "
        "Tasks assigned_to is an INTEGER employee ID, always JOIN with employees to get names.\n\n"
        "BUSINESS CONCEPTS:\n"
        "- 'profitable client' or 'most profitable' = client with highest total revenue (SUM revenue.amount grouped by client)\n"
        "- 'over budget' or 'cost overrun' = projects where actual_cost > estimated_budget\n"
        "- 'burn rate' = total monthly expenses from expenses table\n"
        "- 'salary cost' = SUM of monthly_salary from employees\n"
        "- 'client performance' or 'client rating' = AVG rating from client_feedback\n"
        "- 'project rating' or 'rating below X' = rating column in client_feedback table, JOIN with projects and clients for names\n"
        "- 'workload' or 'utilization' = hours_logged vs hours_allocated from project_assignments\n"
        "- 'forecast revenue' or 'predict' or 'project revenue' = first pull historical monthly revenue data (grouped by month), then the data can be used to project trends\n"
        "- 'revenue trend' or 'monthly revenue' = SUM revenue.amount grouped by DATE_TRUNC('month', revenue_date)\n\n"
        "CRITICAL RULES:\n"
        "- ALWAYS include the name column when querying employees (e.g. e.name), clients (c.name), or projects (p.project_name)\n"
        "- NEVER return only IDs or only non-name columns. The name MUST always be in SELECT.\n"
        "- For ANY query about a specific entity, return ALL key info about it.\n\n"
        "EXAMPLES:\n"
        "Q: Which client brings the most revenue? -> SELECT c.name, SUM(r.amount) AS total_revenue FROM clients c JOIN revenue r ON c.id = r.client_id GROUP BY c.id, c.name ORDER BY total_revenue DESC LIMIT 1;\n"
        "Q: Which client is most profitable? -> SELECT c.name, SUM(r.amount) AS total_revenue FROM clients c JOIN revenue r ON c.id = r.client_id GROUP BY c.id, c.name ORDER BY total_revenue DESC LIMIT 1;\n"
        "Q: Which client is linked to a project? -> SELECT c.name, c.industry, c.acquisition_channel, p.project_name, p.status FROM projects p JOIN clients c ON p.client_id = c.id WHERE p.project_name ILIKE '%project_name%';\n"
        "Q: How many clients were acquired via referral? -> SELECT COUNT(*) AS referral_count FROM clients WHERE acquisition_channel ILIKE '%Referral%';\n"
        "Q: List active projects -> SELECT p.project_name, c.name AS client_name, p.status FROM projects p JOIN clients c ON p.client_id = c.id WHERE p.status ILIKE '%active%';\n"
        "Q: Which employees are working overtime? -> SELECT e.name, e.role, SUM(pa.hours_logged) - SUM(pa.hours_allocated) AS overtime_hours FROM employees e JOIN project_assignments pa ON e.id = pa.employee_id GROUP BY e.id, e.name, e.role HAVING SUM(pa.hours_logged) > SUM(pa.hours_allocated);\n"
        "Q: What is the total revenue? -> SELECT SUM(amount) AS total_revenue FROM revenue;\n"
        "Q: Which projects are delayed? -> SELECT p.project_name, p.deadline, p.status FROM projects p WHERE p.status ILIKE '%delayed%';\n"
        "Q: Which client belongs to media industry? -> SELECT name, industry, acquisition_channel FROM clients WHERE industry ILIKE '%media%';\n"
        "Q: Show tasks assigned to a specific employee -> SELECT t.id, p.project_name, t.status, t.priority, t.due_date FROM tasks t JOIN projects p ON t.project_id = p.id JOIN employees e ON t.assigned_to = e.id WHERE e.name ILIKE '%name%';\n"
        "Q: What is the average client feedback rating? -> SELECT AVG(rating) AS avg_rating FROM client_feedback;\n"
        "Q: Show meeting count per project -> SELECT p.project_name, COUNT(m.id) AS meeting_count FROM projects p JOIN meetings m ON p.id = m.project_id GROUP BY p.id, p.project_name ORDER BY meeting_count DESC;\n"
        "Q: Which projects are over budget? -> SELECT p.project_name, c.name AS client, p.estimated_budget, p.actual_cost, (p.actual_cost - p.estimated_budget) AS overrun FROM projects p JOIN clients c ON p.client_id = c.id WHERE p.actual_cost > p.estimated_budget ORDER BY overrun DESC;\n"
        "Q: Projects with rating below 3 -> SELECT p.project_name, c.name AS client, cf.rating, cf.feedback_text FROM client_feedback cf JOIN projects p ON cf.project_id = p.id JOIN clients c ON cf.client_id = c.id WHERE cf.rating < 3 ORDER BY cf.rating ASC;\n"
        "Q: List all internal meetings with their dates and projects -> SELECT p.project_name, m.meeting_date, m.meeting_type, m.duration_minutes FROM meetings m JOIN projects p ON m.project_id = p.id WHERE m.meeting_type ILIKE '%internal%' ORDER BY m.meeting_date DESC;\n"
        "Q: Forecast revenue for next 3 months -> SELECT DATE_TRUNC('month', revenue_date) AS month, SUM(amount) AS monthly_revenue FROM revenue GROUP BY DATE_TRUNC('month', revenue_date) ORDER BY month;\n"
        "Q: Show monthly revenue trend -> SELECT DATE_TRUNC('month', revenue_date) AS month, SUM(amount) AS monthly_revenue FROM revenue GROUP BY DATE_TRUNC('month', revenue_date) ORDER BY month;\n"
    )

    try:
        primary_messages = [
            {"role": "system", "content": primary_system},
            {"role": "user", "content": user_query}
        ]
        primary_resp = await llm_client.chat(
            model="qwen2.5:7b",
            messages=primary_messages,
            options={"temperature": 0.1, "num_predict": 400}
        )
        raw_sql1 = primary_resp['message']['content']
        sql1 = clean_sql_output(raw_sql1).rstrip(';').strip()
        logger.info(f"Primary SQL (qwen): {sql1}")

        if validate_query(sql1):
            try:
                results1 = execute_read_only_query(sql1)
                logger.info(f"Primary SQL returned {len(results1)} rows")
                if results1 and len(results1) > 0 and any(results1):
                    return True, results1, sql1
            except Exception as e1:
                logger.error(f"Primary SQL execution error: {e1} | Query: {sql1}")

        # --- FALLBACK: sqlcoder:7b via generate() API ---
        logger.info("Primary attempt returned empty/failed. Falling back to sqlcoder:7b...")
        prompt_fallback = SQLCODER_PROMPT_TEMPLATE.format(question=user_query, schema=DB_SCHEMA_DDL)
        response = await llm_client.generate(
            model="sqlcoder:7b",
            prompt=prompt_fallback,
            options={"temperature": 0.1, "num_predict": 500}
        )
        raw_sql2 = response['response']
        sql2 = clean_sql_output(raw_sql2).rstrip(';').strip()
        logger.info(f"Fallback SQL (sqlcoder): {sql2}")

        if validate_query(sql2):
            try:
                results2 = execute_read_only_query(sql2)
                logger.info(f"Fallback SQL returned {len(results2)} rows")
                if results2 and len(results2) > 0 and any(results2):
                    return True, results2, sql2
            except Exception as e2:
                logger.error(f"Fallback SQL execution error: {e2} | Query: {sql2}")

        # Both attempts returned empty — return primary result with context
        return True, [], sql1

    except Exception as e:
        logger.error(f"SQL Agent Error: {e}")
        return False, f"System error: {str(e)}", ""

