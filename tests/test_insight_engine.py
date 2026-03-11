import unittest
import sys
import os

# Add app to path
sys.path.append(os.path.join(os.getcwd(), 'app'))
sys.path.append(os.getcwd())

from app.insight_engine import InsightEngine

class TestInsightEngine(unittest.TestCase):
    
    def test_concentration_risk(self):
        kpis = {"revenue_concentration": 75}
        insights = InsightEngine.generate_insights(kpis)
        
        self.assertTrue(len(insights) > 0)
        risk = next((i for i in insights if i["issue_type"] == "Concentration Risk"), None)
        
        self.assertIsNotNone(risk)
        self.assertEqual(risk["root_cause"], "Client Dependency")
        self.assertIn("Diversify vertical mix", risk["recommended_action"])

    def test_burnout_risk(self):
        kpis = {"employee_utilization": 115}
        insights = InsightEngine.generate_insights(kpis)
        
        risk = next((i for i in insights if i["issue_type"] == "Burnout Risk"), None)
        
        self.assertIsNotNone(risk)
        self.assertEqual(risk["root_cause"], "Resource Overload")
        self.assertIn("Hire additional engineer", risk["recommended_action"])

    def test_severity_sorting(self):
        kpis = {
            "revenue_concentration": 75, # Severity 90
            "employee_utilization": 115, # Severity 85
            "on_time_delivery": 70       # Severity 80
        }
        insights = InsightEngine.generate_insights(kpis)
        
        self.assertEqual(len(insights), 3)
        self.assertEqual(insights[0]["issue_type"], "Concentration Risk") # Highest severity
        self.assertEqual(insights[1]["issue_type"], "Burnout Risk")
        self.assertEqual(insights[2]["issue_type"], "Delivery Failure")

if __name__ == '__main__':
    unittest.main()
