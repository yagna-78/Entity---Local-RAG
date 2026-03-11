import sys
import os
import unittest
import logging

# Add app to path
sys.path.append(os.path.join(os.getcwd(), 'app'))
sys.path.append(os.getcwd())

try:
    from app.simulation_engine import SimulationEngine
except ImportError:
    from simulation_engine import SimulationEngine

# Configure logging to capture output
logging.basicConfig(level=logging.INFO)

class TestHiringSimulation(unittest.TestCase):
    def setUp(self):
        self.baseline = {
            "revenue": 1000000.0,
            "expenses": 500000.0,
            "salaries": 200000.0,
            "employee_count": 10,
            "client_revenue": {}
        }

    def test_hiring_with_valid_salary(self):
        """Test successful simulation with valid salary per hire."""
        scenario = {
            "new_employees": 2,
            "salary_per_hire": 50000
        }
        
        result = SimulationEngine.run_simulation(self.baseline, scenario)
        
        # Original Salaries: 200,000
        # Added Cost: 2 * 50,000 = 100,000
        # New Salaries: 300,000
        
        self.assertEqual(result['simulated']['salaries'], 300000.0)
        self.assertEqual(result['simulated']['employees'], 12)
        print("\n✅ Test Passed: Hiring with valid salary increases costs correctly.")

    def test_hiring_missing_salary(self):
        """Test failure when salary is missing or zero."""
        scenario = {
            "new_employees": 1,
            "salary_per_hire": 0
        }
        
        # SimulationEngine catches exceptions and returns {"error": ...}
        result = SimulationEngine.run_simulation(self.baseline, scenario)
        
        self.assertIn("error", result)
        self.assertIn("'Salary per Hire' is required", result["error"])
        print("\n✅ Test Passed: Missing salary triggers error.")

if __name__ == '__main__':
    unittest.main()
