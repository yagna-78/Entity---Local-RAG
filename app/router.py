
import logging
import json
import ollama
import time
from sqlalchemy import text
from decimal import Decimal
from typing import List, Dict, AsyncGenerator
from intent_classifier import IntentClassifier
from humanizer import Humanizer
from sql_agent import generate_and_execute_sql
import simulation_engine as scenario_orchestrator

# ... imports ...

# --- MODIFIED SYSTEM PROMPTS (STRUCTURED DATA ONLY) ---

PROMPT_DIAGNOSTIC = """
SYSTEM ROLE: Diagnostic Data Engine
OBJECTIVE: Analyze the provided context and return STRUCTURED FINDINGS.

-----------------------------------------
OUTPUT FORMAT (STRICT):
Return a set of clear, factual statements based on the data.
DO NOT use conversational filler.
DO NOT use headers like "## Analysis".
DO NOT use markdown formatting.
Just list the core findings.

Example:
- Revenue dropped 15% in Q3 due to churn.
- Customer X is the primary driver of this loss.
- Pattern detected: High churn in region Y.
-----------------------------------------
YOUR DATA:
"""

PROMPT_HYBRID = """
SYSTEM ROLE: Strategic Logic Core
OBJECTIVE: Provide a structured strategic breakdown based on data.

-----------------------------------------
OUTPUT FORMAT (STRICT JSON-LIKE STRUCTURE):
Identify Structural Weakness: [Text]
Quantify Risk: [Numbers/Text]
Propose Concrete Change: [Actionable Step]
Explain Financial Impact: [Financial Projection]

DO NOT write a paragraph.
DO NOT use introduction or conclusion.
JUST DATA POINTS.
-----------------------------------------
"""

from insight_layer import analyze_data
import knowledge_engine
from complexity_classifier import ComplexityClassifier
from fast_sql import FastSQLExecutor
from context_detector import CompanyContextDetector
from pattern_engine import PatternEngine
from database import engine
import memory_engine
import kpi_engine
import random

# --- User Profile & Memory Helpers ---

def get_user_profile(user_id: str = "default_user") -> Dict:
    try:
        if not engine: return {}
        with engine.connect() as conn:
            row = conn.execute(text("SELECT * FROM user_profiles WHERE user_id = :uid"), {"uid": user_id}).fetchone()
            if row:
                return dict(row._mapping)
    except Exception as e:
        logger.error(f"Profile Fetch Error: {e}")
    return {"tone_preference": "balanced", "depth_preference": "adaptive"}

# PROMPT_SIMULATION is DELETED.
# All financial computation now happens in financial_engine.py (deterministic).
# The LLM only receives pre-computed JSON for humanization.

PROMPT_SCENARIO_HUMANIZER = """
You are an executive communications assistant.
You have received PRE-COMPUTED scenario simulation results as structured JSON.

STRICT RULES:
1. You are NOT allowed to modify any numeric values.
2. You are NOT allowed to recalculate financial metrics.
3. You are NOT allowed to infer revenue causality.
4. You are NOT allowed to add assumptions or fabricate data.
5. All monetary values must use INR (₹).
6. If the question asks "can we afford" or "is it profitable enough" or "should we", give a clear YES or NO answer FIRST, then explain using the data. Base your answer on whether the net margin remains positive after the simulated change.

You ARE allowed to:
- Explain implications of the numbers
- Summarize the financial, operational, and risk impact
- Suggest actions based on the risk assessment
- Answer YES/NO feasibility questions using the pre-computed data

Format your response as a clear, direct executive briefing.
Do NOT use headers, markdown, or bullet lists.
Write in natural paragraphs. Start directly with the key insight.
"""

def determine_route(query: str) -> str:
    """
    Deterministically routes the query based on specific keywords.
    SCENARIO requires hypothesis framing (what if, what happens if, simulate).
    Bare keywords like 'fire' or 'hire' alone route to DATABASE for analysis.
    Advisory/how-to questions route to STRATEGIC (PDF knowledge base).
    """
    q_lower = query.lower()
    
    # SCENARIO: Hypothesis framing, affordability checks, and budget change simulations
    scenario_triggers = [
        # Classic what-if
        "what if",
        "what happens if",
        "what would happen",
        "simulate",
        # Impact analysis
        "impact of firing",
        "impact of hiring",
        "impact of cancelling",
        # Conditional
        "if we fire",
        "if we hire",
        "if we cancel",
        "if we remove",
        "if we lose",
        "if we let go",
        "if we terminate",
        "if we add",
        # Affordability / feasibility
        "can we afford",
        "afford to hire",
        "enough to hire",
        "profitable enough",
        "can we hire",
        "should we hire",
        "should we fire",
        "should we cancel",
        # Budget/expense changes with percentages
        "increases by",
        "increase by",
        "decrease by",
        "decreases by",
        "reduce by",
        "cut by",
        "drop by",
        "grows by",
        # Runway / burn rate / sustainability
        "burn rate",
        "runway",
        "can we survive",
        "survive for",
        "sustain for",
        "last for",
        "enough cash",
        "enough money",
    ]
    if any(trigger in q_lower for trigger in scenario_triggers):
        return "SCENARIO"
        
    if any(k in q_lower for k in ["risk", "problem", "issue", "why", "diagnose"]):
        return "INSIGHT"
        
    if any(k in q_lower for k in ["kpi", "utilization", "concentration"]):
        return "KPI"
    
    # STRATEGIC/ADVISORY: Questions seeking guidance, advice, or best practices
    # These should use the PDF knowledge base, not the database
    advisory_keywords = [
        "what should i do", "what should we do", "how should i", "how should we",
        "how to handle", "how to deal", "how to manage", "how to improve",
        "how to resolve", "how to fix", "how to approach",
        "best practice", "best way to", "advice", "recommend",
        "tips for", "guide", "suggestion", "help me with",
        "refusing", "conflict", "negotiate", "escalat",
        "retention", "motivation", "onboarding",
        "should we focus", "should we prioritize", "should we invest",
        "should we expand", "should we consider",
        "is it better to", "which is better",
        "acquiring or retaining", "acquire or retain",
    ]
    if any(k in q_lower for k in advisory_keywords):
        return "STRATEGIC"
        
    if any(k in q_lower for k in ["strategy", "positioning", "framework", "theory"]):
        return "STRATEGIC"
        
    # DATABASE: Catches everything data-related including 'fire', 'hire', 'performance'
    return "DATABASE"

def build_system_context(mode: str, profile: Dict, memory: str) -> str:
    """
    Step 4: User Profile Adaptation & Memory Injection
    """
    tone = profile.get("tone_preference", "balanced")
    
    base_instructions = ""
    if mode == "CONVERSATIONAL":
        base_instructions = (
            "You are Entity, a COO-level Operator. "
            "Speak naturally but decisively. "
            "Do NOT use headers for simple chats. "
            "Be concise, direct, and action-oriented. "
            "STRICTLY USE INR (₹) for all monetary values."
        )
    elif mode == "ANALYTICAL":
        base_instructions = (
            "You are a Data Operations Lead. "
            "Focus strictly on the numbers and facts provided. "
            "Provide clear, binary assessments based on data. "
            "STRICTLY USE INR (₹) for all monetary values."
        )
    else: # STRATEGIC
        base_instructions = (
            "You are a Chief Operating Officer (COO). "
            "Make executive decisions based on constraints and data. "
            "Avoid generic frameworks. "
            "Focus on execution, risk, and resource allocation. "
            "STRICTLY USE INR (₹) for all monetary values."
        )

    # Tone Injection
    if tone == "casual":
        base_instructions += " Use a relaxed, friendly tone."
    elif tone == "formal":
        base_instructions += " Maintain a strictly professional, executive tone."
        
    # Memory Injection
    if memory:
        base_instructions += f"\\n\\nRECENT CONTEXT:\\n{memory}"
        
    return base_instructions


logger = logging.getLogger(__name__)


# Custom JSON Encoder for Decimal and DateTime
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return super(DecimalEncoder, self).default(obj)

# --- System Prompts for Enforced Formats ---

# --- Dynamic Prompt Builders ---


# --- SIMPLIFIED PROMPT BUILDERS (STRUCTURED OUTPUT) ---

def build_informational_prompt(has_data: bool) -> str:
    # Informational queries can remain direct for now, or optionally be humanized.
    # Given the architecture, we'll keep them simple but direct.
    base = (
        "You are a Data Assistant. "
        "Return the requested information directly. "
        "STRICTLY USE INR (₹) for all monetary values."
    )
    if not has_data:
        base += "\\nNote: No direct database results found."
    return base

def build_diagnostic_prompt(has_data: bool, has_patterns: bool) -> str:
    # Returns the strict diagnostic prompt
    return PROMPT_DIAGNOSTIC

def build_hybrid_prompt(has_data: bool, has_patterns: bool) -> str:
    # Returns the strict hybrid prompt
    return PROMPT_HYBRID

PROMPT_THEORY = (
    "You are a Strategic Business Theorist. "
    "Use the provided Knowledge Base to explain concepts. "
    "STRICTLY USE INR (₹) for all monetary values."
)

PROMPT_GENERAL = (
    "You are a helpful assistant for Entity. "
    "Keep the conversation professional. "
    "STRICTLY USE INR (₹) for all monetary values."
)

PROMPT_OPERATIONAL_MODE = """
SYSTEM: Operational Decision Engine. Company-specific, data-first.

PRIORITY: DB facts > Calculations > Patterns > PDFs (only if DB empty) > Theory (only if asked).

RULES:
- Use actual company data. No generic frameworks unless asked.
- Revenue = Clients + Projects ONLY. Employees do NOT own revenue.
- Employee removal reduces salary cost, NOT revenue.
- Block PDF retrieval if DB can answer.
- Use INR (₹) for all monetary values.

FORMAT: Direct, numeric, operational. Structure: Problem → Impact → Action → Financial Outcome.
"""

class RoutingController:
    def __init__(self, model_name: str = "mistral:latest"):
        self.model_name = model_name
        self.fast_executor = FastSQLExecutor()
        self.context_detector = CompanyContextDetector()
        self.pattern_engine = PatternEngine()
        self.humanizer = Humanizer(model_name) # Layer 2
        
        # Ensure Knowledge Engine is ready
        knowledge_engine.initialize_resources()
        
        # Phase 9: Initialize LLM client once
        self.llm_client = ollama.AsyncClient(host='http://127.0.0.1:11434')

    async def _generate_core_logic(self, messages: List[Dict[str, str]], model: str = None) -> str:
        """
        Layer 1: Generates deterministic, structured output. Does NOT stream.
        """
        target_model = model if model else self.model_name
        options = {"num_predict": 1024, "temperature": 0.1, "repeat_penalty": 1.1}
        response = await self.llm_client.chat(model=target_model, messages=messages, options=options)
        return response['message']['content']

    async def _stream_standard(self, messages: List[Dict[str, str]], sources: List[str] = [], model: str = None) -> AsyncGenerator[str, None]:
        """
        Standard streaming for purely conversational or theoretical queries (Bypasses Humanizer).
        """
        target_model = model if model else self.model_name
        try:
            options = {"num_predict": 1024, "temperature": 0.3, "repeat_penalty": 1.1}
            async for chunk in await self.llm_client.chat(model=target_model, messages=messages, stream=True, options=options):
                if chunk['message']['content']:
                    yield chunk['message']['content']
            
            if sources:
                yield "\n\n---\n**Sources:**\n"
                for source in sources:
                    yield f"- {source}\n"
        except Exception as e:
            logger.error(f"Generation Error: {e}")
            yield f"\\n[Generation Error: {str(e)}]"

    async def _stream_humanized(self, raw_structured_data: str, sources: List[str] = []) -> AsyncGenerator[str, None]:
        """
        Layer 2: Takes structured data and streams natural language.
        """
        logger.info(f"Layer 1 Output (Raw): {raw_structured_data}")
        try:
            async for chunk in self.humanizer.process(raw_structured_data):
                yield chunk
            
            if sources:
                yield "\\n\\n---\\n**Sources:**\\n"
                for source in sources:
                    yield f"- {source}\\n"
        except Exception as e:
            logger.error(f"Humanization Error: {e}")
            yield f"\\n[Humanization Error: {str(e)}]"

    def _log_interaction(self, query: str, intent: str, route: str, execution_time_ms: int, patterns: List[dict] = None, error: str = None):
        """
        Logs the interaction to the database in a fail-safe manner.
        """
        try:
            print("Logging interaction...") # Debug Verification
            if not engine:
                logger.error("Database engine not available for logging.")
                return

            with engine.connect() as conn:
                stmt = text("""
                    INSERT INTO interaction_logs 
                    (user_query, detected_intent, route_taken, execution_time_ms, patterns_detected, error_message)
                    VALUES (:query, :intent, :route, :exec_time, :patterns, :error)
                """)
                conn.execute(stmt, {
                    "query": query,
                    "intent": intent,
                    "route": route,
                    "exec_time": execution_time_ms,
                    "patterns": json.dumps(patterns) if patterns else None,
                    "error": error
                })
                conn.commit()
            print("Interaction logged successfully") # Debug Verification
        except Exception as e:
            logger.error(f"FAILED TO LOG INTERACTION: {e}")
            # Do NOT crash the main request.

    async def process_request(self, query: str, history: List[dict], model: str = "mistral:latest") -> AsyncGenerator[str, None]:
        logger.info(f"Processing Query: {query} [Model: {model}]")
        
        start_time = time.time()
        intent = "UNKNOWN"
        route_taken = "UNKNOWN"
        patterns_detected = []
        error_message = None
        full_response_text = ""

        try:
            # 0. Perf: Route timing
            t_route = time.time()
            route = determine_route(query)
            route_ms = int((time.time() - t_route) * 1000)
            route_taken = f"Deterministic: {route}"
            logger.info(f"⚡ Route: {route} ({route_ms}ms)")
            intent = route
            
            # 1. Dispatch to proper engine
            if route == "SCENARIO":
                async for chunk in self.handle_simulation(query, history, model):
                    full_response_text += chunk
                    yield chunk
                    
            elif route == "DATABASE":
                async for chunk in self.handle_database(query, history, model):
                    full_response_text += chunk
                    yield chunk
                    
            elif route == "KPI":
                async for chunk in self.handle_kpi(query, history, model):
                    full_response_text += chunk
                    yield chunk
                    
            elif route == "INSIGHT":
                async for chunk in self.handle_insight(query, history, model):
                    full_response_text += chunk
                    yield chunk
                    
            elif route == "STRATEGIC":
                async for chunk in self.handle_strategic_rag(query, history, model):
                    full_response_text += chunk
                    yield chunk

        except Exception as e:
            error_message = str(e)
            err = f"\n[Router Error: {str(e)}]"
            logger.error(err)
            yield err
        
        finally:
            # PERF LOGGING
            execution_time = int((time.time() - start_time) * 1000)
            if execution_time > 10000:
                logger.warning(f"⚠️ SLOW QUERY: {execution_time}ms | Route: {route_taken} | Query: {query[:80]}")
            else:
                logger.info(f"✅ Query complete: {execution_time}ms | Route: {route_taken}")
            
            self._log_interaction(query, intent, route_taken, execution_time, patterns_detected, error_message)
            
            # Store exchange in memory
            if full_response_text and len(full_response_text) > 10:
                memory_engine.store_exchange(query, full_response_text, {"intent": intent})

    # --- NEW PHASE-BASED HANDLERS ---
    
    async def _resolve_followup_query(self, query: str, history: List[dict]) -> str:
        """
        Detects pronouns/references in the query and rewrites it using
        conversation history so the SQL generator gets a self-contained question.
        e.g. "which department does she belong to" -> "which department does Riya Patel belong to"
        """
        q_lower = query.lower()
        pronouns = [
            " she ", " he ", " her ", " his ", " him ", " they ", " them ", " their ",
            " this person", " that person", " this employee", " that employee",
            " this client", " that client", " this project", " that project",
            " the same ",
        ]
        # Also check if query starts with a pronoun
        starts_with = ["she ", "he ", "her ", "his ", "they ", "them "]
        
        has_pronoun = any(p in f" {q_lower} " for p in pronouns) or any(q_lower.startswith(s) for s in starts_with)
        
        if not has_pronoun or not history:
            return query
        
        # Gather last 3 exchanges from history for context
        recent_context = []
        count = 0
        for msg in reversed(history):
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                recent_context.insert(0, f"{role.capitalize()}: {content[:300]}")
                if role == "user":
                    count += 1
                if count >= 3:
                    break
        
        if not recent_context:
            return query
        
        conversation_context = "\n".join(recent_context)
        
        try:
            rewrite_messages = [
                {"role": "system", "content": (
                    "You are a query rewriter. The user is asking a follow-up question that contains "
                    "pronouns (she, he, they, etc.) or references (this person, that client, etc.). "
                    "Rewrite the question by replacing pronouns with the actual names/entities from the conversation context. "
                    "Output ONLY the rewritten question, nothing else. "
                    "If there is no pronoun to resolve, output the original question unchanged."
                )},
                {"role": "user", "content": (
                    f"Conversation context:\n{conversation_context}\n\n"
                    f"Current question: {query}\n\n"
                    f"Rewritten question:"
                )}
            ]
            resp = await self.llm_client.chat(
                model="qwen2.5:7b",
                messages=rewrite_messages,
                options={"temperature": 0.0, "num_predict": 100}
            )
            rewritten = resp['message']['content'].strip()
            # Basic sanity: must be a question-like string, not too long
            if rewritten and len(rewritten) < 300 and len(rewritten) > 5:
                logger.info(f"🔄 Query rewritten: '{query}' -> '{rewritten}'")
                return rewritten
        except Exception as e:
            logger.error(f"Query rewrite failed: {e}")
        
        return query

    async def handle_database(self, query: str, history: List[dict], model: str):
        logger.info("DB ENGINE: Single LLM call")
        try:
            # Step 0: Resolve pronouns/references from conversation history
            resolved_query = await self._resolve_followup_query(query, history)
            
            t_db = time.time()
            # SQL generation uses qwen2.5:7b (code model), response uses user's chat model
            success, raw_result, sql_query = await generate_and_execute_sql(resolved_query)  # defaults to qwen2.5:7b
            db_ms = int((time.time() - t_db) * 1000)
            logger.info(f"⚡ SQL executed: {db_ms}ms | Success: {success} | SQL: {sql_query}")
            
            if not success:
                logger.warning(f"SQL Agent failed: {raw_result} | Generated SQL: {sql_query}")
            
            # Build data context — NEVER expose SQL to the LLM/user
            data_context = ""
            if success and raw_result and len(raw_result) > 0 and str(raw_result) != "[]":
                data_context = f"Database Results:\n{raw_result}"
            elif success:
                data_context = "The query returned no matching records."
            else:
                data_context = "Unable to retrieve data for this question."
                
            # SINGLE LLM CALL: Combine data + humanization
            system_msg = (
                "You are an executive operations assistant. Give DECISIVE, DATA-DRIVEN answers. "
                "STRICT RULES: "
                "1. ONLY use numbers that appear in the provided data. NEVER invent numbers. "
                "2. NEVER fabricate statistics like 'industry standard', 'average tickets', or cost estimates unless they appear in the data. "
                "3. For workload/overtime: overtime = hours_logged - hours_allocated. If overtime_hours is positive, the person worked MORE than allocated (OVERTIME). Report both total_allocated, total_logged, and the overtime difference. "
                "4. Give a clear YES/NO recommendation when question asks 'should we'. Cite the exact numbers from data. "
                "5. NEVER show SQL, table names, or column names. "
                "6. Use INR (₹) ONLY for monetary values (salary, revenue, expenses, budget, cost). Use 'hours' as the unit for time-based values (hours_allocated, hours_logged, overtime_hours, duration). NEVER label hours as INR. "
                "7. For yes/no questions: be concise (2-3 sentences). For list/detail questions: include ALL rows from the data, do not truncate. "
                "8. NEVER use markdown tables (| --- | format). Use numbered lists or bullet points instead. "
                "9. ONLY answer the specific question asked. Do NOT add unrelated data or analysis the user did not ask for. "
                "10. NEVER use placeholder text like [value1], [name], [date1], etc. Only use REAL data from the results. "
                "11. If the data shows NO matching records, simply state that clearly in ONE sentence. Do NOT invent example data or templates. "
                "12. For FORECAST/PREDICT questions: if historical monthly data is provided, calculate the average monthly value and project it forward. State the trend clearly and provide the projected numbers with the calculation method used."
            )
            user_msg = f"{data_context}\n\nQuestion: {query}"
            messages = [{'role': 'system', 'content': system_msg}, {'role': 'user', 'content': user_msg}]
            
            async for chunk in self._stream_standard(messages, sources=[], model=model):
                yield chunk
        except Exception as e:
            yield f"Error in Database Engine: {str(e)}"

    async def handle_kpi(self, query: str, history: List[dict], model: str):
        logger.info("KPI ENGINE: Single LLM call")
        try:
            t_db = time.time()
            with engine.connect() as conn:
                results = conn.execute(text("""
                    SELECT d.kpi_code, r.actual_value, r.status
                    FROM kpi_results r
                    JOIN kpi_definitions d ON r.kpi_id = d.id
                    WHERE r.calculated_at = (SELECT MAX(calculated_at) FROM kpi_results r2 WHERE r2.kpi_id = r.kpi_id)
                """)).fetchall()
                kpi_data = "\n".join([f"{r[0]}: {r[1]} ({r[2]})" for r in results])
            db_ms = int((time.time() - t_db) * 1000)
            logger.info(f"⚡ KPI fetch: {db_ms}ms")
                
            # SINGLE LLM CALL
            system_msg = (
                "You are a KPI analyst. Present the requested KPI clearly and directly. "
                "Do NOT change numbers. Use INR (₹). No headers, no fluff."
            )
            user_msg = f"Available KPIs:\n{kpi_data}\n\nQuestion: {query}"
            messages = [{'role': 'system', 'content': system_msg}, {'role': 'user', 'content': user_msg}]
            
            async for chunk in self._stream_standard(messages, sources=[], model=model):
                yield chunk
        except Exception as e:
            yield f"Error in KPI Engine: {str(e)}"

    async def handle_insight(self, query: str, history: List[dict], model: str):
        logger.info("INSIGHT ENGINE: Single LLM call")
        try:
            from insight_engine import InsightEngine
            t_db = time.time()
            with engine.connect() as conn:
                results = conn.execute(text("""
                    SELECT d.kpi_code, r.actual_value
                    FROM kpi_results r
                    JOIN kpi_definitions d ON r.kpi_id = d.id
                    WHERE r.calculated_at = (SELECT MAX(calculated_at) FROM kpi_results r2 WHERE r2.kpi_id = r.kpi_id)
                """)).fetchall()
                kpis = {r[0].lower(): float(r[1]) for r in results}
                
            insights = InsightEngine.generate_insights(kpis)
            insights_json = json.dumps(insights, indent=2)
            db_ms = int((time.time() - t_db) * 1000)
            logger.info(f"⚡ Insight compute: {db_ms}ms")
            
            # SINGLE LLM CALL
            system_msg = (
                "You are an executive diagnostic assistant. Translate the JSON insights into a clear, direct briefing. "
                "Do NOT change numbers. Use INR (₹). No headers. Start directly with the most critical issue."
            )
            user_msg = f"Insight Data:\n{insights_json}\n\nQuestion: {query}"
            messages = [{'role': 'system', 'content': system_msg}, {'role': 'user', 'content': user_msg}]
            
            async for chunk in self._stream_standard(messages, sources=[], model=model):
                yield chunk
        except Exception as e:
            yield f"Error in Insight Engine: {str(e)}"

    async def handle_strategic_rag(self, query: str, history: List[dict], model: str):
        logger.info("PHASE 7: STRATEGIC RAG HANDLING")
        try:
            # Gated retrieval: Top 3 chunks max
            context, sources = knowledge_engine.retrieve_context(query, n_results=3)
            
            system_msg = "Answer the strategic query based strictly on the provided knowledge chunks. No operational DB data."
            user_msg = f"Knowledge Context:\n{context}\n\nUser Question: {query}"
            
            messages = [{'role': 'system', 'content': system_msg}, {'role': 'user', 'content': user_msg}]
            
            # Bypass humanizer for raw RAG answers
            async for chunk in self._stream_standard(messages, sources, model=model):
                yield chunk
        except Exception as e:
            yield f"Error in Strategic RAG Engine: {str(e)}"
            
    def enforce_self_check(self, raw_data: str, query: str, route: str) -> str:
        """
        Phase 10: Self-Check Enforcement
        """
        issues = []
        lower_raw = raw_data.lower()
        
        # Scenario Causality check
        if route == "SCENARIO":
            if "decreased revenue" in lower_raw and "employee" in query.lower():
                issues.append("Violation: Employee change modified revenue.")
                
        # Universal Causality check
        if any(phrase in lower_raw for phrase in ["revenue share", "revenue ownership", "attributed to employee", "employee generates"]):
             issues.append("Violation: Inferred revenue ownership by employee. Financial and operational layers must remain isolated.")
        
        if "framework" in lower_raw and route == "DATABASE":
             issues.append("Violation: Used unnecessary theoretical framework in DB query.")
             
        if issues:
             logger.warning(f"Self-Check Violations Detected: {issues}")
             return f"[Self-Check Intervened: Calculation Aborted. Correcting logic: Financial layer must remain isolated from operational layer. {issues}]"
        return raw_data

    async def handle_informational(self, query: str, history: List[dict], model: str, intent: str = "DATA_ANALYSIS"):
        logger.info(f"Handling INFORMATIONAL request (Minimal Path) - Intent: {intent}...")
        try:
            # 1. Fast Path (SQL)
            complexity = self.complexity_classifier.classify(query)
            if complexity["complexity"] == "SIMPLE" and intent != "THEORY":
                try:
                    result = self.fast_executor.execute(complexity["intent"], complexity["params"])
                    if result:
                        yield result # Direct result, no fluff
                        return
                except Exception:
                    pass

            # 2. Determine Source (SQL vs RAG)
            context_text = ""
            has_data = False
            
            if intent == "THEORY":
                 # RAG Path for Informational Theory
                 rag_context, sources = knowledge_engine.retrieve_context(query, n_results=3)
                 context_text = f"Context (Knowledge Base):\\n{rag_context}\\n"
                 has_data = True # Context is data here
            else:
                # SQL Path for Data/Hybrid Informational
                success, raw_result, sql_query = await generate_and_execute_sql(query, model)
                if success and raw_result and len(raw_result) > 0 and str(raw_result) != "[]":
                    has_data = True
                    context_text = f"Data Results:\\n{raw_result}\\n"
                else:
                    has_data = False
                    context_text = "Data Results: No relevant data found in database."

            # 3. Generate Concise Response
            system_msg = build_informational_prompt(has_data)
            user_msg = f"{context_text}\\n\\nUser Question: {query}"
            
            messages = [{'role': 'system', 'content': system_msg}]
            messages.append({'role': 'user', 'content': user_msg})
            
            # Informational uses standard streaming as it's already simple text
            async for chunk in self._stream_standard(messages, sources=[], model=model):
                yield chunk

        except Exception as e:
            logger.error(f"Informational Error: {e}")
            yield "I couldn't find that information."

    async def handle_diagnostic(self, query: str, history: List[dict], model: str):
        logger.info("Handling DIAGNOSTIC request (Pattern Aware)...")
        try:
            # 1. SQL & Analysis
            success, raw_result, sql_query = await generate_and_execute_sql(query, model)
            data_context = ""
            has_data = False
            
            if success and raw_result and len(raw_result) > 0 and str(raw_result) != "[]":
                 has_data = True
                 analysis = analyze_data(raw_result)
                 data_context = f"Data Analysis:\\n{json.dumps(analysis, cls=DecimalEncoder)}\\n"
            else:
                 data_context = "No data found."

            # 2. Pattern Engine (Allowed)
            patterns = self.pattern_engine.run_analysis()
            pattern_context = ""
            has_patterns = False
            
            if patterns:
                has_patterns = True
                pattern_list = [f"- {p['pattern']} (Signals: {p['trigger_signals']})" for p in patterns]
                pattern_context = "Detected Patterns:\\n" + "\\n".join(pattern_list) + "\\n"
            
            # 3. Generate Response
            system_msg = build_diagnostic_prompt(has_data, has_patterns)
            user_msg = f"{data_context}\\n{pattern_context}\\n\\nUser Question: {query}"
            
            messages = [{'role': 'system', 'content': system_msg}]
            messages.append({'role': 'user', 'content': user_msg})
            
            # Diagnostic produces structured findings -> Humanize it
            raw_data = await self._generate_core_logic(messages, model=model)
            async for chunk in self._stream_humanized(raw_data, sources=[]):
                yield chunk

        except Exception as e:
            logger.error(f"Diagnostic Error: {e}")
            yield f"Error analyzing data: {str(e)}"
                
    async def handle_simulation(self, query: str, history: List[dict], model: str):
        logger.info("SCENARIO ENGINE: Deterministic + Single LLM call")
        try:
            # 1. Run deterministic scenario orchestrator (NO LLM math)
            t_engine = time.time()
            with engine.connect() as conn:
                result = scenario_orchestrator.run_scenario(conn, query)
            engine_ms = int((time.time() - t_engine) * 1000)
            logger.info(f"⚡ Scenario engine: {engine_ms}ms")

            # 2. Check for errors from the engines
            if "error" in result:
                yield f"Scenario Error: {result['error']}"
                return

            # 3. Format pre-computed JSON
            result_json = json.dumps(result, indent=2, cls=DecimalEncoder)
            logger.info(f"Scenario Output (Deterministic): {result_json[:200]}...")

            # 4. SINGLE LLM CALL for humanization (no computation)
            system_msg = PROMPT_SCENARIO_HUMANIZER
            user_msg = f"Pre-computed scenario results:\n{result_json}\n\nOriginal question: {query}"
            messages = [{'role': 'system', 'content': system_msg}, {'role': 'user', 'content': user_msg}]
            
            async for chunk in self._stream_standard(messages, sources=[], model=model):
                yield chunk

        except Exception as e:
            err = f"\n[Simulation Error: {str(e)}]"
            logger.error(err)
            yield err

    async def handle_theory(self, query: str, history: List[dict], model: str):
        logger.info("Handling THEORY request...")
        try:
            context, sources = knowledge_engine.retrieve_context(query, n_results=6)
            
            system_msg = PROMPT_THEORY
            user_msg = f"Context (PDF Knowledge Base):\\n{context}\\n\\nUser Question: {query}"
            
            messages = [{'role': 'system', 'content': system_msg}]
            
            # Let's add last turn of history if it exists and is user
            if history and history[-1]['role'] == 'user':
                pass # current query is user_msg
            
            messages.append({'role': 'user', 'content': user_msg})
            
            # Theory is natural text -> Standard stream
            async for chunk in self._stream_standard(messages, sources, model=model):
                yield chunk
        except Exception as e:
            err = f"\\n[Theorist Error: {str(e)}]"
            logger.error(err)
            yield err

    async def handle_data(self, query: str, history: List[dict], model: str):
        """
        Legacy/Reference Data Handler - Now largely superseded by handle_diagnostic or handle_informational,
        but kept for routing compatibility if strictly DATA_ANALYSIS is picked without INFORMATIONAL depth.
        """
        # We can map this to Diagnostic for now as default
        async for chunk in self.handle_diagnostic(query, history, model):
            yield chunk

    def validate_hybrid_response(self, content: str, has_data: bool, has_patterns: bool) -> bool:
        """
        Validates that the response follows the strict Operational COO format.
        """
        required_headers = [
            "1. Identify Structural Weakness",
            "2. Quantify Risk",
            "3. Propose Concrete Change",
            "4. Explain Financial Impact"
        ]
        
        # Check for headers
        for header in required_headers:
            if header not in content:
                logger.warning(f"Operational Validation Failed: Missing header '{header}'")
                return False

        return True

    async def handle_hybrid(self, query: str, history: List[dict], model: str):
        logger.info("Handling HYBRID request (Strict Operational Pipeline)...")
        
        # --- 0. Complexity Check (Fast SQL Path) ---
        complexity = self.complexity_classifier.classify(query)
        
        if complexity["complexity"] == "SIMPLE":
            logger.info(f"🚀 FAST PATH Triggered (Hybrid): {complexity['intent']}")
            try:
                result = self.fast_executor.execute(complexity["intent"], complexity["params"])
                if result:
                    yield f"⚡ **Fast Data**\\n\\n{result}"
                    return
            except Exception as e:
                logger.error(f"Fast Path Failed: {e}. Falling back to standard path.")
        # -------------------------------------------

        try:
            # Step 1: Mandatory Database Extraction
            success, raw_result, sql_query = await generate_and_execute_sql(query, model)
            
            data_context = ""
            has_data = False
            if success and raw_result and len(raw_result) > 0 and str(raw_result) != "[]":
                has_data = True
                analysis = analyze_data(raw_result)
                data_context = f"Internal Data Extraction:\\n{json.dumps(analysis, indent=2, cls=DecimalEncoder)}\\n"
            else:
                data_context = "Internal Data Extraction: No relevant data found in database.\\n"

            # Step 2: Run Pattern Analysis
            patterns = self.pattern_engine.run_analysis()
            pattern_context = ""
            has_patterns = False
            
            if patterns:
                has_patterns = True
                pattern_list = []
                for p in patterns:
                    pattern_list.append(f"- {p['pattern']} (Confidence: {p['confidence']}%, Project ID: {p['project_id']})")
                    pattern_list.append(f"  Signals: {json.dumps(p['trigger_signals'], cls=DecimalEncoder)}")
                
                pattern_context = "## 🔍 DETECTED RISK PATTERNS (CRITICAL):\\n" + "\\n".join(pattern_list) + "\\n\\n"
            else:
                pattern_context = "No specific risk patterns detected.\\n\\n"

            # Step 3: Retrieval Gating (Block PDFs if Data Exists)
            rag_context = ""
            sources = []
            
            # CRITICAL: If we have hard numbers, we DO NOT look at PDFs unless explicitly asked for theory
            if has_data:
                logger.info("Operational Mode: Data detected. Blocking PDF retrieval to prevent generic theory.")
                rag_context = "Note: PDF Retrieval BLOCKED because database data is sufficient."
            else:
                 logger.info("Operational Mode: No data found. Falling back to Knowledge Base.")
                 rag_txt, sources = knowledge_engine.retrieve_context(query, n_results=3)
                 if rag_txt:
                     rag_context = f"Strategic Context (Knowledge Base):\\n{rag_txt}\\n"
                 else:
                     rag_context = "No relevant knowledge or data found."

            combined_context = (
                f"{data_context}\\n\\n"
                f"{pattern_context}\\n"
                f"{rag_context}\\n"
            )
            
            # Use the new Operational Prompt
            system_msg = PROMPT_OPERATIONAL_MODE
            user_msg = f"Context:\\n{combined_context}\\n\\nUser Question: {query}"
            
            messages = [{'role': 'system', 'content': system_msg}]
            messages.append({'role': 'user', 'content': user_msg})
            
            # Hybrid produces strict operational structure -> Humanize it
            raw_data = await self._generate_core_logic(messages, model=model)
            
            sources_to_yield = []
            if has_data:
                sources_to_yield.append("Company Database (PostgreSQL)")
            sources_to_yield.extend(sources)
            
            async for chunk in self._stream_humanized(raw_data, sources=sources_to_yield):
                yield chunk

        except Exception as e:
            err = f"\\n[Operational Engine Error: {str(e)}]"
            logger.error(err)
            yield err

    async def handle_general(self, query: str, history: List[dict], model: str, system_override: str = None):
        logger.info("Handling GENERAL request...")
        try:
            sys_msg = system_override if system_override else PROMPT_GENERAL
            messages = [{'role': 'system', 'content': sys_msg}]
            
            if history:
                 for h in history[-4:]:
                    if h['role'] in ['user', 'assistant']:
                        messages.append({'role': h['role'], 'content': h['content']})
            
            messages.append({'role': 'user', 'content': query})
            
            # General conversation -> Standard stream
            async for chunk in self._stream_standard(messages, model=model):
                yield chunk
        except Exception as e:
            err = f"\\n[General Chat Error: {str(e)}]"
            logger.error(err)
            yield err
