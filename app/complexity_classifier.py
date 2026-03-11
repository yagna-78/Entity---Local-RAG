import re
import logging

logger = logging.getLogger(__name__)

class ComplexityClassifier:
    """
    Classifies queries into SIMPLE or COMPLEX based on regex patterns.
    Extracts parameters for Fast SQL Path.
    """
    
    PATTERNS = {
        "SALARY_LOOKUP": [
            r"what is ([\w\s]+)'s salary",
            r"how much does ([\w\s]+) make",
            r"salary of ([\w\s]+)",
            r"show me ([\w\s]+)'s pay"
        ],
        "HIGHEST_PAID": [
            r"who is the highest paid",
            r"highest paid employee",
            r"top earner",
            r"who makes the most money"
        ],
        "EMPLOYEE_COUNT": [
            r"how many employees",
            r"total number of employees",
            r"count of staff",
            r"total staff"
        ],
        # Add simpler expense lookups here later if needed
    }

    def classify(self, query: str):
        query_lower = query.lower().strip()
        
        for intent, patterns in self.PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, query_lower)
                if match:
                    logger.info(f"Complexity Classifier: Detected SIMPLE intent [{intent}]")
                    params = {}
                    if match.groups():
                        params["name"] = match.group(1).strip()
                    
                    return {
                        "complexity": "SIMPLE",
                        "intent": intent,
                        "params": params
                    }
                    
        logger.info("Complexity Classifier: Defaulting to COMPLEX")
        return {"complexity": "COMPLEX", "intent": None, "params": {}}
