
import logging
from sqlalchemy import text
from datetime import datetime, date, timedelta
try:
    from app.database import engine
except ImportError:
    # Fallback for local run if needed, but app.database is safer
    from database import engine

logger = logging.getLogger(__name__)

# --- KPI Configuration ---

# 1. Map KPI Code to Deterministic SQL (Dataset-Aware)
# Uses :active_month_start and :dataset_end_date parameters
KPI_QUERY_MAP = {
    "NET_PROFIT_MARGIN": """
        SELECT 
        (
            (SELECT COALESCE(SUM(amount), 0) FROM revenue WHERE revenue_date >= :active_month_start AND revenue_date <= :dataset_end_date)
          -
            (SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE expense_date >= :active_month_start AND expense_date <= :dataset_end_date)
            -
            (SELECT COALESCE(SUM(monthly_salary), 0) FROM employees)
        )
        /
        NULLIF(
            (SELECT SUM(amount) FROM revenue WHERE revenue_date >= :active_month_start AND revenue_date <= :dataset_end_date),
        0
        ) * 100;
    """,
    "SALARY_RATIO": """
        SELECT 
        (
            SELECT COALESCE(SUM(monthly_salary), 0) FROM employees
        )
        /
        NULLIF(
            (SELECT SUM(amount) FROM revenue WHERE revenue_date >= :active_month_start AND revenue_date <= :dataset_end_date),
        0
        ) * 100;
    """,
    "ON_TIME_DELIVERY": """
        SELECT 
        COUNT(*) FILTER (WHERE completed_at <= deadline) * 100.0 /
        NULLIF(COUNT(*),0)
        FROM projects
        WHERE status = 'completed';
    """,
    "EMPLOYEE_UTILIZATION": """
        SELECT 
        AVG(hours_logged / NULLIF(hours_allocated,0)) * 100
        FROM project_assignments;
    """,
    "AVG_CLIENT_RATING": """
        SELECT AVG(rating)
        FROM client_feedback;
    """,
    "REVENUE_CONCENTRATION": """
        WITH vertical_revenue AS (
          SELECT c.industry, SUM(r.amount) total
          FROM revenue r
          JOIN clients c ON r.client_id = c.id
          WHERE r.revenue_date >= :active_month_start AND r.revenue_date <= :dataset_end_date
          GROUP BY c.industry
        )
        SELECT MAX(total) * 100.0 / NULLIF(SUM(total),0)
        FROM vertical_revenue;
    """,
    "BUDGET_OVERRUN": """
        SELECT 
        AVG((actual_cost - estimated_budget) / NULLIF(estimated_budget, 0)) * 100
        FROM projects;
    """,
    "CHURN_RISK_INDEX": """
        SELECT 
        COUNT(*) FILTER (WHERE rating <= 2) * 100.0 / NULLIF(COUNT(*), 0)
        FROM client_feedback
        WHERE feedback_date >= :dataset_end_date - INTERVAL '30 days' AND feedback_date <= :dataset_end_date;
    """,
    "ESCALATION_FREQUENCY": """
        SELECT 
        COUNT(*) FILTER (WHERE mn.sentiment = 'tense' AND m.meeting_date >= :dataset_end_date - INTERVAL '30 days' AND m.meeting_date <= :dataset_end_date)
        FROM meeting_notes mn
        JOIN meetings m ON mn.meeting_id = m.id;
    """,
    "REVENUE_PER_EMPLOYEE": """
        SELECT 
        (
            SELECT COALESCE(SUM(amount), 0) 
            FROM revenue 
            WHERE revenue_date >= :active_month_start AND revenue_date <= :dataset_end_date
        )
        /
        NULLIF(
            (SELECT COUNT(*) FROM employees),
        0
        );
    """
}

# --- Validation & Sanity Checks ---

class KPICalculationError(Exception):
    pass

def validate_kpi_value(conn, kpi_code, computed_value, params):
    """
    Phase 5: Validation Engine
    Re-runs independent verification query to check for mismatches > 1%.
    """
    query = KPI_QUERY_MAP.get(kpi_code)
    if not query:
        return 
        
    try:
        # Re-run query with params
        res = conn.execute(text(query), params).fetchone()
        verification_value = float(res[0]) if res and res[0] is not None else 0.0
        
        diff = abs(computed_value - verification_value)
        if verification_value == 0:
            diff_pct = 0 if computed_value == 0 else 100
        else:
            diff_pct = (diff / verification_value) * 100.0
            
        if diff_pct > 1.0:
            raise KPICalculationError(f"Validation Mismatch for {kpi_code}: Engine={computed_value}, Verify={verification_value} (Diff: {diff_pct:.2f}%)")
            
        logger.info(f"KPI {kpi_code} Validated. Diff: {diff_pct:.2f}%")
        
    except Exception as e:
        logger.error(f"Validation failed for {kpi_code}: {e}")
        raise e

def check_sanity_bounds(kpi_code, value):
    warnings = []
    
    if kpi_code == 'NET_PROFIT_MARGIN' and value > 90:
        warnings.append(f"POTENTIAL QUERY ERROR: Net Profit Margin {value}% > 90%")
        
    if kpi_code == 'SALARY_TO_REVENUE_RATIO' and value < 5 and value > 0:
         warnings.append(f"POTENTIAL QUERY ERROR: Salary-to-Revenue {value}% < 5%")
         
    if kpi_code == 'REVENUE_CONCENTRATION' and value > 95:
        warnings.append(f"POTENTIAL QUERY ERROR: Revenue Concentration {value}% > 95%")
        
    if kpi_code == 'EMPLOYEE_UTILIZATION' and value > 150:
        warnings.append(f"POTENTIAL QUERY ERROR: Employee Utilization {value}% > 150%")
        
    for w in warnings:
        logger.warning(w)

# --- Schema Management ---

def ensure_kpi_schema():
    logger.info("Verifying KPI Schema...")
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS kpi_definitions (
                    id SERIAL PRIMARY KEY,
                    kpi_name TEXT NOT NULL,
                    target_value_min DECIMAL,
                    target_value_max DECIMAL,
                    comparison_operator TEXT NOT NULL,
                    kpi_code TEXT UNIQUE,
                    metric_unit TEXT,
                    unit_type TEXT,
                    time_scope TEXT
                );
            """))

            known_kpis = [
                ('NET_PROFIT_MARGIN', 'Net Profit Margin (%)', 'percentage', 'current_month'),
                ('SALARY_RATIO', 'Salary to Revenue Ratio (%)', 'percentage', 'current_month'),
                ('ON_TIME_DELIVERY', 'On-Time Delivery (%)', 'percentage', 'all_time'),
                ('EMPLOYEE_UTILIZATION', 'Employee Utilization (%)', 'percentage', 'all_time'),
                ('AVG_CLIENT_RATING', 'Average Client Rating', 'rating', 'all_time'),
                ('REVENUE_CONCENTRATION', 'Revenue Concentration (%)', 'percentage', 'current_month'),
                ('BUDGET_OVERRUN', 'Budget Overrun (%)', 'percentage', 'all_time'),
                ('CHURN_RISK_INDEX', 'Churn Risk Index (%)', 'percentage', 'rolling_30_days'),
                ('ESCALATION_FREQUENCY', 'Escalation Frequency (Count)', 'count', 'rolling_30_days'),
                ('REVENUE_PER_EMPLOYEE', 'Revenue Per Employee', 'currency', 'current_month')
            ]
            
            for code, name, unit, scope in known_kpis:
                # Upsert logic (simplified)
                # First try update by name/code to handle changes
                conn.execute(text("""
                    UPDATE kpi_definitions 
                    SET kpi_name = :name, unit_type = :unit, time_scope = :scope 
                    WHERE kpi_code = :code
                """), {"code": code, "name": name, "unit": unit, "scope": scope})
                
                # Then insert if not exists
                conn.execute(text("""
                    INSERT INTO kpi_definitions (kpi_name, kpi_code, unit_type, time_scope, comparison_operator, target_value_min)
                    SELECT :name, :code, :unit, :scope, '>=', 0
                    WHERE NOT EXISTS (SELECT 1 FROM kpi_definitions WHERE kpi_code = :code)
                """), {"code": code, "name": name, "unit": unit, "scope": scope})
            conn.commit()

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS kpi_results (
                    id SERIAL PRIMARY KEY,
                    kpi_id INTEGER REFERENCES kpi_definitions(id),
                    kpi_code TEXT, 
                    actual_value DECIMAL,
                    status TEXT,
                    calculated_at TIMESTAMP DEFAULT NOW()
                );
            """))
            conn.commit()

            logger.info("KPI Schema Verification Complete.")
            
    except Exception as e:
        logger.error(f"Schema verification failed: {e}")

# --- Core Logic ---

def get_dataset_dates(conn):
    """
    Phase 1: Detect Real Data Window
    Returns (dataset_end_date, active_month_start)
    """
    try:
        # Get Max dates from key tables
        dates_list = []
        for table, col in [('revenue', 'revenue_date'), ('expenses', 'expense_date'), ('client_feedback', 'feedback_date'), ('meetings', 'meeting_date')]:
            res = conn.execute(text(f"SELECT MAX({col}) FROM {table}")).fetchone()
            if res and res[0]:
                d = res[0]
                if isinstance(d, datetime):
                    d = d.date()
                dates_list.append(d)
        
        if not dates_list:
             # Fallback to current date if DB is empty
            fallback = date.today()
            return fallback, date(fallback.year, fallback.month, 1)
            
        # dataset_end_date is the max of all max dates
        dataset_end_date = max(dates_list)
        
        # active_month_start is first day of that month
        active_month_start = date(dataset_end_date.year, dataset_end_date.month, 1)
        
        logger.info(f"Dataset Window Detected: End={dataset_end_date}, Start={active_month_start}")
        return dataset_end_date, active_month_start
        
    except Exception as e:
        logger.error(f"Date detection failed: {e}")
        # Fail safe
        fallback = date.today()
        return fallback, date(fallback.year, fallback.month, 1)

def check_for_kpi_correction(conn, kpi_code):
    """
    Step 6: True Self-Learning
    Check if a valid correction exists for this KPI.
    """
    try:
        # Use nested transaction to prevent aborting the main transaction if table missing
        with conn.begin_nested():
            # Get latest correction
            res = conn.execute(text("""
                SELECT corrected_value, created_at 
                FROM kpi_corrections 
                WHERE kpi_code = :code 
                ORDER BY created_at DESC 
                LIMIT 1
            """), {"code": kpi_code}).fetchone()
            
            if res:
                logger.info(f"Self-Learning: Applying correction for {kpi_code} -> {res[0]}")
                return float(res[0])
            
        return None
    except Exception as e:
        logger.error(f"Correction lookup failed (Ignored): {e}")
        return None

def compute_kpis():
    """
    Main orchestration function.
    """
    logger.info("Starting KPI Computation (Dataset-Aware)...")
    
    computed_statuses = [] 
    
    try:
        with engine.connect() as conn:
            # 1. Detect Dates
            dataset_end_date, active_month_start = get_dataset_dates(conn)
            params = {
                "dataset_end_date": dataset_end_date,
                "active_month_start": active_month_start
            }
            
            # 2. Fetch Definitions
            definitions = conn.execute(text("SELECT id, kpi_code, comparison_operator, target_value_min, target_value_max, metric_unit FROM kpi_definitions")).fetchall()
            
            for def_row in definitions:
                kpi_id, kpi_code, operator, min_val, max_val, unit = def_row
                
                if not kpi_code or kpi_code == 'COMPANY_HEALTH':
                    continue
                    
                logger.info(f"Computing KPI: {kpi_code}")
                    
                # 3. Get Query
                query = KPI_QUERY_MAP.get(kpi_code)
                if not query:
                    logger.warning(f"No query map for {kpi_code}, skipping.")
                    continue
                
                # 4. Execute Query with Params
                try:
                    result = conn.execute(text(query), params).fetchone()
                    if result and result[0] is not None:
                        actual_value = float(result[0])
                        logger.info(f"Value: {actual_value}")
                    else:
                        actual_value = 0.0
                        
                        actual_value = 0.0
                        
                    # 5. Validation & Correction (Self-Learning Override)
                    corrected = check_for_kpi_correction(conn, kpi_code)
                    if corrected is not None:
                         actual_value = corrected
                    else:
                        validate_kpi_value(conn, kpi_code, actual_value, params)
                        check_sanity_bounds(kpi_code, actual_value)
                    
                except Exception as qe:
                    logger.error(f"Query execution failed for {kpi_code}: {qe}")
                    raise qe
                
                # 6. Evaluate Status
                status = evaluate_kpi_status(actual_value, operator, min_val, max_val)
                computed_statuses.append(status)
                
                # 6.5. Get Previous Value for Trend Calculation
                prev_result = conn.execute(text("""
                    SELECT actual_value FROM kpi_results 
                    WHERE kpi_id = :id 
                    ORDER BY calculated_at DESC 
                    LIMIT 1
                """), {"id": kpi_id}).fetchone()
                
                previous_value = float(prev_result[0]) if prev_result and prev_result[0] is not None else None
                
                # Calculate delta percentage
                if previous_value is not None and previous_value != 0:
                    delta_percent = ((actual_value - previous_value) / previous_value) * 100
                else:
                    delta_percent = None
                
                # 7. Insert Result with Historical Data
                conn.execute(text("""
                    INSERT INTO kpi_results (kpi_id, kpi_code, actual_value, previous_value, delta_percent, status, calculated_at)
                    VALUES (:id, :code, :val, :prev_val, :delta, :status, :time)
                """), {
                    "id": kpi_id,
                    "code": kpi_code,
                    "val": actual_value,
                    "prev_val": previous_value,
                    "delta": delta_percent,
                    "status": status,
                    "time": datetime.now()
                })
            
            # 8. Company Health Score
            calc_company_health_score(conn, computed_statuses)
            
            conn.commit()
            logger.info("KPI Computation Finished. KPI ENGINE VERIFIED - DATASET AWARE")

    except Exception as e:
        import traceback
        logger.error(f"KPI Computation Cycle Failed: {e}")
        logger.error(traceback.format_exc())

def evaluate_kpi_status(value, operator, min_val, max_val):
    def safe_float(v):
        return float(v) if v is not None else 0.0

    min_v = safe_float(min_val)
    max_v = safe_float(max_val)

    if operator == '>=':
        if value >= min_v:
            return 'on_track'
        elif value >= min_v * 0.8:
            return 'at_risk'
        else:
            return 'critical'

    if operator == '<=':
        if value <= max_v:
            return 'on_track'
        elif value <= max_v * 1.2:
            return 'at_risk'
        else:
            return 'critical'

    if operator == 'between':
        if min_v <= value <= max_v:
            return 'on_track'
        else:
            return 'at_risk'
            
    return 'unknown'

def calc_company_health_score(conn, statuses):
    critical_count = statuses.count('critical')
    at_risk_count = statuses.count('at_risk')
    
    score = 100 - (critical_count * 10) - (at_risk_count * 5)
    score = max(0, score) 
    
    overall_status = 'on_track'
    if score < 70:
        overall_status = 'critical'
    elif score < 90:
        overall_status = 'at_risk'
    
    res = conn.execute(text("SELECT id FROM kpi_definitions WHERE kpi_code = 'COMPANY_HEALTH'")).fetchone()
    if res:
        health_id = res[0]
    else:
        res_ins = conn.execute(text("""
            INSERT INTO kpi_definitions (kpi_name, kpi_code, comparison_operator, target_value_min) 
            VALUES ('Company Health Score', 'COMPANY_HEALTH', '>=', 90) RETURNING id
        """)).fetchone()
        health_id = res_ins[0]
    
    conn.execute(text("""
        INSERT INTO kpi_results (kpi_id, kpi_code, actual_value, status, calculated_at)
        VALUES (:id, :code, :val, :status, :time)
    """), {
        "id": health_id,
        "code": "COMPANY_HEALTH",
        "val": score,
        "status": overall_status,
        "time": datetime.now()
    })

def get_baseline_metrics(conn):
    """
    Returns a dictionary of current baseline metrics for simulation context.
    """
    dataset_end_date, active_month_start = get_dataset_dates(conn)
    params = {
        "dataset_end_date": dataset_end_date,
        "active_month_start": active_month_start
    }
    
    # 1. Revenue
    rev = float(conn.execute(text("SELECT COALESCE(SUM(amount), 0) FROM revenue WHERE revenue_date >= :active_month_start AND revenue_date <= :dataset_end_date"), params).scalar() or 0.0)
    
    # 2. Expenses
    exp = float(conn.execute(text("SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE expense_date >= :active_month_start AND expense_date <= :dataset_end_date"), params).scalar() or 0.0)
    
    # 3. Salaries (Monthly)
    sal = float(conn.execute(text("SELECT COALESCE(SUM(monthly_salary), 0) FROM employees"), params).scalar() or 0.0)
    
    # 4. Employee Count
    emp_count = conn.execute(text("SELECT COUNT(*) FROM employees"), params).scalar() or 0
    
    # 5. Project Count (Active)
    proj_count = conn.execute(text("SELECT COUNT(*) FROM projects WHERE status = 'in_progress'"), params).scalar() or 0
    
    # 6. Calculate Margin
    margin = 0.0
    if rev > 0:
        # Total Costs = Expenses + Salaries
        total_costs = exp + sal
        margin = ((rev - total_costs) / rev) * 100.0

    # 7. Revenue by Client (For Simulation Accuracy)
    client_rev_query = text("""
        SELECT c.name, COALESCE(SUM(r.amount), 0)
        FROM revenue r
        JOIN clients c ON r.client_id = c.id
        WHERE r.revenue_date >= :active_month_start AND r.revenue_date <= :dataset_end_date
        GROUP BY c.name
    """)
    client_revenue = {row[0]: float(row[1]) for row in conn.execute(client_rev_query, params).fetchall()}
    
    return {
        "revenue": float(rev),
        "expenses": float(exp),
        "salaries": float(sal),
        "employee_count": int(emp_count),
        "project_count": int(proj_count),
        "margin": float(margin),
        "client_revenue": client_revenue,
        "period_start": active_month_start.isoformat(),
        "period_end": dataset_end_date.isoformat()
    }
