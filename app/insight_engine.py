import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class InsightEngine:
    """
    system UPGRADE: AUTONOMOUS INSIGHT ENGINE
    
    Responsibilities:
    1. Scan KPIs against thresholds (Phase 1).
    2. Map to Root Causes deterministically (Phase 2).
    3. Attach predefined solutions (Phase 3).
    4. Score severity (Phase 4).
    5. Return structured JSON (Phase 5).
    """

    @staticmethod
    def generate_insights(kpis: Dict[str, Any]) -> List[Dict[str, Any]]:
        insights = []
        
        # --- PHASE 1 & 2: SCAN & ROOT CAUSE MAPPING ---
        
        # 1. Revenue Concentration
        concentration = float(kpis.get("revenue_concentration", 0))
        if concentration > 70:
            insights.append({
                "issue": "Client Dependency Risk",
                "severity": "High",
                "root_cause": "Client Dependency",
                "financial_impact": "High Risk of Revenue Collapse",
                "recommended_action": [
                    "Diversify vertical mix",
                    "Acquire 2 new mid-size clients"
                ]
            })

        # 2. Employee Utilization
        utilization = float(kpis.get("employee_utilization", 0))
        if utilization > 110:
             insights.append({
                "issue": "Overload Risk",
                "severity": "Medium",
                "root_cause": "Resource Overload",
                "financial_impact": "Potential Churn & Quality Drop",
                "recommended_action": [
                    "Hire additional engineer",
                    "Rebalance assignments"
                ]
            })

        # 3. On-Time Delivery
        otd = float(kpis.get("on_time_delivery", 100))
        if otd < 80:
             insights.append({
                "issue": "Execution Risk",
                "severity": "High",
                "root_cause": "Operational Execution Failure",
                "financial_impact": "SLA Penalties & Reputation Loss",
                "recommended_action": [
                    "Introduce milestone reviews",
                    "Add QA buffer"
                ]
            })
            
        # 4. Escalation Frequency
        escalations = float(kpis.get("escalation_frequency", 0))
        if escalations > 3:
             insights.append({
                "issue": "Process Breakdown Risk",
                "severity": "Medium",
                "root_cause": "Process Breakdown",
                "financial_impact": "Increased Support Costs",
                "recommended_action": [
                    "Review support protocols",
                    "Implement early warning system"
                ]
            })

        # 5. Churn Risk
        churn_risk = float(kpis.get("churn_risk_index", 0))
        if churn_risk > 30:
             insights.append({
                "issue": "Retention Risk",
                "severity": "Critical",
                "root_cause": "Client Dissatisfaction",
                "financial_impact": "Direct Revenue Loss",
                "recommended_action": [
                    "Deploy retention taskforce",
                    "Schedule executive check-in"
                ]
            })

        # --- PHASE 4: SEVERITY SCORING ---
        # Severity = Weighted Average of Risk Factors (Global Context)
        # However, for specific insights, we can assign intrinsic severity based on the rule.
        
        # Sort by severity implicitly or leave as a list since severity_score is removed.
        
        return insights
