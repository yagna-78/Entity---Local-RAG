import os
import sys
import re

# Ensure the app directory is on Python path for bare imports
_app_dir = os.path.dirname(os.path.abspath(__file__))
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)

import logging
import shutil
import traceback
from sqlalchemy import text
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Import modules
import knowledge_engine
from router import RoutingController
from tip_engine import TipEngine
import kpi_engine
from database import get_db, engine, Base
import asyncio # <--- NEW IMPORT

# Configuration
# (Most config moved to rag_engine or router, keeping local constants if needed)

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances
routing_controller = None

# Map legacy/stale frontend model names to currently installed models
MODEL_MAPPINGS = {
    "mistral:7b": "mistral:latest",
    "qwen2.5:0.5b": "qwen2.5:7b",
    "qwen2.5:1.5b": "qwen2.5:7b",
    "qwen2.5:3b": "qwen2.5:7b",
    "qwen2.5:14b": "qwen2.5:7b",
}
DEFAULT_MODEL = "qwen2.5:7b"

# --- KPI Scheduler ---
async def run_kpi_scheduler():
    """
    Background task to run KPI computation every 5 minutes.
    """
    while True:
        try:
            logger.info("⏳ Running KPI Computation Cycle...")
            # compute_kpis is synchronous/blocking, so run in threadpool
            await asyncio.to_thread(kpi_engine.compute_kpis)
            logger.info("✅ KPI Computation Complete.")
        except Exception as e:
            logger.error(f"❌ KPI Scheduler Error: {e}")
        
        # Wait 5 minutes
        await asyncio.sleep(300)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Load models and database on startup.
    """
    global routing_controller
    
    logger.info("Initializing resources...")
    knowledge_engine.initialize_resources()
    
    logger.info("Initializing Routing Controller...")
    routing_controller = RoutingController(model_name=DEFAULT_MODEL)
    
    # Initialize Tip Engine (ensure DB ready)
    global tip_engine
    tip_engine = TipEngine()
    
    # Create tables if they don't exist (basic auto-migration)
    if engine:
        # STEP 6: DATABASE INITIALIZATION & CONNECTION VALIDATION
        try:
            # Create tables if they don't exist (basic auto-migration)
            Base.metadata.create_all(bind=engine)
        
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            logger.info("✅ Database Connection Verified (SELECT 1).")
            
            # --- KPI ENGINE STARTUP ---
            logger.info("Initializing KPI Engine Schema...")
            kpi_engine.ensure_kpi_schema()
            
            # Start Scheduler
            asyncio.create_task(run_kpi_scheduler())
            
        except Exception as e:
            logger.critical(f"❌ DATABASE CONNECTION ERROR: {e}. Server will start but DB features disabled.")
    else:
        logger.error("Database engine is None. Logging will fail.")
    
    yield
    
    logger.info("Shutting down...")

app = FastAPI(title="Entity Context-Aware Chatbot", lifespan=lifespan)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class QueryRequest(BaseModel):
    question: str
    model: str = DEFAULT_MODEL
    mode: str = "qa"  # Options: "qa", "advisor" (Legacy compatibility)
    history: List[dict] = []

class MessageRequest(BaseModel):
    content: str
    model: str = DEFAULT_MODEL
    role: str = "user"

class ConversationCreate(BaseModel):
    user_id: Optional[str] = None
    title: Optional[str] = "New Conversation"

class RenameRequest(BaseModel):
    title: str

class IngestResponse(BaseModel):
    message: str
    count: int

# --- API Endpoints ---

@app.get("/health")
async def health_check():
    """
    Health Check Endpoint.
    """
    return {"status": "ok", "message": "Entity AI Backend is running"}

# ... (Chat History Endpoints Removed)


@app.post("/upload", response_model=IngestResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a new file to the data directory and trigger ingestion.
    """
    # Ensure data dir exists
    if not os.path.exists(knowledge_engine.DATA_DIR):
        os.makedirs(knowledge_engine.DATA_DIR)

    try:
        # Validate file type
        if not file.filename.lower().endswith((".txt", ".pdf")):
            raise HTTPException(status_code=400, detail="Only .txt and .pdf files are supported")
            
        file_path = os.path.join(knowledge_engine.DATA_DIR, file.filename)
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        logger.info(f"File uploaded: {file.filename}")
        
        # Trigger ingestion
        knowledge_engine.ingest_data(force=True)
        count = knowledge_engine.get_collection_count()
        
        return IngestResponse(message=f"File '{file.filename}' uploaded and processed successfully.", count=count)
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest", response_model=IngestResponse)
async def trigger_ingest():
    """
    Force re-ingestion of data.
    """
    try:
        knowledge_engine.ingest_data(force=True)
        count = knowledge_engine.get_collection_count()
        return IngestResponse(message="Ingestion complete successfully.", count=count)
    except Exception as e:
        logger.error(f"Ingestion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/daily-tip")
async def get_daily_tip():
    """
    Returns the executive Tip of the Day.
    Generates a new one if none exists for today.
    """
    try:
        if tip_engine is None:
             raise HTTPException(status_code=500, detail="Tip Engine not initialized.")
             
        tip = tip_engine.get_daily_tip()
        return tip
    except Exception as e:
        logger.error(f"Daily Tip Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/kpis/compute")
async def trigger_kpi_computation():
    """
    Manually triggers KPI computation.
    """
    try:
        await asyncio.to_thread(kpi_engine.compute_kpis)
        return {"status": "success", "message": "KPI computation triggered successfully."}
    except Exception as e:
        logger.error(f"Manual KPI Input Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/kpis")
async def get_kpis():
    """
    Returns the latest KPI results for the dashboard.
    """
    try:
        with engine.connect() as conn:
            # Join definitions and results to get names and targets
            # Get the LATEST result for each KPI
            # We cast to FLOAT to ensure JSON serializability (handle Decimal types)
            query = text("""
                SELECT 
                    d.kpi_name,
                    d.kpi_code,
                    CAST(r.actual_value AS FLOAT) as actual_value,
                    CAST(r.previous_value AS FLOAT) as previous_value,
                    CAST(r.delta_percent AS FLOAT) as delta_percent,
                    CAST(d.target_value_min AS FLOAT) as target_min,
                    CAST(d.target_value_max AS FLOAT) as target_max,
                    r.status,
                    r.calculated_at,
                    d.unit_type,
                    d.time_scope
                FROM kpi_results r
                JOIN kpi_definitions d ON r.kpi_id = d.id
                WHERE r.calculated_at = (
                    SELECT MAX(calculated_at) 
                    FROM kpi_results r2 
                    WHERE r2.kpi_id = r.kpi_id
                )
                ORDER BY d.id ASC;
            """)
            results = conn.execute(query).fetchall()
            
            response_data = []
            for row in results:
                try:
                    # row indices: 0=name, 1=code, 2=value, 3=prev_value, 4=delta_percent, 
                    # 5=target_min, 6=target_max, 7=status, 8=last_updated, 9=unit_type, 10=time_scope
                    response_data.append({
                        "name": row[0],
                        "code": row[1],
                        "value": row[2] if row[2] is not None else 0.0,
                        "previous_value": row[3] if row[3] is not None else None,
                        "delta_percent": row[4] if row[4] is not None else None,
                        "target_min": row[5] if row[5] is not None else None,
                        "target_max": row[6] if row[6] is not None else None,
                        "status": row[7],
                        "last_updated": row[8].isoformat() if row[8] else None,
                        "unit_type": row[9],
                        "time_scope": row[10]
                    })
                except Exception as row_err:
                    logger.error(f"Error processing KPI row: {row} - {row_err}")
                    continue # Skip bad row instead of crashing query

            return response_data
            
    except Exception as e:
        logger.error(f"KPI Fetch Error: {e}")
        # Return a meaningful error message
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

# --- Dashboard & Portfolio Routes ---
from api_routes import router as api_router
app.include_router(api_router)

@app.post("/ask")
async def ask(request: QueryRequest):
    """
    Main Chat Endpoint (Legacy/Stateless).
    Routes query via Context-Aware Routing Controller.
    """
    try:
        query = request.question
        model = request.model
        history = request.history

        # --- INSTANT GREETING DETECTION ---
        # Respond instantly to greetings without invoking the LLM pipeline
        _greeting_patterns = {
            "hi", "hello", "hey", "hii", "hiii", "helo",
            "good morning", "good afternoon", "good evening", "good night",
            "gm", "morning", "evening",
            "howdy", "yo", "sup", "whats up", "what's up",
            "greetings", "namaste", "hola",
            "thanks", "thank you", "thankyou", "thx",
            "bye", "goodbye", "good bye", "see you", "see ya",
        }
        _greeting_responses = {
            "hi": "Hello! 👋 I'm your Entity AI assistant. How can I help you today?",
            "hello": "Hey there! 👋 Welcome to Entity AI. What would you like to know?",
            "hey": "Hey! 👋 How can I assist you today?",
            "good morning": "Good morning! ☀️ How can I help you today?",
            "good afternoon": "Good afternoon! How can I assist you?",
            "good evening": "Good evening! 🌆 What can I do for you?",
            "good night": "Good night! 🌙 Let me know if there's anything you need before you go.",
            "thanks": "You're welcome! 😊 Let me know if there's anything else I can help with.",
            "thank you": "You're welcome! 😊 Feel free to ask anything else.",
            "bye": "Goodbye! 👋 Have a great day!",
            "goodbye": "Goodbye! 👋 See you next time!",
        }
        _default_greeting = "Hello! 👋 I'm your Entity AI assistant. Ask me anything about your company data, strategy, or operations."

        cleaned = re.sub(r'[^\w\s\']', '', query.lower()).strip()
        if len(cleaned.split()) <= 4 and cleaned in _greeting_patterns:
            matched_response = _greeting_responses.get(cleaned, _default_greeting)
            logger.info(f"⚡ Instant greeting response for: '{query}'")

            async def _greeting_stream():
                yield matched_response

            return StreamingResponse(_greeting_stream(), media_type="text/plain")
        # --- END GREETING DETECTION ---

        # Map legacy models
        if model in MODEL_MAPPINGS:
            model = MODEL_MAPPINGS[model]
            
        logger.info(f"Incoming Request -> Model: {model}, Query: {query[:50]}...")
        
        if routing_controller is None:
            raise HTTPException(status_code=500, detail="Routing Controller not initialized.")

        return StreamingResponse(
            routing_controller.process_request(query, history, model), 
            media_type="text/plain"
        )

    except Exception as e:
        error_trace = traceback.format_exc()
        logger.error(f"Error in /ask endpoint: {e}")
        logger.error(error_trace)
        
        # Write to file for debugging
        log_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "server_error.log"))
        with open(log_file, "a") as f:
            f.write(f"\n--- Error at {str(e)} ---\n")
            f.write(error_trace)
            
        raise HTTPException(status_code=500, detail=str(e))



# Mount static files for UI
STATIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)
    
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)

