"""
routers/projects.py — Project (workspace) management.

POST   /projects              — create a new project
GET    /projects              — list all projects for current user
GET    /projects/{id}         — get one project
DELETE /projects/{id}         — delete a project

C1: Creator is automatically added as admin in project_members on creation.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth.dependencies import get_current_user
from database import get_pool

router = APIRouter(prefix="/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    name: str
    description: str | None = None


@router.post("")
async def create_project(
    body: CreateProjectRequest,
    user: dict = Depends(get_current_user),  # noqa: B008
):
    """
    Create a new project for the current user.
    C1: Creator is automatically inserted as admin in project_members.
    """
    project_id = str(uuid.uuid4())
    member_id  = str(uuid.uuid4())

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO projects (project_id, user_id, name, description)
            VALUES ($1, $2, $3, $4)
        """, project_id, user["user_id"], body.name, body.description)

        # Automatically make the creator an admin
        await conn.execute("""
            INSERT INTO project_members (member_id, project_id, user_id, role)
            VALUES ($1, $2, $3, 'admin')
            ON CONFLICT (project_id, user_id) DO NOTHING
        """, member_id, project_id, user["user_id"])

    return {
        "project_id":  project_id,
        "name":        body.name,
        "description": body.description,
        "your_role":   "admin",
    }


@router.get("")
async def list_projects(
    user: dict = Depends(get_current_user),  # noqa: B008
):
    """
    List all projects where the current user is a member.
    C1: Uses project_members to find projects, not just owned ones.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT p.project_id, p.name, p.description, p.created_at,
                   pm.role,
                   (SELECT COUNT(*) FROM traces WHERE traces.project_id = p.project_id) AS trace_count
            FROM projects p
            JOIN project_members pm ON pm.project_id = p.project_id
            WHERE pm.user_id = $1
            ORDER BY p.created_at DESC
        """, user["user_id"])
    return [dict(row) for row in rows]


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    user: dict = Depends(get_current_user),  # noqa: B008
):
    """Get a single project. Returns 404 if not found or user is not a member."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT p.project_id, p.name, p.description, p.created_at, pm.role
            FROM projects p
            JOIN project_members pm ON pm.project_id = p.project_id
            WHERE p.project_id = $1 AND pm.user_id = $2
        """, project_id, user["user_id"])

    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    return dict(row)


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    user: dict = Depends(get_current_user),  # noqa: B008
):
    """
    Delete a project. Only admins can delete.
    Traces become unowned (project_id → NULL). API keys are cascade-deleted.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Check the user is an admin of this project
        role_row = await conn.fetchrow("""
            SELECT role FROM project_members
            WHERE project_id = $1 AND user_id = $2
        """, project_id, user["user_id"])

        if not role_row or role_row["role"] != "admin":
            raise HTTPException(status_code=403, detail="Only admins can delete a project")

        result = await conn.execute("""
            DELETE FROM projects WHERE project_id = $1
        """, project_id)

    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Project not found")

    return {"status": "deleted", "project_id": project_id}