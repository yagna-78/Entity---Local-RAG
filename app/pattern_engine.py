import logging
import json
from datetime import datetime
from typing import List, Dict, Any
from decimal import Decimal
from sqlalchemy import text
from database import engine

logger = logging.getLogger(__name__)

# Helper for JSON serialization
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

class PatternEngine:
    """
    Deterministic Pattern Recognition Engine.
    Identifies structural risks from database signals without LLM hallucination.
    """

    def __init__(self):
        pass

    def run_analysis(self) -> List[Dict[str, Any]]:
        """
        Runs all pattern checks and returns detected patterns.
        Also logs them to the database.
        """
        detected_patterns = []
        
        # 1. Escalation Risk
        escalations = self.detect_escalation_risk()
        detected_patterns.extend(escalations)

        # 2. Revenue Concentration
        concentration = self.detect_revenue_concentration()
        detected_patterns.extend(concentration)

        # 3. Overload Risk
        overload = self.detect_overload_risk()
        detected_patterns.extend(overload)

        # 4. Churn Risk
        churn = self.detect_churn_risk()
        detected_patterns.extend(churn)

        # 5. Governance Breakdown
        governance = self.detect_governance_breakdown()
        detected_patterns.extend(governance)

        # Log to DB
        self._log_patterns(detected_patterns)

        return detected_patterns

    def _execute_query(self, query: str) -> List[Dict]:
        """Helper to run raw SQL."""
        try:
            with engine.connect() as conn:
                result = conn.execute(text(query))
                keys = result.keys()
                return [dict(zip(keys, row)) for row in result.fetchall()]
        except Exception as e:
            logger.error(f"Pattern Query Failed: {e}")
            return []

    def detect_escalation_risk(self) -> List[Dict]:
        """
        Trigger: Budget overrun > 15%, delayed status.
        """
        sql = """
        SELECT id, project_name, actual_cost, estimated_budget, status 
        FROM projects 
        WHERE (actual_cost > estimated_budget * 1.15) 
           OR (status = 'Delayed')
        """
        rows = self._execute_query(sql)
        patterns = []
        for row in rows:
            overrun_pct = 0
            if row['estimated_budget'] and row['estimated_budget'] > 0:
                overrun_pct = ((row['actual_cost'] - row['estimated_budget']) / row['estimated_budget']) * 100
            
            patterns.append({
                "pattern": "Escalation Risk",
                "project_id": row['id'],
                "confidence": 85 if overrun_pct > 15 else 60,
                "severity_score": int(overrun_pct / 10) + 1,
                "trigger_signals": {
                    "project_name": row['project_name'],
                    "budget_overrun_pct": round(overrun_pct, 1),
                    "status": row['status']
                }
            })
        return patterns

    def detect_revenue_concentration(self) -> List[Dict]:
        """
        Trigger: One vertical > 60% of total revenue.
        """
        # Calculate total revenue
        total_rev_sql = "SELECT SUM(amount) as total FROM revenue"
        total_rows = self._execute_query(total_rev_sql)
        total_rev = total_rows[0]['total'] if total_rows and total_rows[0]['total'] else 0
        
        if total_rev == 0:
            return []

        # Revenue by Industry
        sql = """
        SELECT c.industry, SUM(r.amount) as industry_rev
        FROM revenue r
        JOIN clients c ON r.client_id = c.id
        GROUP BY c.industry
        """
        rows = self._execute_query(sql)
        patterns = []
        
        for row in rows:
            share_pct = (row['industry_rev'] / total_rev) * 100
            if share_pct > 60:
                patterns.append({
                    "pattern": "Revenue Concentration Risk",
                    "project_id": None, # Organization level
                    "confidence": 95,
                    "severity_score": 8,
                    "trigger_signals": {
                        "industry": row['industry'],
                        "revenue_share_pct": round(share_pct, 1)
                    }
                })
        return patterns

    def detect_overload_risk(self) -> List[Dict]:
        """
        Trigger: hours_logged > hours_allocated by > 15% across projects.
        """
        sql = """
        SELECT e.name, pa.project_id, pa.hours_logged, pa.hours_allocated
        FROM project_assignments pa
        JOIN employees e ON pa.employee_id = e.id
        WHERE pa.hours_logged > pa.hours_allocated * 1.15
        """
        rows = self._execute_query(sql)
        
        # Aggregate by employee to see if it's systemic (2+ projects) -- Simplified for now to just catch the instance
        patterns = []
        for row in rows:
             over_pct = ((row['hours_logged'] - row['hours_allocated']) / row['hours_allocated']) * 100
             patterns.append({
                "pattern": "Overload Risk",
                "project_id": row['project_id'],
                "confidence": 80,
                "severity_score": 5,
                "trigger_signals": {
                    "employee": row['name'],
                    "over_allocation_pct": round(over_pct, 1)
                }
            })
        return patterns

    def detect_churn_risk(self) -> List[Dict]:
        """
        Trigger: Client rating <= 2.
        """
        sql = """
        SELECT cf.project_id, c.name, cf.rating, cf.feedback_text
        FROM client_feedback cf
        JOIN clients c ON cf.client_id = c.id
        WHERE cf.rating <= 2
        """
        rows = self._execute_query(sql)
        patterns = []
        for row in rows:
            patterns.append({
                "pattern": "Churn Risk",
                "project_id": row['project_id'],
                "confidence": 90,
                "severity_score": 9,
                "trigger_signals": {
                    "client": row['name'],
                    "rating": row['rating'],
                    "feedback": row['feedback_text'][:50] + "..."
                }
            })
        return patterns

    def detect_governance_breakdown(self) -> List[Dict]:
        """
        Trigger: Missed deadlines (status=Delayed) AND low completion rate logic if we had tasks. 
        Simplified: Check for projects past deadline that are not 'Completed'.
        """
        sql = """
        SELECT id, project_name, deadline, status
        FROM projects
        WHERE deadline < CURRENT_DATE 
          AND status NOT IN ('Completed', 'Done', 'Delivered')
        """
        rows = self._execute_query(sql)
        patterns = []
        for row in rows:
            patterns.append({
                "pattern": "Governance Breakdown",
                "project_id": row['id'],
                "confidence": 75,
                "severity_score": 6,
                "trigger_signals": {
                    "project": row['project_name'],
                    "issue": "Past deadline but not complete",
                    "status": row['status']
                }
            })
        return patterns

    def _log_patterns(self, patterns: List[Dict]):
        """
        Inserts detected patterns into the database.
        Checks for duplicates (simple time-window or ID detection could be added, 
        but for now we log events as they occur in analysis).
        """
        if not patterns:
            return

        with engine.connect() as conn:
            for p in patterns:
                # Optional: Check if we recently logged this for this project to avoid spam
                # For this implementation, we just insert.
                
                insert_sql = text("""
                INSERT INTO pattern_events (pattern_name, project_id, detected_signals, severity_score)
                VALUES (:name, :pid, :signals, :score)
                """)
                
                conn.execute(insert_sql, {
                    "name": p['pattern'],
                    "pid": p['project_id'],
                    "signals": json.dumps(p['trigger_signals'], cls=DecimalEncoder),
                    "score": p['severity_score']
                })
            conn.commit()
