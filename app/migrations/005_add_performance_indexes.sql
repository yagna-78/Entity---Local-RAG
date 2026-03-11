-- Performance Indexes Migration
-- Speeds up all frequent queries across the pipeline

-- Revenue table: date-range and client lookups
CREATE INDEX IF NOT EXISTS idx_revenue_date ON revenue(revenue_date);
CREATE INDEX IF NOT EXISTS idx_revenue_client_id ON revenue(client_id);

-- Expenses table: date-range lookups
CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(expense_date);

-- Projects table: status filtering and client joins
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
CREATE INDEX IF NOT EXISTS idx_projects_client_id ON projects(client_id);

-- Project Assignments: employee lookups and project joins
CREATE INDEX IF NOT EXISTS idx_assignments_employee_id ON project_assignments(employee_id);
CREATE INDEX IF NOT EXISTS idx_assignments_project_id ON project_assignments(project_id);

-- Employees: status and role filtering
CREATE INDEX IF NOT EXISTS idx_employees_status ON employees(status);
CREATE INDEX IF NOT EXISTS idx_employees_role ON employees(role);

-- KPI Results: fast latest-value lookups
CREATE INDEX IF NOT EXISTS idx_kpi_results_calculated_at ON kpi_results(calculated_at);
CREATE INDEX IF NOT EXISTS idx_kpi_results_kpi_id ON kpi_results(kpi_id);

-- Interaction Logs: timestamp ordering
CREATE INDEX IF NOT EXISTS idx_interaction_logs_timestamp ON interaction_logs(created_at);
