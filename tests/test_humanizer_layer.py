
import asyncio
import sys
import os

# Add app to path
sys.path.append(os.path.join(os.getcwd(), 'app'))

try:
    from humanizer import Humanizer
except ImportError:
    # Handle the case where the app directory structure might be different or needed
    sys.path.append(os.path.join(os.getcwd(), 'd:/RAG - ChatBot/RAG - ChatBot/app'))
    from humanizer import Humanizer

SAMPLE_INPUT = """
- Revenue dropped 15% (₹1.2M) in Q3 due to churn.
- Customer X is the primary driver of this loss (-₹800k).
- Pattern detected: High churn in region Y (Severity: High).
"""

async def test_humanizer():
    print("Initializing Humanizer...")
    try:
        humanizer = Humanizer(model_name="mistral:latest")
        
        print("\n--- INPUT DATA ---")
        print(SAMPLE_INPUT)
        
        print("\n--- HUMANIZED OUTPUT ---")
        full_output = ""
        async for chunk in humanizer.process(SAMPLE_INPUT):
            print(chunk, end="", flush=True)
            full_output += chunk
        print("\n")

        # Verification checks
        if "15%" in full_output:
            print("✅ Number Check Passed: 15% preserved")
        else:
            print("❌ Number Check Failed: 15% missing")

        if "1.2M" in full_output:
            print("✅ Number Check Passed: 1.2M preserved")
        else:
            print("❌ Number Check Failed: 1.2M missing")

        if "##" in full_output:
            print("❌ Style Check Failed: Headers detected")
        else:
            print("✅ Style Check Passed: No headers found")
            
    except Exception as e:
        print(f"Test Failed with Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_humanizer())
