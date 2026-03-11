import asyncio
import sys
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Add app to path
sys.path.append(os.path.join(os.getcwd(), 'app'))

# Now we can import router directly
try:
    from router import RoutingController
except ImportError:
    # If checking from root, maybe need to add root?
    sys.path.append(os.getcwd())
    from app.router import RoutingController

class TestOperationalMode(unittest.TestCase):
    def setUp(self):
        # Patching modules where they are IMPORTED in router.py
        # Since router.py does: "from intent_classifier import IntentClassifier"
        # We need to patch 'router.IntentClassifier'
        
        self.patches = [
            patch('router.IntentClassifier'),
            patch('router.ComplexityClassifier'),
            patch('router.FastSQLExecutor'),
            patch('router.CompanyContextDetector'),
            patch('router.PatternEngine'),
            patch('router.knowledge_engine'),
            patch('router.memory_engine'),  # Add memory engine
            patch('router.engine')          # Add database engine
        ]
        
        self.mock_objs = [p.start() for p in self.patches]
        
        # Initialize
        self.router = RoutingController()

        # Mock internal components
        self.router.classifier = AsyncMock()
        self.router.complexity_classifier = MagicMock()
        self.router.complexity_classifier.classify.return_value = {"complexity": "COMPLEX", "intent": "TEST"}
        self.router.fast_executor = MagicMock()
        self.router.context_detector = MagicMock()
        self.router.context_detector.is_company_context.return_value = True
        self.router.pattern_engine = MagicMock()
        self.router.pattern_engine.run_analysis.return_value = []
        
        # Mock _log_interaction to avoid DB errors
        self.router._log_interaction = MagicMock()

    def tearDown(self):
        patch.stopall()

    @patch('router.generate_and_execute_sql', new_callable=AsyncMock)
    @patch('router.knowledge_engine.retrieve_context')
    @patch('router.ollama.AsyncClient')
    def test_retrieval_gating_data_exists(self, mock_ollama, mock_retrieve, mock_sql):
        """
        Test that if DB data exists, PDF retrieval is BLOCKED.
        """
        async def run_test():
            # Setup: Data IS found
            mock_sql.return_value = (True, [{"revenue": 5000000}], "SELECT revenue FROM finance")
            
            # Mock Classifier to return HYBRID (Strategic) to trigger the logic
            self.router.classifier.classify.return_value = {
                "intent": "HYBRID",
                "confidence": 95,
                "depth": "STRATEGIC"
            }

            # Mock Ollama response stream
            mock_client_instance = AsyncMock()
            mock_ollama.return_value = mock_client_instance
            
            async def async_generator():
                yield {'message': {'content': 'Analysis based on data.'}}
            
            mock_client_instance.chat.return_value = async_generator()

            # Execute
            response = ""
            async for chunk in self.router.process_request("What is the revenue strategy?", [], model="test"):
                response += chunk

            # Assertions
            mock_sql.assert_called() # SQL should be called
            mock_retrieve.assert_not_called() # PDF retrieval should be BLOCKED
            print("\n✅ Test Passed: Retrieval blocked when data exists.")

        asyncio.run(run_test())

    @patch('router.generate_and_execute_sql', new_callable=AsyncMock)
    @patch('router.knowledge_engine.retrieve_context')
    @patch('router.ollama.AsyncClient')
    def test_retrieval_fallback_no_data(self, mock_ollama, mock_retrieve, mock_sql):
        """
        Test that if NO data exists, PDF retrieval is ALLOWED.
        """
        async def run_test():
            # Setup: No data found
            mock_sql.return_value = (False, [], None)
            
            # Setup: Retrieval works
            mock_retrieve.return_value = ("PDF Content", ["doc1.pdf"])

            # Mock Classifier
            self.router.classifier.classify.return_value = {
                "intent": "HYBRID",
                "confidence": 95,
                "depth": "STRATEGIC"
            }

            # Mock Ollama
            mock_client_instance = AsyncMock()
            mock_ollama.return_value = mock_client_instance
            
            async def async_generator():
                yield {'message': {'content': 'Theoretical analysis.'}}
            
            mock_client_instance.chat.return_value = async_generator()

            # Execute
            response = ""
            async for chunk in self.router.process_request("Explain the strategy", [], model="test"):
                response += chunk

            # Assertions
            mock_sql.assert_called() 
            mock_retrieve.assert_called() # PDF retrieval should be called
            print("\n✅ Test Passed: Retrieval allowed when data is missing.")

        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()
