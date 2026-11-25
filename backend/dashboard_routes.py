"""Authenticated APIs for the dashboard and collaborative team workspace."""
from collections import Counter

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, EmailStr, Field

from auth import app_url, current_user, public_user
from chat_manager import ask_followup, get_conversation_history, restore_conversation
from database import get_connection, save_message
from mailer import send_team_invitation
from teams import (accept_invitation, accept_invite_link, add_comment, cancel_invitation,
                   create_invitation, create_invite_link, create_team, delete_team,
                   get_shared_item, get_team, get_user_teams, mark_notifications_read,
                   member_role, notifications, remove_member, set_member_role,
                   share_conversation, team_feed, update_team)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def require_user(request: Request):
    user = current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Please sign in to continue.")
    return user


def team_error(error: Exception):
    if isinstance(error, PermissionError):
        raise HTTPException(status_code=403, detail=str(error)) from error
    raise HTTPException(status_code=400, detail=str(error)) from error


class TeamRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)


class InviteRequest(BaseModel):
    email: EmailStr


class InviteLinkRequest(BaseModel):
    expiry_days: int = 7


class RoleRequest(BaseModel):
    role: str


class CommentRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    parent_id: int | None = None


class ShareRequest(BaseModel):
    team_id: int


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


@router.get("/summary")
def summary(request: Request) -> dict:
    user = require_user(request)
    with get_connection() as connection:
        rows = connection.execute("SELECT session_id, original_text, tone, user_role, provider_used, created_at FROM conversations WHERE user_id=? ORDER BY created_at DESC", (user["id"],)).fetchall()
        onboarding = connection.execute(
            "SELECT user_type FROM user_onboarding WHERE user_id = ?", (user["id"],)
        ).fetchone()
    conversations = [dict(row) for row in rows]
    top = lambda key, fallback: (Counter(row[key] for row in conversations if row[key]).most_common(1) or [(fallback, 0)])[0][0]
    return {"user": {**public_user(user), "user_type": onboarding["user_type"] if onboarding else None}, "stats": {"total": len(conversations), "tone": top("tone", "—"), "role": top("user_role", "—"), "provider": top("provider_used", "Not used yet")}, "conversations": conversations, "teams": get_user_teams(user["id"])}


@router.get("/teams")
def teams(request: Request) -> dict:
    user = require_user(request)
    return {"teams": get_user_teams(user["id"])}


@router.post("/teams")
def new_team(payload: TeamRequest, request: Request) -> dict:
    user = require_user(request)
    try:
        return {"success": True, "team": create_team(user["id"], payload.name, payload.description)}
    except ValueError as error:
        team_error(error)


@router.get("/teams/{team_id}")
def team_details(team_id: int, request: Request) -> dict:
    user = require_user(request)
    try:
        return {"team": get_team(user["id"], team_id)}
    except (PermissionError, ValueError) as error:
        team_error(error)


@router.put("/teams/{team_id}")
def edit_team(team_id: int, payload: TeamRequest, request: Request) -> dict:
    user = require_user(request)
    try:
        return {"success": True, "team": update_team(user["id"], team_id, payload.name, payload.description)}
    except (PermissionError, ValueError) as error:
        team_error(error)


@router.delete("/teams/{team_id}")
def remove_team(team_id: int, request: Request) -> dict:
    user = require_user(request)
    try:
        delete_team(user["id"], team_id)
        return {"success": True}
    except (PermissionError, ValueError) as error:
        team_error(error)


@router.post("/teams/{team_id}/invite")
def invite(team_id: int, payload: InviteRequest, request: Request) -> dict:
    user = require_user(request)
    try:
        invitation = create_invitation(user["id"], team_id, str(payload.email))
        try:
            send_team_invitation(recipient=str(payload.email), team_name=invitation["team_name"], inviter_name=user["full_name"], invitation_url=app_url(request, f"/api/dashboard/team-invitations/{invitation['token']}"))
        except RuntimeError:
            cancel_invitation(invitation["token"])
            raise
        return {"success": True}
    except (PermissionError, ValueError) as error:
        team_error(error)
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.post("/teams/{team_id}/invite-links")
def invite_link(team_id: int, payload: InviteLinkRequest, request: Request) -> dict:
    user = require_user(request)
    try:
        link = create_invite_link(user["id"], team_id, payload.expiry_days)
        return {"success": True, "url": app_url(request, f"/api/dashboard/team-invite-links/{link['token']}"), "expires_at": link["expires_at"]}
    except (PermissionError, ValueError) as error:
        team_error(error)


@router.put("/teams/{team_id}/members/{member_id}")
def change_role(team_id: int, member_id: int, payload: RoleRequest, request: Request) -> dict:
    user = require_user(request)
    try:
        set_member_role(user["id"], team_id, member_id, payload.role.lower())
        return {"success": True}
    except (PermissionError, ValueError) as error:
        team_error(error)


@router.delete("/teams/{team_id}/members/{member_id}")
def delete_member(team_id: int, member_id: int, request: Request) -> dict:
    user = require_user(request)
    try:
        remove_member(user["id"], team_id, member_id)
        return {"success": True}
    except (PermissionError, ValueError) as error:
        team_error(error)


@router.get("/teams/{team_id}/feed")
def feed(team_id: int, request: Request) -> dict:
    user = require_user(request)
    try:
        return {"items": team_feed(user["id"], team_id), "role": member_role(user["id"], team_id)}
    except PermissionError as error:
        team_error(error)


@router.post("/teams/{team_id}/items/{session_id}/share")
def share_item(team_id: int, session_id: str, request: Request) -> dict:
    user = require_user(request)
    try:
        share_conversation(user["id"], team_id, session_id)
        return {"success": True}
    except (PermissionError, ValueError) as error:
        team_error(error)


@router.get("/teams/{team_id}/items/{session_id}")
def shared_item(team_id: int, session_id: str, request: Request) -> dict:
    user = require_user(request)
    try:
        return {"item": get_shared_item(user["id"], team_id, session_id)}
    except (PermissionError, ValueError) as error:
        team_error(error)


@router.post("/teams/{team_id}/items/{session_id}/comments")
def comment(team_id: int, session_id: str, payload: CommentRequest, request: Request) -> dict:
    user = require_user(request)
    try:
        return {"success": True, "comment": add_comment(user["id"], team_id, session_id, payload.content, payload.parent_id)}
    except (PermissionError, ValueError) as error:
        team_error(error)


@router.post("/teams/{team_id}/items/{session_id}/chat")
def collaborative_chat(team_id: int, session_id: str, payload: ChatRequest, request: Request) -> dict:
    user = require_user(request)
    try:
        item = get_shared_item(user["id"], team_id, session_id)
    except (PermissionError, ValueError) as error:
        team_error(error)
    if not get_conversation_history(session_id):
        restore_conversation(session_id, item["original_text"], item["simplified_explanation"], item["messages"], item["language"])
    result = ask_followup(session_id, payload.question.strip())
    save_message(session_id, "user", payload.question.strip())
    if result["success"]:
        save_message(session_id, "assistant", result["response"])
        return result
    raise HTTPException(status_code=502, detail=result.get("detail", "The AI could not answer right now."))


@router.get("/notifications")
def notification_list(request: Request) -> dict:
    user = require_user(request)
    items = notifications(user["id"])
    return {"notifications": items, "unread": sum(not item["is_read"] for item in items)}


@router.post("/notifications/read")
def read_notifications(request: Request) -> dict:
    user = require_user(request)
    mark_notifications_read(user["id"])
    return {"success": True}


@router.get("/team-invitations/{token}", response_class=HTMLResponse)
def invitation_page(token: str, request: Request):
    user = current_user(request)
    if user is None:
        return RedirectResponse(f"/signin?invite={token}", status_code=303)
    try:
        return RedirectResponse(f"/team-feed?joined={accept_invitation(user['id'], user['email'], token)}", status_code=303)
    except (PermissionError, ValueError) as error:
        return HTMLResponse(f"<h1>Invitation unavailable</h1><p>{str(error)}</p>", status_code=400)


@router.get("/team-invite-links/{token}", response_class=HTMLResponse)
def invite_link_page(token: str, request: Request):
    user = current_user(request)
    if user is None:
        return RedirectResponse(f"/signin?teamInvite={token}", status_code=303)
    try:
        return RedirectResponse(f"/team-feed?joined={accept_invite_link(user['id'], token)}", status_code=303)
    except ValueError as error:
        return HTMLResponse(f"<h1>Invite link unavailable</h1><p>{str(error)}</p>", status_code=400)
