
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ExecutiveSummaryGenerator:
    """
    PHASE 3: EXECUTIVE SUMMARY GENERATOR
    
    Responsibilities:
    1. Ingest Risk Profile (from RiskEngine) and Financial Forecast.
    2. Generate concise, decisive operational narrative.
    3. Structure: 
       - Financial Health
       - Operational Strain
       - Client Risk
       - Immediate Action
    """
    
    @staticmethod
    def generate_summary(risk_profile: Dict, forecast: Dict) -> Dict[str, str]:
        """
        Generates the 4-point executive summary.
        """
        logger.info("Generating Executive Summary...")
        
        # Extract Key Signals
        f_risk = risk_profile["breakdown"]["financial_risk"]
        o_risk = risk_profile["breakdown"]["operational_risk"]
        c_risk = risk_profile["breakdown"]["client_risk"]
        
        factors = risk_profile["factors"]
        margin = factors.get("margin", 0)
        runway = factors.get("runway", 99)
        utilization = factors.get("utilization", 0)
        concentration = factors.get("concentration", 0)
        
        # 1. Financial Health Summary
        financial_msg = ""
        if margin > 20 and runway > 6:
            financial_msg = "Financials are strong with healthy margins (>20%) and extended runway."
        elif margin > 0:
            financial_msg = f"Profitable ({margin:.1f}%) but efficiency improvements needed."
        else:
            financial_msg = "CRITICAL: Negative margin requires immediate cost restructuring."
            
        if runway < 3:
            financial_msg += f" Runway is critical (<{runway:.1f} months)."

        # 2. Operational Strain Summary
        ops_msg = ""
        if utilization > 110:
            ops_msg = "Severe burnout risk detected (Utilization >110%). Delivery failure imminent."
        elif utilization > 95:
            ops_msg = "Team at capacity. Efficiency dropping due to high load."
        elif utilization < 70:
            ops_msg = "Resource underutilization detected. Capacity available for new projects."
        else:
            ops_msg = "Operations stable with optimal resource load."

        # 3. Client Risk Summary
        client_msg = ""
        if concentration > 50:
            client_msg = f"High dependency risk: Single client holds {concentration:.1f}% of revenue."
        elif concentration > 30:
            client_msg = "Revenue concentration is elevated; diversification recommended."
        else:
            client_msg = "Client portfolio is well-diversified."

        # 4. Immediate Action Recommendation (The 'So What?')
        action_msg = ""
        # Priority Logic: Financial > Client > Ops
        if f_risk > 70:
             action_msg = "IMMEDIATE PRIORITY: Cut non-essential costs and freeze hiring to extend runway."
        elif c_risk > 60:
             action_msg = "PRIORITY: Aggressively pursue new accounts to dilute concentration risk."
        elif o_risk > 70:
             action_msg = "PRIORITY: Hire additional resources or decline low-margin work to reduce burnout."
        else:
             action_msg = "Maintain current growth trajectory. Focus on optimizing margin."
             
        # Combined Formatting
        full_text = (
            f"**Financial:** {financial_msg}\n"
            f"**Operational:** {ops_msg}\n"
            f"**Client Risk:** {client_msg}\n"
            f"**Action:** {action_msg}"
        )

        return {
            "financial_health": financial_msg,
            "operational_strain": ops_msg,
            "client_risk": client_msg,
            "immediate_action": action_msg,
            "full_narrative": full_text
        }
