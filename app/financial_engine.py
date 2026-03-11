"""
FINANCIAL ENGINE — Deterministic Financial Computation Layer

All financial math is executed here. NO LLM involvement.
Revenue changes ONLY via client/project events, NEVER via employee events.
"""

import logging
from sqlalchemy import text
from typing import Dict, Optional

logger = logging.getLogger(__name__)


# ─── SAFE MATH ───────────────────────────────────────────────

def safe_divide(a: float, b: float) -> Optional[float]:
    """Division-by-zero guard. Returns None instead of crashing."""
    if b == 0:
        return None
    return a / b


# ─── BASELINE FETCHER ────────────────────────────────────────

def get_baseline(conn) -> Dict:
    """Fetch current-month baseline metrics from the database."""
    try:
        import kpi_engine
    except ImportError:
        from app import kpi_engine
    return kpi_engine.get_baseline_metrics(conn)


# ─── EMPLOYEE SCENARIOS ──────────────────────────────────────

def fire_employee(conn, employee_name: str) -> Dict:
    """
    Simulate firing an employee. Revenue DOES NOT change.
    All numbers come from the database — nothing is invented.
    """
    baseline = get_baseline(conn)
    revenue = float(baseline["revenue"])
    expenses = float(baseline["expenses"])
    total_salary = float(baseline["salaries"])
    employee_count = int(baseline["employee_count"])

    # Fetch specific employee salary — try exact match first, then fuzzy
    row = conn.execute(
        text("SELECT name, monthly_salary FROM employees WHERE LOWER(name) = LOWER(:name) AND status = 'active'"),
        {"name": employee_name}
    ).fetchone()

    # Fuzzy fallback: partial name match
    if not row:
        row = conn.execute(
            text("SELECT name, monthly_salary FROM employees WHERE LOWER(name) ILIKE :pattern AND status = 'active' LIMIT 1"),
            {"pattern": f"%{employee_name.lower()}%"}
        ).fetchone()

    if not row:
        return {"error": f"Employee '{employee_name}' not found in the database."}

    matched_name = row[0]
    employee_salary = float(row[1])
    logger.info(f"Matched employee: {matched_name} (queried: {employee_name}) | Salary: {employee_salary}")

    # ── CAUSALITY LOCK: Revenue DOES NOT change ──
    new_revenue = revenue

    # Salary decreases
    new_total_salary = total_salary - employee_salary

    # Recalculate cost
    new_total_cost = expenses + new_total_salary
    new_employee_count = employee_count - 1

    # Safe math
    base_total_cost = expenses + total_salary
    base_margin = safe_divide((revenue - base_total_cost), revenue)
    base_margin = base_margin * 100 if base_margin is not None else None

    net_margin = safe_divide((new_revenue - new_total_cost), new_revenue)
    net_margin = net_margin * 100 if net_margin is not None else None

    salary_ratio = safe_divide(new_total_salary, new_revenue)
    salary_ratio = salary_ratio * 100 if salary_ratio is not None else None

    base_salary_ratio = safe_divide(total_salary, revenue)
    base_salary_ratio = base_salary_ratio * 100 if base_salary_ratio is not None else None

    revenue_per_employee = safe_divide(new_revenue, new_employee_count)
    base_rpe = safe_divide(revenue, employee_count)

    # ── REVENUE LOCK VALIDATION ──
    validate_revenue_lock("employee_change", revenue, new_revenue)

    return {
        "scenario_type": "fire_employee",
        "employee_name": employee_name,
        "baseline": {
            "revenue": revenue,
            "expenses": expenses,
            "salaries": total_salary,
            "total_cost": base_total_cost,
            "net_margin": round(base_margin, 2) if base_margin is not None else None,
            "salary_ratio": round(base_salary_ratio, 2) if base_salary_ratio is not None else None,
            "revenue_per_employee": round(base_rpe, 2) if base_rpe is not None else None,
            "employee_count": employee_count,
        },
        "simulated": {
            "revenue": new_revenue,
            "salary_saved": employee_salary,
            "new_total_salary": new_total_salary,
            "total_cost": new_total_cost,
            "net_margin": round(net_margin, 2) if net_margin is not None else None,
            "salary_ratio": round(salary_ratio, 2) if salary_ratio is not None else None,
            "revenue_per_employee": round(revenue_per_employee, 2) if revenue_per_employee is not None else None,
            "employee_count": new_employee_count,
        },
        "delta": {
            "salary_change": -employee_salary,
            "margin_change": round(net_margin - base_margin, 2) if (net_margin is not None and base_margin is not None) else None,
            "revenue_change": 0,
        }
    }


def hire_employee(conn, salary_per_hire: float, count: int = 1) -> Dict:
    """
    Simulate hiring employee(s). Revenue DOES NOT change.
    """
    baseline = get_baseline(conn)
    revenue = float(baseline["revenue"])
    expenses = float(baseline["expenses"])
    total_salary = float(baseline["salaries"])
    employee_count = int(baseline["employee_count"])

    # ── CAUSALITY LOCK: Revenue DOES NOT change ──
    new_revenue = revenue

    added_salary = salary_per_hire * count
    new_total_salary = total_salary + added_salary
    new_total_cost = expenses + new_total_salary
    new_employee_count = employee_count + count

    base_total_cost = expenses + total_salary
    base_margin = safe_divide((revenue - base_total_cost), revenue)
    base_margin = base_margin * 100 if base_margin is not None else None

    net_margin = safe_divide((new_revenue - new_total_cost), new_revenue)
    net_margin = net_margin * 100 if net_margin is not None else None

    salary_ratio = safe_divide(new_total_salary, new_revenue)
    salary_ratio = salary_ratio * 100 if salary_ratio is not None else None

    base_salary_ratio = safe_divide(total_salary, revenue)
    base_salary_ratio = base_salary_ratio * 100 if base_salary_ratio is not None else None

    revenue_per_employee = safe_divide(new_revenue, new_employee_count)
    base_rpe = safe_divide(revenue, employee_count)

    validate_revenue_lock("employee_change", revenue, new_revenue)

    return {
        "scenario_type": "hire_employee",
        "baseline": {
            "revenue": revenue,
            "expenses": expenses,
            "salaries": total_salary,
            "total_cost": base_total_cost,
            "net_margin": round(base_margin, 2) if base_margin is not None else None,
            "salary_ratio": round(base_salary_ratio, 2) if base_salary_ratio is not None else None,
            "revenue_per_employee": round(base_rpe, 2) if base_rpe is not None else None,
            "employee_count": employee_count,
        },
        "simulated": {
            "revenue": new_revenue,
            "added_salary": added_salary,
            "new_total_salary": new_total_salary,
            "total_cost": new_total_cost,
            "net_margin": round(net_margin, 2) if net_margin is not None else None,
            "salary_ratio": round(salary_ratio, 2) if salary_ratio is not None else None,
            "revenue_per_employee": round(revenue_per_employee, 2) if revenue_per_employee is not None else None,
            "employee_count": new_employee_count,
        },
        "delta": {
            "salary_change": added_salary,
            "margin_change": round(net_margin - base_margin, 2) if (net_margin is not None and base_margin is not None) else None,
            "revenue_change": 0,
        }
    }


# ─── CLIENT SCENARIOS ────────────────────────────────────────

def cancel_client(conn, client_name: str) -> Dict:
    """
    Simulate cancelling a client. Revenue DECREASES by client contribution.
    """
    baseline = get_baseline(conn)
    revenue = float(baseline["revenue"])
    expenses = float(baseline["expenses"])
    total_salary = float(baseline["salaries"])
    employee_count = int(baseline["employee_count"])
    client_revenue_map = baseline.get("client_revenue", {})

    # Find client revenue (case-insensitive match)
    client_rev = None
    matched_name = None
    for name, amount in client_revenue_map.items():
        if name.lower() == client_name.lower():
            client_rev = float(amount)
            matched_name = name
            break

    if client_rev is None:
        return {"error": f"Client '{client_name}' not found in revenue data."}

    # Revenue DECREASES
    new_revenue = revenue - client_rev
    if new_revenue < 0:
        new_revenue = 0

    total_cost = expenses + total_salary

    base_margin = safe_divide((revenue - total_cost), revenue)
    base_margin = base_margin * 100 if base_margin is not None else None

    new_margin = safe_divide((new_revenue - total_cost), new_revenue)
    new_margin = new_margin * 100 if new_margin is not None else None

    base_salary_ratio = safe_divide(total_salary, revenue)
    base_salary_ratio = base_salary_ratio * 100 if base_salary_ratio is not None else None

    new_salary_ratio = safe_divide(total_salary, new_revenue)
    new_salary_ratio = new_salary_ratio * 100 if new_salary_ratio is not None else None

    base_rpe = safe_divide(revenue, employee_count)
    new_rpe = safe_divide(new_revenue, employee_count)

    client_pct = safe_divide(client_rev, revenue)
    client_pct = client_pct * 100 if client_pct is not None else None

    return {
        "scenario_type": "cancel_client",
        "client_name": matched_name,
        "client_revenue": client_rev,
        "client_contribution_pct": round(client_pct, 2) if client_pct is not None else None,
        "baseline": {
            "revenue": revenue,
            "expenses": expenses,
            "salaries": total_salary,
            "total_cost": total_cost,
            "net_margin": round(base_margin, 2) if base_margin is not None else None,
            "salary_ratio": round(base_salary_ratio, 2) if base_salary_ratio is not None else None,
            "revenue_per_employee": round(base_rpe, 2) if base_rpe is not None else None,
            "employee_count": employee_count,
        },
        "simulated": {
            "revenue": new_revenue,
            "total_cost": total_cost,
            "net_margin": round(new_margin, 2) if new_margin is not None else None,
            "salary_ratio": round(new_salary_ratio, 2) if new_salary_ratio is not None else None,
            "revenue_per_employee": round(new_rpe, 2) if new_rpe is not None else None,
            "employee_count": employee_count,
        },
        "delta": {
            "revenue_change": -client_rev,
            "margin_change": round(new_margin - base_margin, 2) if (new_margin is not None and base_margin is not None) else None,
        }
    }


# ─── BURN RATE / RUNWAY ANALYSIS ─────────────────────────────

def burn_rate_analysis(conn, months_to_check: int = 6) -> Dict:
    """
    Deterministic burn rate and runway analysis.
    Computes actual monthly burn rate, revenue, and whether the company can sustain operations.
    """
    baseline = get_baseline(conn)
    revenue = float(baseline["revenue"])
    expenses = float(baseline["expenses"])
    total_salary = float(baseline["salaries"])
    employee_count = int(baseline["employee_count"])

    # Get monthly revenue breakdown from DB
    monthly_rev_rows = conn.execute(
        text("SELECT DATE_TRUNC('month', revenue_date) AS month, SUM(amount) AS total FROM revenue GROUP BY month ORDER BY month")
    ).fetchall()
    
    monthly_revenues = [float(r[1]) for r in monthly_rev_rows]
    num_revenue_months = len(monthly_revenues) if monthly_revenues else 1
    avg_monthly_revenue = sum(monthly_revenues) / num_revenue_months if monthly_revenues else 0
    
    # Get monthly expense breakdown from DB
    monthly_exp_rows = conn.execute(
        text("SELECT DATE_TRUNC('month', expense_date) AS month, SUM(amount) AS total FROM expenses GROUP BY month ORDER BY month")
    ).fetchall()
    
    monthly_expenses = [float(r[1]) for r in monthly_exp_rows]
    num_expense_months = len(monthly_expenses) if monthly_expenses else 1
    avg_monthly_expenses = sum(monthly_expenses) / num_expense_months if monthly_expenses else 0
    
    # Monthly burn = avg expenses + monthly salaries
    monthly_burn = avg_monthly_expenses + total_salary
    
    # Net monthly cash flow
    monthly_net = avg_monthly_revenue - monthly_burn
    
    # Projected over requested period
    projected_revenue = avg_monthly_revenue * months_to_check
    projected_burn = monthly_burn * months_to_check
    projected_net = projected_revenue - projected_burn
    
    # Runway: how many months can the company operate
    # If profitable (net > 0), runway is infinite. If burning cash, calculate how long.
    if monthly_net >= 0:
        runway_months = None  # Sustainable - infinite runway
        can_survive = True
    else:
        # With continuous losses, how long before cumulative loss becomes critical
        runway_months = None  # No reserve data available
        can_survive = False
    
    # Margin
    margin = safe_divide(monthly_net, avg_monthly_revenue)
    margin_pct = margin * 100 if margin is not None else None
    
    return {
        "scenario_type": "burn_rate_analysis",
        "months_analyzed": num_revenue_months,
        "months_requested": months_to_check,
        "monthly": {
            "avg_revenue": round(avg_monthly_revenue, 2),
            "avg_expenses": round(avg_monthly_expenses, 2),
            "salary_cost": round(total_salary, 2),
            "total_burn_rate": round(monthly_burn, 2),
            "net_cash_flow": round(monthly_net, 2),
            "net_margin_pct": round(margin_pct, 2) if margin_pct is not None else None,
        },
        "projected": {
            "period_months": months_to_check,
            "total_revenue": round(projected_revenue, 2),
            "total_burn": round(projected_burn, 2),
            "net_position": round(projected_net, 2),
        },
        "assessment": {
            "can_survive": can_survive,
            "monthly_surplus_or_deficit": round(monthly_net, 2),
            "is_profitable": monthly_net > 0,
            "employee_count": employee_count,
        },
        "revenue_breakdown_monthly": [
            {"month": str(r[0])[:7], "revenue": float(r[1])} for r in monthly_rev_rows
        ],
    }


# ─── GENERAL WHAT-IF SCENARIOS ───────────────────────────────

def general_what_if(conn, metric: str, change_pct: float = None, change_abs: float = None) -> Dict:
    """
    Simulate a general what-if scenario for any financial metric.
    
    Args:
        conn: Database connection
        metric: What is changing — 'revenue', 'expenses', 'salaries', or an expense category like 'marketing', 'software', 'rent'
        change_pct: Percentage change (e.g., 20 means +20%, -10 means -10%)
        change_abs: Absolute change in INR (overrides change_pct if both provided)
    """
    baseline = get_baseline(conn)
    revenue = float(baseline["revenue"])
    expenses = float(baseline["expenses"])
    total_salary = float(baseline["salaries"])
    employee_count = int(baseline["employee_count"])
    total_cost = expenses + total_salary

    metric_lower = metric.lower().strip()
    
    # Determine current value and which component changes
    current_value = 0
    affected_component = "expenses"  # default
    
    if metric_lower in ["revenue", "total revenue", "income"]:
        current_value = revenue
        affected_component = "revenue"
    elif metric_lower in ["expenses", "total expenses", "total cost", "costs"]:
        current_value = expenses
        affected_component = "expenses"
    elif metric_lower in ["salary", "salaries", "payroll", "salary cost"]:
        current_value = total_salary
        affected_component = "salaries"
    else:
        # Try to match an expense category from the database
        row = conn.execute(
            text("SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE LOWER(category) ILIKE :cat"),
            {"cat": f"%{metric_lower}%"}
        ).fetchone()
        if row and float(row[0]) > 0:
            current_value = float(row[0])
            affected_component = f"expenses ({metric})"
        else:
            # Fallback: treat as general expense
            current_value = expenses
            affected_component = "expenses"
    
    # Calculate the change amount
    if change_abs is not None:
        change_amount = change_abs
    elif change_pct is not None:
        change_amount = current_value * (change_pct / 100.0)
    else:
        return {"error": "No change amount specified."}
    
    new_value = current_value + change_amount
    
    # Calculate new totals
    if affected_component == "revenue":
        new_revenue = new_value
        new_expenses = expenses
        new_salary = total_salary
    elif affected_component == "salaries":
        new_revenue = revenue
        new_expenses = expenses
        new_salary = new_value
    else:
        # Expense category or total expenses
        new_revenue = revenue
        new_expenses = expenses + change_amount  # Add the change to total expenses
        new_salary = total_salary
    
    new_total_cost = new_expenses + new_salary
    
    # Margins
    base_margin = safe_divide((revenue - total_cost), revenue)
    base_margin = base_margin * 100 if base_margin is not None else None
    
    new_margin = safe_divide((new_revenue - new_total_cost), new_revenue)
    new_margin = new_margin * 100 if new_margin is not None else None
    
    base_rpe = safe_divide(revenue, employee_count)
    new_rpe = safe_divide(new_revenue, employee_count)
    
    return {
        "scenario_type": "general_what_if",
        "description": f"{'Increase' if change_amount > 0 else 'Decrease'} {metric} by {abs(change_pct) if change_pct else abs(change_amount)}{'%' if change_pct else ' INR'}",
        "metric_changed": metric,
        "affected_component": affected_component,
        "baseline": {
            "revenue": revenue,
            "expenses": expenses,
            "salaries": total_salary,
            "total_cost": total_cost,
            "metric_current_value": current_value,
            "net_margin": round(base_margin, 2) if base_margin is not None else None,
            "revenue_per_employee": round(base_rpe, 2) if base_rpe is not None else None,
            "employee_count": employee_count,
        },
        "simulated": {
            "revenue": new_revenue,
            "expenses": new_expenses,
            "salaries": new_salary,
            "total_cost": new_total_cost,
            "metric_new_value": new_value,
            "change_amount": round(change_amount, 2),
            "net_margin": round(new_margin, 2) if new_margin is not None else None,
            "revenue_per_employee": round(new_rpe, 2) if new_rpe is not None else None,
            "employee_count": employee_count,
        },
        "delta": {
            "cost_change": round(new_total_cost - total_cost, 2),
            "revenue_change": round(new_revenue - revenue, 2),
            "margin_change": round(new_margin - base_margin, 2) if (new_margin is not None and base_margin is not None) else None,
        }
    }


# ─── REVENUE LOCK VALIDATOR ──────────────────────────────────

def validate_revenue_lock(scenario_type: str, original_revenue: float, new_revenue: float):
    """
    IMMUTABLE GUARD: For employee-change scenarios, revenue must NOT change.
    If violated, raises an exception to abort execution.
    """
    if scenario_type == "employee_change":
        if new_revenue != original_revenue:
            raise ValueError("Revenue corruption detected. Employee events cannot modify revenue.")
