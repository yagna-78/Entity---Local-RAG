"""
OPERATIONAL ENGINE — Employee Impact Analysis

Determines the operational consequences of employee changes:
- Which projects are affected
- Capacity drop by role
- Utilization overload risk
"""

import logging
from sqlalchemy import text
from typing import Dict, List

logger = logging.getLogger(__name__)


def operational_impact(conn, employee_name: str) -> Dict:
    """
    Calculates operational impact of removing a specific employee.
    Returns affected projects, capacity drop %, and overload risk.
    """
    # 1. Find employee (exact match first, then fuzzy)
    emp_row = conn.execute(
        text("SELECT id, role, department FROM employees WHERE LOWER(name) = LOWER(:name) AND status = 'active'"),
        {"name": employee_name}
    ).fetchone()

    if not emp_row:
        emp_row = conn.execute(
            text("SELECT id, role, department FROM employees WHERE LOWER(name) ILIKE :pattern AND status = 'active' LIMIT 1"),
            {"pattern": f"%{employee_name.lower()}%"}
        ).fetchone()

    if not emp_row:
        return {
            "affected_projects": [],
            "role": "Unknown",
            "department": "Unknown",
            "capacity_drop_pct": 0,
            "overload_risk": 0,
            "warning": f"Employee '{employee_name}' not found."
        }

    employee_id = emp_row[0]
    role = emp_row[1] or "Unknown"
    department = emp_row[2] or "Unknown"

    # 2. Find assigned projects
    project_rows = conn.execute(
        text("""
            SELECT p.project_name, pa.hours_allocated, pa.hours_logged
            FROM project_assignments pa
            JOIN projects p ON pa.project_id = p.id
            WHERE pa.employee_id = :eid
        """),
        {"eid": employee_id}
    ).fetchall()

    affected_projects = []
    for row in project_rows:
        affected_projects.append({
            "project_name": row[0],
            "hours_allocated": float(row[1] or 0),
            "hours_logged": float(row[2] or 0)
        })

    # 3. Calculate capacity drop
    # Critical roles get 100% capacity drop for their function
    critical_solo_roles = ["devops", "cto", "lead architect", "system admin"]
    if role.lower() in critical_solo_roles:
        # Check if they are the ONLY person with this role
        role_count = conn.execute(
            text("SELECT COUNT(*) FROM employees WHERE LOWER(role) = LOWER(:role) AND status = 'active'"),
            {"role": role}
        ).scalar() or 0

        if role_count <= 1:
            capacity_drop = 100.0  # Complete function loss
        else:
            capacity_drop = round(100.0 / role_count, 1)
    else:
        # For non-critical roles, capacity drop is proportional to team size
        dept_count = conn.execute(
            text("SELECT COUNT(*) FROM employees WHERE LOWER(department) = LOWER(:dept) AND status = 'active'"),
            {"dept": department}
        ).scalar() or 1

        capacity_drop = round(100.0 / dept_count, 1)

    # 4. Calculate overload risk (remaining team utilization)
    total_allocated = conn.execute(
        text("SELECT COALESCE(SUM(hours_allocated), 0) FROM project_assignments")
    ).scalar() or 0

    total_logged = conn.execute(
        text("SELECT COALESCE(SUM(hours_logged), 0) FROM project_assignments")
    ).scalar() or 0

    # Employee's allocation that will be redistributed
    emp_allocation = conn.execute(
        text("SELECT COALESCE(SUM(hours_allocated), 0) FROM project_assignments WHERE employee_id = :eid"),
        {"eid": employee_id}
    ).scalar() or 0

    # Remaining team's new load
    remaining_allocation = float(total_allocated)  # Work doesn't disappear
    remaining_capacity = float(total_allocated) - float(emp_allocation)  # Team capacity shrinks

    if remaining_capacity > 0:
        overload_risk = round((remaining_allocation / remaining_capacity) * 100, 1)
    else:
        overload_risk = 999.0  # Critical overload

    return {
        "employee_name": employee_name,
        "role": role,
        "department": department,
        "affected_projects": affected_projects,
        "capacity_drop_pct": capacity_drop,
        "overload_risk": min(overload_risk, 999.0)
    }
