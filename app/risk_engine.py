"""
RISK ENGINE — Risk Assessment Layer

Takes operational output and classifies delivery and churn risk levels.
Pure deterministic logic — no LLM involvement.
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


def risk_assessment(operational_output: Dict) -> Dict:
    """
    Assesses delivery and churn risk based on operational impact data.
    """
    capacity_drop = operational_output.get("capacity_drop_pct", 0)
    overload_risk = operational_output.get("overload_risk", 0)
    role = operational_output.get("role", "Unknown")
    affected_projects = operational_output.get("affected_projects", [])

    # ── Delivery Risk ──
    if capacity_drop == 100:
        delivery_risk = "Severe"
        delivery_detail = f"Complete loss of {role} function. All {len(affected_projects)} assigned project(s) at risk."
    elif capacity_drop >= 50:
        delivery_risk = "High"
        delivery_detail = f"{capacity_drop}% capacity reduction in {role} function."
    elif capacity_drop >= 25:
        delivery_risk = "Moderate"
        delivery_detail = f"{capacity_drop}% capacity reduction. Workload redistribution required."
    else:
        delivery_risk = "Low"
        delivery_detail = f"Minimal capacity impact ({capacity_drop}%)."

    # ── Churn Risk (remaining team overload) ──
    if overload_risk > 120:
        churn_risk = "Critical"
        churn_detail = f"Remaining team at {overload_risk}% utilization. Burnout imminent."
    elif overload_risk > 100:
        churn_risk = "High"
        churn_detail = f"Team utilization at {overload_risk}%. Overtime required."
    elif overload_risk > 80:
        churn_risk = "Elevated"
        churn_detail = f"Team utilization at {overload_risk}%. Approaching overload."
    else:
        churn_risk = "Controlled"
        churn_detail = f"Team utilization at {overload_risk}%. Within safe limits."

    # ── SLA Risk ──
    sla_risk = "Low"
    if len(affected_projects) > 2 and capacity_drop >= 50:
        sla_risk = "High"
    elif len(affected_projects) > 0 and capacity_drop >= 25:
        sla_risk = "Moderate"

    return {
        "delivery_risk": delivery_risk,
        "delivery_detail": delivery_detail,
        "churn_risk": churn_risk,
        "churn_detail": churn_detail,
        "sla_risk": sla_risk,
        "affected_project_count": len(affected_projects),
    }


# ─── DASHBOARD RISK PROFILE (for /risk endpoint) ────────────

def calculate_risk_profile(kpi_dict: Dict) -> Dict:
    """
    Calculates weighted risk scores for the dashboard.
    Used by api_routes.py /risk endpoint.
    """
    net_margin = kpi_dict.get("net_margin", kpi_dict.get("net_profit_margin", 0))
    salary_ratio = kpi_dict.get("salary_ratio", 0)
    on_time = kpi_dict.get("on_time_delivery", 100)
    churn_idx = kpi_dict.get("churn_risk_index", 0)
    runway = kpi_dict.get("runway_months", 999)
    rev_concentration = kpi_dict.get("revenue_concentration", 0)

    # Financial Risk (0-100)
    financial_score = 0
    if net_margin < 10:
        financial_score += 40
    elif net_margin < 20:
        financial_score += 20
    if salary_ratio > 70:
        financial_score += 30
    elif salary_ratio > 50:
        financial_score += 15
    if runway < 6:
        financial_score += 30
    elif runway < 12:
        financial_score += 15

    # Operational Risk (0-100)
    ops_score = 0
    if on_time < 60:
        ops_score += 50
    elif on_time < 80:
        ops_score += 25
    if churn_idx > 50:
        ops_score += 50
    elif churn_idx > 30:
        ops_score += 25

    # Client Risk (0-100)
    client_score = 0
    if rev_concentration > 50:
        client_score += 60
    elif rev_concentration > 30:
        client_score += 30

    # Overall
    overall = round((financial_score * 0.4 + ops_score * 0.35 + client_score * 0.25), 1)

    def level(score):
        if score >= 60:
            return "Critical"
        elif score >= 40:
            return "High"
        elif score >= 20:
            return "Moderate"
        return "Low"

    return {
        "financial": {"score": financial_score, "level": level(financial_score)},
        "operational": {"score": ops_score, "level": level(ops_score)},
        "client": {"score": client_score, "level": level(client_score)},
        "overall": {"score": overall, "level": level(overall)},
    }
