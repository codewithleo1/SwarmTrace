"""
routers/members.py — Project member management (RBAC).
C2: audit log calls added on invite, role change, and remove.
"""

import uuid

from auth.dependencies import require_role
from database import get_pool
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from routers.audit import log_action

router = APIRouter()

VALID_ROLES = {"admin", "developer", "viewer"}


class InviteMemberRequest(BaseModel):
    email: str
    role: str = "developer"


class UpdateRoleRequest(BaseModel):
    role: str


@router.get("/projects/{project_id}/members")
async def list_members(
    project_id: str,
    user: dict = Depends(require_role("project_id", "viewer")),  # noqa: B008
):
    """List all members of a project. Requires any membership."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT pm.member_id, pm.role, pm.created_at,
                   u.user_id, u.email, u.name,
                   inv.name AS invited_by_name
            FROM project_members pm
            JOIN users u ON u.user_id = pm.user_id
            LEFT JOIN users inv ON inv.user_id = pm.invited_by
            WHERE pm.project_id = $1
            ORDER BY
                CASE pm.role
                    WHEN 'admin'     THEN 0
                    WHEN 'developer' THEN 1
                    WHEN 'viewer'    THEN 2
                END,
                pm.created_at ASC
        """, project_id)

    return [
        {
            "member_id":       str(row["member_id"]),
            "user_id":         str(row["user_id"]),
            "email":           row["email"],
            "name":            row["name"],
            "role":            row["role"],
            "invited_by_name": row["invited_by_name"],
            "created_at":      row["created_at"],
        }
        for row in rows
    ]


@router.post("/projects/{project_id}/members", status_code=201)
async def invite_member(
    project_id: str,
    body: InviteMemberRequest,
    user: dict = Depends(require_role("project_id", "admin")),  # noqa: B008
):
    """Invite a user by email. Requires admin role."""
    if body.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid role '{body.role}'. Must be one of: {', '.join(sorted(VALID_ROLES))}",
        )

    pool = await get_pool()
    async with pool.acquire() as conn:
        invitee = await conn.fetchrow(
            "SELECT user_id, name FROM users WHERE email = $1", body.email
        )
        if not invitee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No account found for {body.email}. They must register first.",
            )

        invitee_id = str(invitee["user_id"])

        existing = await conn.fetchrow("""
            SELECT member_id FROM project_members
            WHERE project_id = $1 AND user_id = $2
        """, project_id, invitee_id)

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"{body.email} is already a member of this project",
            )

        member_id = str(uuid.uuid4())
        await conn.execute("""
            INSERT INTO project_members (member_id, project_id, user_id, role, invited_by)
            VALUES ($1, $2, $3, $4, $5)
        """, member_id, project_id, invitee_id, body.role, user["user_id"])

    # C2: audit
    await log_action(
        project_id=project_id,
        user_id=user["user_id"],
        user_email=user["email"],
        action="MEMBER_INVITED",
        resource_type="member",
        resource_id=member_id,
        metadata={"invitee_email": body.email, "role": body.role},
    )

    return {
        "member_id": member_id,
        "email":     body.email,
        "name":      invitee["name"],
        "role":      body.role,
        "message":   f"{body.email} added as {body.role}",
    }


@router.patch("/projects/{project_id}/members/{member_id}")
async def update_member_role(
    project_id: str,
    member_id: str,
    body: UpdateRoleRequest,
    user: dict = Depends(require_role("project_id", "admin")),  # noqa: B008
):
    """Change a member's role. Requires admin. Cannot change your own role."""
    if body.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid role '{body.role}'. Must be one of: {', '.join(sorted(VALID_ROLES))}",
        )

    pool = await get_pool()
    async with pool.acquire() as conn:
        target = await conn.fetchrow("""
            SELECT user_id, role FROM project_members
            WHERE member_id = $1 AND project_id = $2
        """, member_id, project_id)

        if not target:
            raise HTTPException(status_code=404, detail="Member not found")

        if str(target["user_id"]) == user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change your own role — ask another admin",
            )

        old_role = target["role"]
        await conn.execute("""
            UPDATE project_members SET role = $1
            WHERE member_id = $2 AND project_id = $3
        """, body.role, member_id, project_id)

    # C2: audit
    await log_action(
        project_id=project_id,
        user_id=user["user_id"],
        user_email=user["email"],
        action="MEMBER_ROLE_CHANGED",
        resource_type="member",
        resource_id=member_id,
        metadata={"old_role": old_role, "new_role": body.role},
    )

    return {"status": "updated", "member_id": member_id, "new_role": body.role}


@router.delete("/projects/{project_id}/members/{member_id}")
async def remove_member(
    project_id: str,
    member_id: str,
    user: dict = Depends(require_role("project_id", "admin")),  # noqa: B008
):
    """Remove a member from the project. Requires admin. Cannot remove yourself."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        target = await conn.fetchrow("""
            SELECT user_id FROM project_members
            WHERE member_id = $1 AND project_id = $2
        """, member_id, project_id)

        if not target:
            raise HTTPException(status_code=404, detail="Member not found")

        if str(target["user_id"]) == user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove yourself — transfer admin first",
            )

        await conn.execute("""
            DELETE FROM project_members
            WHERE member_id = $1 AND project_id = $2
        """, member_id, project_id)

    # C2: audit
    await log_action(
        project_id=project_id,
        user_id=user["user_id"],
        user_email=user["email"],
        action="MEMBER_REMOVED",
        resource_type="member",
        resource_id=member_id,
        metadata={"removed_user_id": str(target["user_id"])},
    )

    return {"status": "removed", "member_id": member_id}