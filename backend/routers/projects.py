"""
routers/projects.py — Project (workspace) management.

POST   /projects              — create a new project
GET    /projects              — list all projects for current user
GET    /projects/{id}         — get one project
DELETE /projects/{id}         — delete a project

A project is a named workspace that groups traces and API keys together.
Every trace belongs to a project. Every API key is scoped to a project.
Multi-tenancy is enforced by filtering all queries by user_id from the JWT.
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
    """Create a new project for the current user."""
    project_id = str(uuid.uuid4())

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO projects (project_id, user_id, name, description)
            VALUES ($1, $2, $3, $4)
        """, project_id, user["user_id"], body.name, body.description)

    return {
        "project_id": project_id,
        "name": body.name,
        "description": body.description,
    }


@router.get("")
async def list_projects(
    user: dict = Depends(get_current_user),  # noqa: B008
):
    """List all projects owned by the current user."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT project_id, name, description, created_at,
                   (SELECT COUNT(*) FROM traces WHERE traces.project_id = projects.project_id) AS trace_count
            FROM projects
            WHERE user_id = $1
            ORDER BY created_at DESC
        """, user["user_id"])
    return [dict(row) for row in rows]


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    user: dict = Depends(get_current_user),  # noqa: B008
):
    """Get a single project. Returns 404 if not found or not owned by user."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT project_id, name, description, created_at
            FROM projects
            WHERE project_id = $1 AND user_id = $2
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
    Delete a project. Only the owner can delete it.
    Traces become unowned (project_id → NULL). API keys are cascade-deleted.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("""
            DELETE FROM projects
            WHERE project_id = $1 AND user_id = $2
        """, project_id, user["user_id"])

    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Project not found")

    return {"status": "deleted", "project_id": project_id}