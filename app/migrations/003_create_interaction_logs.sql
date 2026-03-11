CREATE TABLE IF NOT EXISTS interaction_logs (
    id SERIAL PRIMARY KEY,
    user_query TEXT NOT NULL,
    detected_intent TEXT,
    route_taken TEXT,
    execution_time_ms INTEGER,
    patterns_detected JSONB,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
