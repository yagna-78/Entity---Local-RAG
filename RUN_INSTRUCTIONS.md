# Local Business Strategy Advisor - Setup & Run

## Overview
This system has been upgraded from a simple RAG chatbot to a **Business Strategy Advisor**. 
It now supports two modes:
1.  **Q&A Mode**: Standard document retrieval.
2.  **Business Advisor Mode**: Uses retrieved business principles to analyze user reports and generate structured strategic advice.

## Quick Start

### 1. Update Dependencies (If needed)
If you haven't already:
```powershell
pip install -r requirements.txt
```

### 2. Re-Ingest Data (CRITICAL)
We have updated the chunking strategy to better capture business contexts (~1000 chars/chunk). You **MUST** run this to rebuild the database:
```powershell
python manual_ingest.py
```
*Ensure your business books and strategy documents are in the `data/` folder.*

### 3. Run the App
Start the server:
```powershell
python app/main.py
```
*Server runs at: http://127.0.0.1:8000*

### 4. Application Usage
1.  **Open Browser**: Go to [http://127.0.0.1:8000](http://127.0.0.1:8000).
2.  **Upload User Report**: Use the "Upload Document" button to add a specific company report (PDF/TXT).
3.  **Select Mode**:
    *   Choose **"Business Advisor"** from the sidebar.
    *   Select your preferred powerful model (e.g., `qwen2.5:7b` or `mistral:7b`).
4.  **Ask**:
    *   "Analyze the uploaded financial report and suggest cost-cutting strategies."
    *   "Based on the strategy documents, how should we enter the Asian market?"

## Features
*   **Structured Output**: The Advisor mode forces a specific format (Executive Summary, Problems, Opportunities, Actions, Risks).
*   **Deep Retrieval**: Context retrieval is increased (`k=6`) in Advisor mode for better synthesis.
*   **Hallucination Control**: Strict instructions to use *only* provided data.
