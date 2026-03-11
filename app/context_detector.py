import re
import logging

logger = logging.getLogger(__name__)

class CompanyContextDetector:
    """
    Detects if a query implies a specific company context (Database) 
    vs general conceptual context (PDF/Theory).
    """

    # Strong indicators of company data
    COMPANY_KEYWORDS = [
        r"\b(our|my|the)\s+company\b",
        r"\b(our|my|the)\s+employees?\b",
        r"\b(our|my|the)\s+projects?\b",
        r"\b(our|my|the)\s+revenue\b",
        r"\b(our|my|the)\s+expenses?\b",
        r"\b(our|my|the)\s+budget\b",
        r"\b(our|my|the)\s+clients?\b",
        r"\b(our|my|the)\s+tasks?\b",
        r"\b(our|my|the)\s+meetings?\b",
        r"\b(we|us|entity)\b",  # 'Entity' is correctly detected as the company name
        r"\bdatabase\b",
        r"\bsql\b"
    ]

    # Specific entities that almost always mean database queries
    ENTITY_KEYWORDS = [
        r"\bsalary\b",
        r"\bsalaries\b",
        r"\bpay\b",
        r"\bpaid\b",
        r"\bearn(s|ing|ings)?\b",
        r"\bcost\b",
        r"\bprofit\b",
        r"\bloss\b",
        r"\bmargin\b",
        r"\bdeadline\b",
        r"\bhired?\b",
        r"\bfired?\b",
        r"\bpromote\b",
        r"\braise\b",
        r"\bbonus\b",
        r"\bhighest\b",
        r"\blowest\b",
        r"\baverage\b",
        r"\btotal\b",
        r"\bcount\b"
    ]

    def is_company_context(self, query: str) -> bool:
        """
        Returns True if the query likely refers to internal company data.
        """
        query_lower = query.lower().strip()
        
        # Check explicit company references
        for pattern in self.COMPANY_KEYWORDS:
            if re.search(pattern, query_lower):
                logger.info(f"Context Detector: Company Keyword Matched -> {pattern}")
                return True
                
        # Check specific data entities
        for pattern in self.ENTITY_KEYWORDS:
            if re.search(pattern, query_lower):
                logger.info(f"Context Detector: Entity Keyword Matched -> {pattern}")
                return True
        
        # Check for numeric constraints which usually imply data analysis
        # e.g. "employees > 5000", "revenue last month"
        if re.search(r"\d+", query_lower) and ("year" in query_lower or "month" in query_lower or "greater" in query_lower or "less" in query_lower):
             logger.info("Context Detector: Numeric constraint detected -> Company Context")
             return True

        return False
