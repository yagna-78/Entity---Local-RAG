import logging
from sqlalchemy import text
from database import engine

logger = logging.getLogger(__name__)

class FastSQLExecutor:
    """
    Executes pre-defined SQL templates for SIMPLE intents.
    Bypasses LLM generation.
    """
    
    TEMPLATES = {
        "SALARY_LOOKUP": {
            "sql": "SELECT name, monthly_salary, role FROM employees WHERE LOWER(name) LIKE LOWER(:name)",
            "format": "{name} ({role}) verifies a monthly salary of ₹{monthly_salary:,.2f}."
        },
        "HIGHEST_PAID": {
            "sql": "SELECT name, monthly_salary, role FROM employees ORDER BY monthly_salary DESC LIMIT 1",
            "format": "The highest paid employee is {name} ({role}) with ₹{monthly_salary:,.2f} per month."
        },
        "EMPLOYEE_COUNT": {
            "sql": "SELECT COUNT(*) as count FROM employees",
            "format": "There are currently {count} employees in the company."
        }
    }

    def execute(self, intent: str, params: dict):
        if intent not in self.TEMPLATES:
            return None
            
        template = self.TEMPLATES[intent]
        sql = template["sql"]
        
        try:
            with engine.connect() as connection:
                # Prepare params for LIKE query if needed
                if "name" in params:
                    # simplistic fuzzy match
                    params["name"] = f"%{params['name']}%"
                    
                result = connection.execute(text(sql), params)
                row = result.fetchone()
                
                if not row:
                    return "No data found for this query."
                
                # Convert row to dict for formatting
                data = dict(zip(result.keys(), row))
                
                # Format response
                return template["format"].format(**data)
                
        except Exception as e:
            logger.error(f"Fast SQL Error: {e}")
            return f"Error executing fast query: {str(e)}"
