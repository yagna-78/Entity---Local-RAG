-- Upgrades for Conversational Intelligence Layer

-- 1. Create User Profiles Table
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id TEXT PRIMARY KEY DEFAULT 'default_user',
    tone_preference TEXT DEFAULT 'balanced', -- 'formal', 'casual', 'concise', 'balanced'
    depth_preference TEXT DEFAULT 'adaptive', -- 'high_level', 'detailed', 'adaptive'
    math_strictness BOOLEAN DEFAULT TRUE,
    auto_correction_history JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Insert default user if not exists
INSERT INTO user_profiles (user_id) 
VALUES ('default_user') 
ON CONFLICT (user_id) DO NOTHING;

-- 2. Create KPI Corrections Table (Self-Learning)
CREATE TABLE IF NOT EXISTS kpi_corrections (
    id SERIAL PRIMARY KEY,
    kpi_code TEXT NOT NULL,
    corrected_value DECIMAL NOT NULL,
    original_value DECIMAL,
    justification TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    applied_count INTEGER DEFAULT 0
);

-- Index for fast lookup of latest correction
CREATE INDEX IF NOT EXISTS idx_kpi_corrections_code_time ON kpi_corrections (kpi_code, created_at DESC);

-- 3. Update Interaction Logs (Enhanced Logging)
ALTER TABLE interaction_logs ADD COLUMN IF NOT EXISTS response_mode TEXT;
ALTER TABLE interaction_logs ADD COLUMN IF NOT EXISTS satisfaction_score INTEGER;
ALTER TABLE interaction_logs ADD COLUMN IF NOT EXISTS tone_used TEXT;
