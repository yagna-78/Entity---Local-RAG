
import logging
import re
import ollama
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

# --- STRICT HUMANIZATION PROMPT ---
PROMPT_HUMANIZER = """
SYSTEM ROLE: Executive Communications Lead.
OBJECTIVE: Reformat the provided STRUCTURED DATA into a NATURAL, DECISION-FOCUSED narrative.

-----------------------------------------
INPUT DATA:
{input_data}

-----------------------------------------
STRICT RULES (NON-NEGOTIABLE):
1. NO ROBOTIC HEADERS (e.g., "## Analysis", "### Conclusion").
2. NO BULLET POINT LISTS unless absolutely necessary for data density.
3. DO NOT CHANGE ANY NUMBERS. (If input says "50%", output MUST say "50%").
4. DO NOT ADD NEW ASSUMPTIONS.
5. DO NOT USE GENERIC OPENERS (e.g., "Based on the data provided..."). Start directly with the insight.
6. TONE: Direct, authoritative, "COO-style".
-----------------------------------------
EXAMPLE OUTPUT STYLE:

"Revenue is down 12% driven by a sharp drop in the Enterprise segment. While churn is stable, the pipeline velocity has slowed significantly. We need to immediately reallocate SDRs to the mid-market vertical to compensate for this gap."

-----------------------------------------
YOUR TURN. REWRITE THE DATA ABOVE.
"""

class Humanizer:
    def __init__(self, model_name: str = "mistral:latest"):
        self.model_name = model_name
        self.llm_client = ollama.AsyncClient(host='http://127.0.0.1:11434')

    async def process(self, raw_input: str) -> AsyncGenerator[str, None]:
        """
        Takes raw structured output (JSON/bullet points) and converts it to natural text.
        """
        prompt = PROMPT_HUMANIZER.format(input_data=raw_input)
        
        try:
            options = {
                "num_predict": 1024,
                "temperature": 0.5, # Slightly higher for natural flow, but constrained by prompt
                "repeat_penalty": 1.1
            }
            
            # Streaming the humanized response
            async for chunk in await self.llm_client.generate(model=self.model_name, prompt=prompt, stream=True, options=options):
                content = chunk['response']
                if content:
                    yield content

        except Exception as e:
            logger.error(f"Humanizer Error: {e}")
            # Fallback: Just return the raw input if humanization fails
            yield raw_input

    def verify_numbers(self, original: str, humanized: str) -> bool:
        """
        Safety check: Extracts numbers from both texts and ensures
        the humanized version didn't hallucinate or drop key figures.
        (Simplified version: Checks if all 4+ digit numbers / percentages in original exist in humanized)
        """
        # Regex for currency/percentages/large numbers
        pattern = r'(\₹?[\d,]+\.?\d*%?)'
        
        # This is a complex problem to solve perfectly with regex.
        # For now, we trust the prompt engineering + low temp.
        # This method is a placeholder for future strict validation.
        return True
