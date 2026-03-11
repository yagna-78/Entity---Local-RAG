"""
SCENARIO SIMULATION ENGINE — Orchestrator

Parses user queries to detect scenario type, then dispatches to:
1. financial_engine.py — deterministic financial computation
2. operational_engine.py — project/capacity impact  
3. risk_engine.py — delivery/churn risk assessment

Returns a combined JSON result. NO financial math happens here.
The LLM only receives this JSON for humanization — it never computes.
"""

import re
import json
import logging
from typing import Dict, Optional
from sqlalchemy import text

import financial_engine
import operational_engine
import risk_engine

logger = logging.getLogger(__name__)


# ─── SCENARIO TYPE DETECTION ─────────────────────────────────

def detect_scenario(query: str) -> Dict:
    """
    Parses the natural language query to determine the scenario type
    and extract the target entity (employee name, client name, etc.)
    
    Returns: {"type": "fire_employee"|"hire_employee"|"cancel_client"|"general_what_if"|"unknown", "target": "..."}
    """
    q = query.lower()

    # ── Client Cancellation (checked BEFORE employee removal so "lose client" isn't misrouted) ──
    if any(kw in q for kw in ["cancel", "cancels", "cancelled", "lose client", "client leaves", "client cancel", "as a client"]):
        # Extract client name — multiple patterns for different phrasings
        client_patterns = [
            # "<client> cancels/cancelled our contract" — client name BEFORE verb
            r'(?:what (?:if|happens if)\s+)(.+?)\s+(?:cancels?|cancelled)\s+(?:our|the|their)\s+(?:contract|deal|agreement)',
            # "cancel/lose <client>" — verb BEFORE client name
            r'(?:cancel|cancels?|cancelled|lose|leaves?)\s+(?:client\s+)?(?:contract\s+with\s+)?(.+?)(?:\s*\?|$)',
            # "we lose <client> as a client" — explicit lose pattern
            r'(?:we\s+)?(?:lose|lost)\s+(.+?)(?:\s+as\s+|\s*\?|$)',
        ]
        for pattern in client_patterns:
            client_match = re.search(pattern, q)
            if client_match:
                target = client_match.group(1).strip().rstrip("?").strip()
                target = re.sub(r'\b(the|our|client|contract|if we)\b', '', target).strip()
                target = re.sub(r'\s+', ' ', target).strip()
                if target:
                    return {"type": "cancel_client", "target": target}

    # ── Employee Removal ──
    fire_patterns = [
        r"(?:fire|remove|let go|terminate|lose)\s+(?:our\s+)?(?:only\s+)?(.+?)(?:\s+from|\s+\?|$)",
        r"what (?:if|happens if) we (?:fire|remove|let go|terminate|lose)\s+(.+?)(?:\s*\?|$)",
        r"(?:fire|remove|let go)\s+(.+?)$",
    ]
    
    for pattern in fire_patterns:
        match = re.search(pattern, q)
        if match and any(kw in q for kw in ["fire", "remove", "let go", "terminate", "lose"]):
            target = match.group(1).strip().rstrip("?").strip()
            # Clean up noise words AND role titles
            noise = r'\b(the|our|an?|only|employee|engineer|developer|team member|devops|backend|frontend|fullstack|full stack|senior|junior|lead|manager|intern|designer|qa|tester|analyst|consultant|architect|admin|system admin|hr|marketing|sales|support|ops|operations|data|ml|ai|software|sre|cloud|mobile|ios|android|web)\b'
            target = re.sub(noise, '', target).strip()
            # Collapse multiple spaces
            target = re.sub(r'\s+', ' ', target).strip()
            if target:
                return {"type": "fire_employee", "target": target}

    # ── Employee Hiring ──
    if any(kw in q for kw in ["hire", "add employee", "recruit", "onboard"]):
        # Try to extract salary
        salary_match = re.search(r'(\d[\d,]*)\s*(?:per month|monthly|salary|/month)', q)
        salary = float(salary_match.group(1).replace(",", "")) if salary_match else 50000.0
        count_match = re.search(r'(\d+)\s*(?:new|more|additional)?\s*(?:employee|engineer|developer|people|hire)', q)
        count = int(count_match.group(1)) if count_match else 1
        return {"type": "hire_employee", "target": None, "salary": salary, "count": count}

    # ── Burn Rate / Runway / Sustainability ──
    burn_keywords = ["burn rate", "runway", "survive", "sustain", "last for", "enough cash", "enough money"]
    if any(kw in q for kw in burn_keywords):
        # Try to extract months
        months_match = re.search(r'(\d+)\s*(?:month|months)', q)
        months = int(months_match.group(1)) if months_match else 6  # default 6 months
        return {"type": "burn_rate", "target": None, "months": months}

    # ── General What-If (budget, revenue, expense changes) ──
    # Patterns: "X increases/decreases by Y%", "increase X by Y%", "X goes up/down by Y%"
    
    # Extract percentage
    pct_match = re.search(r'(\d+(?:\.\d+)?)\s*%', q)
    change_pct = float(pct_match.group(1)) if pct_match else None
    
    # Extract absolute amount (e.g., "by 50000", "add 1 lakh")
    abs_match = re.search(r'(?:by|add|increase|decrease)\s+(?:inr\s*)?(\d[\d,]*)\s*(?:inr|rupees)?', q)
    change_abs = float(abs_match.group(1).replace(",", "")) if abs_match and not pct_match else None
    
    # Determine direction (increase or decrease)
    is_decrease = any(kw in q for kw in ["decrease", "reduces", "reduce", "drop", "drops", "cut", "cuts", "falls", "fall", "lower", "decline"])
    
    # Extract the metric being changed
    metric_patterns = [
        (r'(marketing|software|rent|salary|salaries|infrastructure|cloud|saas|contractor)\s*(?:budget|cost|expense|spending)?', None),
        (r'(revenue|income|earnings)', None),
        (r'(expense|cost|budget|spending)\s*(?:for\s+)?(\w+)?', None),
        (r'(budget)\s+(?:for\s+)?(\w+)', None),
    ]
    
    metric = None
    for pattern, _ in metric_patterns:
        m = re.search(pattern, q)
        if m:
            metric = m.group(1).strip()
            # If there's a second group (e.g., "budget for marketing"), use it
            if m.lastindex and m.lastindex > 1 and m.group(2):
                metric = m.group(2).strip()
            break
    
    if metric and (change_pct is not None or change_abs is not None):
        if is_decrease and change_pct:
            change_pct = -change_pct
        if is_decrease and change_abs:
            change_abs = -change_abs
        return {
            "type": "general_what_if",
            "target": metric,
            "change_pct": change_pct,
            "change_abs": change_abs,
        }

    return {"type": "unknown", "target": None}


# ─── MAIN ORCHESTRATOR ───────────────────────────────────────

def run_scenario(conn, query: str) -> Dict:
    """
    Master orchestrator. Parses the query, dispatches to sub-engines,
    and returns a combined JSON structure ready for LLM humanization.
    
    The LLM NEVER computes anything — all numbers come from here.
    """
    scenario = detect_scenario(query)
    scenario_type = scenario["type"]
    target = scenario.get("target")

    logger.info(f"Scenario Detected: {scenario_type} | Target: {target}")

    if scenario_type == "fire_employee":
        if not target:
            return {"error": "Could not identify which employee to remove from the query."}

        # 1. Financial Impact (deterministic)
        financial = financial_engine.fire_employee(conn, target)
        if "error" in financial:
            return financial

        # 2. Operational Impact
        operational = operational_engine.operational_impact(conn, target)

        # 3. Risk Assessment
        risk = risk_engine.risk_assessment(operational)

        return {
            "scenario_type": "fire_employee",
            "target": target,
            "financial": financial,
            "operational": operational,
            "risk": risk,
        }

    elif scenario_type == "hire_employee":
        salary = scenario.get("salary", 50000.0)
        count = scenario.get("count", 1)

        financial = financial_engine.hire_employee(conn, salary, count)
        if "error" in financial:
            return financial

        return {
            "scenario_type": "hire_employee",
            "salary_per_hire": salary,
            "count": count,
            "financial": financial,
            "operational": None,
            "risk": None,
        }

    elif scenario_type == "cancel_client":
        if not target:
            return {"error": "Could not identify which client to cancel from the query."}

        financial = financial_engine.cancel_client(conn, target)
        if "error" in financial:
            return financial

        return {
            "scenario_type": "cancel_client",
            "target": target,
            "financial": financial,
            "operational": None,
            "risk": None,
        }

    elif scenario_type == "burn_rate":
        months = scenario.get("months", 6)
        result = financial_engine.burn_rate_analysis(conn, months_to_check=months)
        if "error" in result:
            return result
        return result

    elif scenario_type == "general_what_if":
        change_pct = scenario.get("change_pct")
        change_abs = scenario.get("change_abs")
        
        result = financial_engine.general_what_if(conn, target, change_pct=change_pct, change_abs=change_abs)
        if "error" in result:
            return result
        
        return result

    else:
        return {"error": "Could not determine the scenario type. Please specify a change like: 'increase marketing budget by 20%', 'fire/hire employee', or 'cancel client'."}
