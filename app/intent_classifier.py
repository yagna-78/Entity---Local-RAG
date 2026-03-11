import logging
import json
import re
from typing import Dict, Any, Optional
import ollama

logger = logging.getLogger(__name__)

class IntentClassifier:
    """
    Classifies user queries into one of four categories:
    - THEORY: Conceptual questions, definitions, frameworks.
    - DATA_ANALYSIS: Quantitative questions about company data (revenue, employees, etc.).
    - HYBRID: Questions requiring both data and strategic interpretation.
    - GENERAL: Small talk, greetings, or out-of-scope queries.
    """

    def __init__(self, model_name: str = "qwen2.5:7b"):
        self.model_name = model_name
        self.system_prompt = (
            "You are an Intent Classification & Depth Analysis Engine for Entity.\n"
            "Your job is to classify the user's query into EXACTLY ONE Intent and ONE Depth Level.\n\n"
            "--- INTENTS ---\n"
            "1. **THEORY**: Conceptual questions, business frameworks, marketing strategy, definitions. (e.g., 'What is Blue Ocean Strategy?')\n"
            "2. **DATA_ANALYSIS**: Questions strictly about company database numbers. Keywords: revenue, cost, employees, projects, budget, tasks, delays. (e.g., 'What was our Q3 revenue?')\n"
            "3. **HYBRID**: Questions that need specific company data to answer a strategic question. (e.g., 'Given our high burn rate, what changes should we make?')\n"
            "4. **GENERAL**: Greetings, thanks, or casual conversation. (e.g., 'Hi', 'Good morning')\n\n"
            "--- DEPTH LEVELS ---\n"
            "1. **INFORMATIONAL**: Single attribute question, simple lookup, no diagnostic verbs. (e.g., 'Where is Dream Homes?', 'What is the budget for Project X?')\n"
            "2. **DIAGNOSTIC**: Asks for cause, pattern, reason, or explanation. (e.g., 'Why is Project 4 delayed?', 'What caused the revenue drop?')\n"
            "3. **STRATEGIC**: Asks for risk, impact, recommendation, decision, or future scenario. (e.g., 'If Dream Homes cancels, what happens?', 'How should we respond to this?')\n\n"
            "OUTPUT FORMAT:\n"
            "Return a strictly valid JSON object. Do NOT add markdown formatting or explanations.\n"
            "{\n"
            "  \"intent\": \"THEORY | DATA_ANALYSIS | HYBRID | GENERAL\",\n"
            "  \"depth\": \"INFORMATIONAL | DIAGNOSTIC | STRATEGIC\",\n"
            "  \"confidence\": <integer between 0 and 100>,\n"
            "  \"reasoning\": \"<brief explanation>\"\n"
            "}"
        )

    async def classify(self, query: str) -> Dict[str, Any]:
        """
        Classifies the query and returns the intent, confidence, and depth.
        """
        try:
            response = await ollama.AsyncClient(host='http://127.0.0.1:11434').generate(
                model=self.model_name,
                prompt=f"{self.system_prompt}\n\nUser Query: \"{query}\"\nJSON Output:",
                options={
                    "temperature": 0.1,  # Low temperature for deterministic classification
                    "num_predict": 128,
                    "format": "json"     # Enforce JSON output mode if supported by the model
                }
            )

            raw_response = response['response'].strip()
            
            # Attempt to parse JSON
            try:
                # Cleanup if model adds markdown
                cleaned_json = raw_response
                if '```json' in cleaned_json:
                    cleaned_json = re.search(r'```json\s*(\{.*?\})\s*```', cleaned_json, re.DOTALL).group(1)
                elif '```' in cleaned_json:
                    cleaned_json = re.search(r'```\s*(\{.*?\})\s*```', cleaned_json, re.DOTALL).group(1)
                
                result = json.loads(cleaned_json)
                
                # Normalize keys
                intent = result.get("intent", "GENERAL").upper()
                confidence = result.get("confidence", 0)
                depth = result.get("depth", "INFORMATIONAL").upper()
                
                # Validation
                valid_intents = ["THEORY", "DATA_ANALYSIS", "HYBRID", "GENERAL"]
                if intent not in valid_intents:
                    logger.warning(f"Invalid intent '{intent}' detected. Defaulting to GENERAL.")
                    intent = "GENERAL"
                    confidence = 0
                
                valid_depths = ["INFORMATIONAL", "DIAGNOSTIC", "STRATEGIC"]
                if depth not in valid_depths:
                    depth = "INFORMATIONAL"

                logger.info(f"Intent Classifier: {intent} (Confidence: {confidence}%, Depth: {depth})")
                return {"intent": intent, "confidence": confidence, "depth": depth}

            except json.JSONDecodeError:
                logger.error(f"Failed to parse Intent Classifier output: {raw_response}")
                return {"intent": "GENERAL", "confidence": 0, "depth": "INFORMATIONAL"}

        except Exception as e:
            logger.error(f"Intent Classifier Error: {e}")
            return {"intent": "GENERAL", "confidence": 0, "depth": "INFORMATIONAL"}
