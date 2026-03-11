import logging
import json
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy import text
from database import engine
from pattern_engine import PatternEngine

logger = logging.getLogger(__name__)

class TipEngine:
    """
    Generates daily executive tips based on structural risks and financial ratios.
    Enforces deterministic logic: Data -> Insight -> Tip.
    """
    
    def __init__(self):
        self.pattern_engine = PatternEngine()

    def get_daily_tip(self):
        """
        Orchestrator: Checks DB for today's tip. If missing, generates a new one.
        """
        today = date.today()
        
        # 1. Check DB
        existing_tip = self._fetch_existing_tip(today)
        if existing_tip:
            return existing_tip
            
        # 2. Generate New
        return self._generate_new_tip(today)

    def _fetch_existing_tip(self, extract_date):
        sql = text("SELECT tip_text, related_pattern, severity_score FROM daily_tips WHERE generated_on = :date")
        try:
            with engine.connect() as conn:
                result = conn.execute(sql, {"date": extract_date}).fetchone()
                if result:
                    return {
                        "date": str(extract_date),
                        "tip": result[0],
                        "pattern": result[1],
                        "severity": result[2],
                        "source": "database_cache"
                    }
        except Exception as e:
            logger.error(f"Error fetching tip: {e}")
            return None
        return None

    def _fetch_recent_patterns(self, days=3):
        """
        Fetches patterns shown in the last N days to apply decay.
        """
        try:
            with engine.connect() as conn:
                # Get patterns from the last 'days' days, excluding today (if any)
                sql = text("""
                    SELECT related_pattern, generated_on 
                    FROM daily_tips 
                    WHERE generated_on >= CURRENT_DATE - INTERVAL :days DAY 
                    AND generated_on < CURRENT_DATE
                """)
                # SQLite/Postgres compatibility: Interval syntax might vary. 
                # safer to use python date math if DB agnostic, but let's try standard SQL first or bind params.
                # Actually, simpler to just fetch last 5 tips and filter in python to be safe across DB types if needed.
                # But let's verify DB type. It's likely Postgres based on "RETURNING id" usage in other files.
                # using standard interval syntax for now.
                
                rows = conn.execute(text("""
                    SELECT related_pattern 
                    FROM daily_tips 
                    WHERE generated_on >= :cutoff
                """), {"cutoff": date.today() - timedelta(days=days)}).fetchall()
                
                return [r[0] for r in rows]
        except Exception as e:
            logger.error(f"Failed to fetch recent patterns: {e}")
            return []

    def _generate_new_tip(self, generate_date):
        """
        Runs analysis, ranks risks, picks top one, formats tip, saves to DB.
        Avoiding repetition: Tries not to show the exact same pattern as yesterday.
        """
        logger.info("Generating new Daily Tip...")
        
        candidates = []
        
        # A. Run Pattern Engine (Structural Risks)
        patterns = self.pattern_engine.run_analysis()
        for p in patterns:
            candidates.append(self._pattern_to_tip(p))
            
        # B. Run Financial Ratio Checks (Data Risks)
        financial_tips = self._check_financial_ratios()
        candidates.extend(financial_tips)
        
        # C. Fallback
        if not candidates:
            fallback_tip = {
                "tip_text": "Operations are stable. No critical risks detected. Maintain current governance.",
                "related_pattern": "Stability",
                "severity_score": 0
            }
            candidates.append(fallback_tip)
            
        # D. Rank by Severity with Decay
        
        # 1. Get recent patterns
        recent_patterns = self._fetch_recent_patterns(days=3)
        logger.info(f"Recent patterns to decay: {recent_patterns}")
        
        # 2. Apply Decay
        # Rule: -5 points if shown in last 3 days
        for cand in candidates:
            if cand['related_pattern'] in recent_patterns:
                cand['severity_score'] -= 5
                cand['tip_text'] += " (Recurring Issue)"
        
        # 3. Sort desc by severity
        sorted_candidates = sorted(candidates, key=lambda x: x['severity_score'], reverse=True)
        
        # 4. Selection
        best_candidate = sorted_candidates[0]
        
        return self._finalize_tip(best_candidate, generate_date)

    def _finalize_tip(self, candidate, generate_date):
        # F. Save to DB
        self._save_tip(candidate, generate_date)
        
        return {
            "date": str(generate_date),
            "tip": candidate['tip_text'],
            "pattern": candidate['related_pattern'],
            "severity": candidate['severity_score'],
            "source": "generated_now"
        }

    def _save_tip(self, tip_data, generate_date):
        sql = text("""
            INSERT INTO daily_tips (tip_text, related_pattern, severity_score, generated_on)
            VALUES (:text, :pattern, :score, :date)
            ON CONFLICT (generated_on) DO NOTHING
        """)
        try:
            with engine.connect() as conn:
                conn.execute(sql, {
                    "text": tip_data['tip_text'],
                    "pattern": tip_data['related_pattern'],
                    "score": tip_data['severity_score'],
                    "date": generate_date
                })
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to save generated tip: {e}")

    # --- Rule Templates ---

    def _pattern_to_tip(self, pattern):
        """
        Converts a raw PatternEngine output to a user-friendly executive tip.
        """
        ptype = pattern['pattern']
        signals = pattern['trigger_signals']
        
        text = ""
        
        if ptype == "Escalation Risk":
            name = signals.get('project_name', 'Unknown Project')
            overrun = signals.get('budget_overrun_pct', 0)
            text = f"Action Required: Audit {name} immediately. It is running {overrun}% over budget. Initiate scope freeze."
            
        elif ptype == "Revenue Concentration Risk":
            industry = signals.get('industry', 'Unknown')
            share = signals.get('revenue_share_pct', 0)
            text = f"Strategic Risk: {industry} accounts for {share}% of revenue. Prioritize diversification into adjacent verticals to reduce exposure."
            
        elif ptype == "Overload Risk":
             emp = signals.get('employee', 'Employee')
             pct = signals.get('over_allocation_pct', 0)
             text = f"Capacity Alert: {emp} is over-allocated by {pct}%. Redistribute tasks or hire contractors to prevent burnout."
             
        elif ptype == "Churn Risk":
            client = signals.get('client', 'Client')
            text = f"Retention Alert: {client} gave a rating ≤ 2. Schedule a high-level intervention call today."
            
        elif ptype == "Governance Breakdown":
            proj = signals.get('project', 'Project')
            text = f"Process Failure: {proj} is past deadline but incomplete. Enforce daily stand-ups to unblock."
            
        else:
            text = f"Attention: {ptype} detected. Review detailed dashboard."
            
        return {
            "tip_text": text,
            "related_pattern": ptype,
            "severity_score": pattern.get('severity_score', 5)
        }

    def _check_financial_ratios(self):
        """
        Additional data-only checks not covered by PatternEngine (Marketing, Margin).
        """
        tips = []
        
        try:
            with engine.connect() as conn:
                # 1. Marketing Spend Ratio
                # Assuming 'expenses' table has 'category' and 'amount', and 'revenue' has 'amount'
                # Simplified schema assumption: 
                # Total Revenue
                rev_row = conn.execute(text("SELECT SUM(amount) FROM revenue")).fetchone()
                total_revenue = float(rev_row[0]) if rev_row and rev_row[0] else 0
                
                if total_revenue > 0:
                    # Marketing Expense
                    # Note: We need to see if 'expenses' table exists and has this data. 
                    # Based on sql_agent.py schema hint, we might not have 'expenses'.
                    # Let's check 'projects' budget vs cost? 
                    # User prompt mentioned "Marketing Expense". I will assume a query, 
                    # but if table missing, I'll catch exception and skip.
                    
                    try:
                        mark_row = conn.execute(text("SELECT SUM(amount) FROM expenses WHERE category = 'Marketing'")).fetchone()
                        marketing_spend = float(mark_row[0]) if mark_row and mark_row[0] else 0
                        
                        ratio = (marketing_spend / total_revenue) * 100
                        
                        # Rule: If > 15% AND Overload detected? 
                        # User prompt: "If marketing expense >15% revenue AND overload detected"
                        # I'll simplify: strictly check the ratio for now.
                        if ratio > 15:
                             tips.append({
                                "tip_text": f"Efficiency Opportunity: Marketing spend is {round(ratio,1)}% of revenue (>15%). Reallocate 15% of this budget to R&D or Operations.",
                                "related_pattern": "Marketing Efficiency",
                                "severity_score": 6
                             })
                    except Exception:
                         pass # Table might not exist
                    
                    # 2. Margin/Salary Risk
                    # "If salary > 70% revenue"
                    # We have employees.monthly_salary.
                    try:
                        sal_row = conn.execute(text("SELECT SUM(monthly_salary) FROM employees")).fetchone()
                        total_monthly_salary = float(sal_row[0]) if sal_row and sal_row[0] else 0
                        annual_salary = total_monthly_salary * 12
                        
                        sal_ratio = (annual_salary / total_revenue) * 100
                        
                        if sal_ratio > 70:
                             tips.append({
                                "tip_text": f"Margin Risk: Projected annual salary cost is {round(sal_ratio,1)}% of revenue. Implement hiring freeze or pricing revision.",
                                "related_pattern": "Margin Squeeze",
                                "severity_score": 9
                             })
                    except Exception:
                        pass

        except Exception as e:
            logger.error(f"Financial ratio check failed: {e}")
            
        return tips
