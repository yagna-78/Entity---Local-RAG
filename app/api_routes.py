
import os
import sys
import logging

# Ensure the app directory is on the Python path so bare imports work
# e.g. 'from database import engine' resolves to 'app/database.py'
_app_dir = os.path.dirname(os.path.abspath(__file__))
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import text
from typing import List
from pydantic import BaseModel

from database import engine
import kpi_engine
import simulation_engine as scenario_orchestrator
import financial_engine
import risk_engine

try:
    from forecasting_engine import ForecastingEngine
except ImportError:
    ForecastingEngine = None

try:
    from executive_summary import ExecutiveSummaryGenerator
except ImportError:
    ExecutiveSummaryGenerator = None

try:
    from insight_engine import InsightEngine
except ImportError:
    InsightEngine = None

router = APIRouter()
logger = logging.getLogger(__name__)

# --- Models ---
class SimulationRequest(BaseModel):
    revenue_pct_change: float = 0.0
    salary_pct_change: float = 0.0
    clients_removed: List[str] = []
    new_employees: int = 0
    salary_per_hire: float = 0.0 # Added field
    marketing_spend_increase: float = 0.0

# --- Dashboard Data Endpoints ---

@router.get("/dashboard/revenue")
async def get_dashboard_revenue():
    """
    Returns current month revenue total and breakdown by source/client.
    """
    try:
        with engine.connect() as conn:
            end_date, start_date = kpi_engine.get_dataset_dates(conn)
            params = {"start": start_date, "end": end_date}
            
            total_rev = conn.execute(text("""
                SELECT COALESCE(SUM(amount), 0) 
                FROM revenue 
                WHERE revenue_date >= :start AND revenue_date <= :end
            """), params).scalar()
            
            breakdown = conn.execute(text("""
                SELECT c.name, COALESCE(SUM(r.amount), 0) as amount
                FROM revenue r
                JOIN clients c ON r.client_id = c.id
                WHERE r.revenue_date >= :start AND r.revenue_date <= :end
                GROUP BY c.name
                ORDER BY amount DESC
            """), params).fetchall()
            
            return {
                "period": f"{start_date} to {end_date}",
                "total_revenue": float(total_rev),
                "breakdown": [{"source": row[0], "amount": float(row[1])} for row in breakdown]
            }
    except Exception as e:
        logger.error(f"Revenue Dashboard Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/team")
async def get_dashboard_team():
    """
    Returns employee list with roles and active project assignments.
    """
    try:
        with engine.connect() as conn:
            employees = conn.execute(text("""
                SELECT e.id, e.name, e.role, e.monthly_salary
                FROM employees e
                ORDER BY e.name
            """)).fetchall()
            
            team_data = []
            for emp in employees:
                projects = conn.execute(text("""
                    SELECT p.project_name
                    FROM project_assignments pa
                    JOIN projects p ON pa.project_id = p.id
                    WHERE pa.employee_id = :eid AND p.status IN ('in_progress', 'ongoing', 'active', 'delayed')
                """), {"eid": emp[0]}).fetchall()
                
                team_data.append({
                    "name": emp[1],
                    "role": emp[2],
                    "projects": [{"name": p[0]} for p in projects]
                })
                
            return {"team": team_data}
    except Exception as e:
        logger.error(f"Team Dashboard Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/expenses")
async def get_dashboard_expenses():
    """
    Returns current month expense total and breakdown by category.
    """
    try:
        with engine.connect() as conn:
            end_date, start_date = kpi_engine.get_dataset_dates(conn)
            params = {"start": start_date, "end": end_date}
            
            total_exp = conn.execute(text("""
                SELECT COALESCE(SUM(amount), 0) 
                FROM expenses 
                WHERE expense_date >= :start AND expense_date <= :end
            """), params).scalar()
            
            breakdown = conn.execute(text("""
                SELECT category, COALESCE(SUM(amount), 0) as amount
                FROM expenses
                WHERE expense_date >= :start AND expense_date <= :end
                GROUP BY category
                ORDER BY amount DESC
            """), params).fetchall()
            
            return {
                "period": f"{start_date} to {end_date}",
                "total_expenses": float(total_exp),
                "breakdown": [{"category": row[0], "amount": float(row[1])} for row in breakdown]
            }
    except Exception as e:
        logger.error(f"Expense Dashboard Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/projects")
async def get_dashboard_projects():
    """
    Returns active projects and their clients.
    """
    try:
        with engine.connect() as conn:
            projects = conn.execute(text("""
                SELECT p.project_name, c.name as client, p.status, p.deadline
                FROM projects p
                JOIN clients c ON p.client_id = c.id
                WHERE p.status IN ('in_progress', 'ongoing', 'active', 'delayed')
                ORDER BY p.deadline ASC
            """)).fetchall()
            
            return {
                "active_projects": [
                    {
                        "name": row[0], 
                        "client": row[1], 
                        "deadline": row[3].isoformat() if row[3] else "No Deadline"
                    } 
                    for row in projects
                ]
            }
    except Exception as e:
        logger.error(f"Project Dashboard Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Portfolio Mode Endpoints ---

@router.post("/simulate")
async def run_simulation(request: SimulationRequest):
    """
    Runs an in-memory simulation based on provided deltas.
    All parameters are applied together in a single pass so that
    combined changes (e.g. revenue + new hires) are reflected correctly.
    """
    try:
        with engine.connect() as conn:
            baseline_data = kpi_engine.get_baseline_metrics(conn)

            # --- If client removal is involved, delegate to deterministic engine ---
            if request.clients_removed:
                raw_result = financial_engine.cancel_client(conn, request.clients_removed[0])
            else:
                # --- Unified simulation: apply ALL params together ---
                rev = baseline_data["revenue"]
                sal = baseline_data["salaries"]
                exp = baseline_data["expenses"]
                emp = baseline_data["employee_count"]

                # 1. Revenue change (percentage)
                new_rev = rev * (1 + request.revenue_pct_change / 100)

                # 2. Salary change (percentage on existing salaries)
                new_sal = sal * (1 + request.salary_pct_change / 100)

                # 3. New hires (additive salary)
                new_emp = emp + request.new_employees
                if request.new_employees > 0:
                    hire_salary = (request.salary_per_hire or 50000.0) * request.new_employees
                    new_sal += hire_salary

                # 4. Marketing spend increase (additive to expenses)
                new_exp = exp + request.marketing_spend_increase

                # 5. Derived metrics
                base_total_cost = exp + sal
                new_total_cost = new_exp + new_sal

                base_margin = financial_engine.safe_divide((rev - base_total_cost), rev)
                base_margin = round(base_margin * 100, 2) if base_margin is not None else None

                margin = financial_engine.safe_divide((new_rev - new_total_cost), new_rev)
                margin = round(margin * 100, 2) if margin is not None else None

                raw_result = {
                    "scenario_type": "combined_simulation",
                    "baseline": {
                        "revenue": rev, "salaries": sal, "expenses": exp,
                        "net_margin": base_margin, "employee_count": emp,
                    },
                    "simulated": {
                        "revenue": round(new_rev, 2), "salaries": round(new_sal, 2),
                        "expenses": round(new_exp, 2), "total_cost": round(new_total_cost, 2),
                        "net_margin": margin, "employee_count": new_emp,
                    },
                }

        if "error" in raw_result:
             raise HTTPException(status_code=500, detail=raw_result["error"])

        # Normalize response: ensure frontend-expected keys (revenue, net_margin, employees) exist
        b = raw_result.get("baseline", {})
        s = raw_result.get("simulated", {})
        result = {
            **raw_result,
            "baseline": {
                **b,
                "revenue": b.get("revenue", 0),
                "net_margin": b.get("net_margin", b.get("margin", 0)),
                "employees": b.get("employee_count", b.get("employees", 0)),
            },
            "simulated": {
                **s,
                "revenue": s.get("revenue", 0),
                "net_margin": s.get("net_margin", s.get("margin", 0)),
                "employees": s.get("employee_count", s.get("employees", 0)),
            },
        }
        return result

    except Exception as e:
        logger.error(f"Simulation Endpoint Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/forecast")
async def get_forecast():
    """
    PHASE 2: 3-Month Financial Projection & Runway Analysis.
    """
    try:
        with engine.connect() as conn:
            result = ForecastingEngine.generate_forecast(conn)
            
        if "error" in result:
             raise HTTPException(status_code=500, detail=result["error"])
             
        return result
        
    except Exception as e:
        logger.error(f"Forecast Endpoint Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/risk")
async def get_risk_profile():
    """
    PHASE 4: Returns Weighted Risk Scores (Financial, Ops, Client).
    """
    try:
        with engine.connect() as conn:
            baseline = kpi_engine.get_baseline_metrics(conn)
            
            kpi_dict = {}
            results = conn.execute(text("""
                SELECT d.kpi_code, r.actual_value
                FROM kpi_results r
                JOIN kpi_definitions d ON r.kpi_id = d.id
                WHERE r.calculated_at = (SELECT MAX(calculated_at) FROM kpi_results r2 WHERE r2.kpi_id = r.kpi_id)
            """)).fetchall()
            
            for row in results:
                kpi_dict[row[0].lower()] = float(row[1])
            
            kpi_dict["net_margin"] = kpi_dict.get("net_profit_margin", baseline.get("margin", 0))
            
            if "runway_months" not in kpi_dict:
                 total_rev = float(conn.execute(text("SELECT COALESCE(SUM(amount), 0) FROM revenue")).scalar() or 0)
                 total_exp = float(conn.execute(text("SELECT COALESCE(SUM(amount), 0) FROM expenses")).scalar() or 0)
                 cash = (total_rev - total_exp) * 0.2
                 burn = max(0, baseline['expenses'] + baseline['salaries'] - baseline['revenue'])
                 kpi_dict["runway_months"] = cash / burn if burn > 0 else 999
            
            profile = risk_engine.calculate_risk_profile(kpi_dict)
            return profile
            
    except Exception as e:
        logger.error(f"Risk Endpoint Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summary")
async def get_executive_summary():
    """
    PHASE 3: Returns 4-point Executive Narrative.
    """
    try:
        with engine.connect() as conn:
             kpi_dict = {}
             results = conn.execute(text("""
                SELECT d.kpi_code, r.actual_value
                FROM kpi_results r
                JOIN kpi_definitions d ON r.kpi_id = d.id
                WHERE r.calculated_at = (SELECT MAX(calculated_at) FROM kpi_results r2 WHERE r2.kpi_id = r.kpi_id)
             """)).fetchall()
             for row in results: kpi_dict[row[0].lower()] = float(row[1])
             
             baseline = kpi_engine.get_baseline_metrics(conn)
             kpi_dict["net_margin"] = kpi_dict.get("net_profit_margin", baseline.get("margin", 0))
             
             if "runway_months" not in kpi_dict:
                 total_rev = float(conn.execute(text("SELECT COALESCE(SUM(amount), 0) FROM revenue")).scalar() or 0)
                 total_exp = float(conn.execute(text("SELECT COALESCE(SUM(amount), 0) FROM expenses")).scalar() or 0)
                 cash = (total_rev - total_exp) * 0.2
                 burn = max(0, baseline['expenses'] + baseline['salaries'] - baseline['revenue'])
                 kpi_dict["runway_months"] = cash / burn if burn > 0 else 999
                 
             raw_risk = risk_engine.calculate_risk_profile(kpi_dict)
             forecast = {} 
             
             # Transform risk_engine output to the format ExecutiveSummaryGenerator expects
             risk_profile = {
                 "breakdown": {
                     "financial_risk": raw_risk["financial"]["score"],
                     "operational_risk": raw_risk["operational"]["score"],
                     "client_risk": raw_risk["client"]["score"],
                 },
                 "factors": {
                     "margin": kpi_dict.get("net_margin", kpi_dict.get("net_profit_margin", 0)),
                     "runway": kpi_dict.get("runway_months", 999),
                     "utilization": kpi_dict.get("employee_utilization", 0),
                     "concentration": kpi_dict.get("revenue_concentration", 0),
                 }
             }
             
             summary = ExecutiveSummaryGenerator.generate_summary(risk_profile, forecast)
             return summary

    except Exception as e:
        logger.error(f"Summary Endpoint Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/insights")
async def get_insights():
    """
    PHASE 5: Autonomous Insight Engine.
    Returns structured list of warnings, root causes, and solutions.
    """
    try:
        with engine.connect() as conn:
            # 1. Fetch Latest KPIs
            kpi_dict = {}
            results = conn.execute(text("""
                SELECT d.kpi_code, r.actual_value
                FROM kpi_results r
                JOIN kpi_definitions d ON r.kpi_id = d.id
                WHERE r.calculated_at = (SELECT MAX(calculated_at) FROM kpi_results r2 WHERE r2.kpi_id = r.kpi_id)
            """)).fetchall()
            
            for row in results:
                kpi_dict[row[0].lower()] = float(row[1])
            
            # 2. Run Insight Engine
            insights = InsightEngine.generate_insights(kpi_dict)
            
            return insights

    except Exception as e:
        logger.error(f"Insight Engine Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
