"""SQLite helpers for ToneWise's shared team workspace."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from database import get_connection

ROLES = {"owner", "admin", "member"}


def _team(connection, team_id: int):
    return connection.execute("SELECT id, name, description, owner_id, created_at FROM teams WHERE id=?", (team_id,)).fetchone()


def member_role(user_id: int, team_id: int) -> str | None:
    with get_connection() as connection:
        row = connection.execute("SELECT member_role FROM team_members WHERE team_id=? AND user_id=?", (team_id, user_id)).fetchone()
    return row["member_role"] if row else None


def require_team_role(user_id: int, team_id: int, allowed: set[str] | None = None) -> str:
    role = member_role(user_id, team_id)
    if not role:
        raise PermissionError("You are not a member of this team.")
    if allowed and role not in allowed:
        raise PermissionError("You do not have permission to manage this team.")
    return role


def get_user_teams(user_id: int) -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute("""SELECT t.id, t.name, t.description, t.owner_id, t.created_at, tm.member_role
            FROM teams t JOIN team_members tm ON tm.team_id=t.id WHERE tm.user_id=? ORDER BY t.created_at DESC""", (user_id,)).fetchall()
        return [{**dict(row), "members": get_team_members(connection, row["id"])} for row in rows]


def get_team_members(connection, team_id: int) -> list[dict]:
    rows = connection.execute("""SELECT u.id, u.full_name, u.email, tm.member_role, tm.joined_at
        FROM team_members tm JOIN users u ON u.id=tm.user_id WHERE tm.team_id=?
        ORDER BY CASE tm.member_role WHEN 'owner' THEN 0 WHEN 'admin' THEN 1 ELSE 2 END, u.full_name""", (team_id,)).fetchall()
    return [dict(row) for row in rows]


def get_team(user_id: int, team_id: int) -> dict:
    require_team_role(user_id, team_id)
    with get_connection() as connection:
        team = _team(connection, team_id)
        if not team:
            raise ValueError("That team could not be found.")
        result = dict(team)
        result["members"] = get_team_members(connection, team_id)
        result["member_role"] = member_role(user_id, team_id)
        return result


def create_team(user_id: int, name: str, description: str = "") -> dict:
    name, description = name.strip(), description.strip()
    if not name or len(name) > 80 or len(description) > 500:
        raise ValueError("Enter a team name (up to 80 characters) and description (up to 500 characters).")
    with get_connection() as connection:
        cursor = connection.execute("INSERT INTO teams (name, description, owner_id) VALUES (?, ?, ?)", (name, description, user_id))
        connection.execute("INSERT INTO team_members (team_id, user_id, member_role) VALUES (?, ?, 'owner')", (cursor.lastrowid, user_id))
    return get_team(user_id, cursor.lastrowid)


def update_team(user_id: int, team_id: int, name: str, description: str) -> dict:
    require_team_role(user_id, team_id, {"owner", "admin"})
    if not name.strip() or len(name.strip()) > 80 or len(description.strip()) > 500:
        raise ValueError("Enter a team name (up to 80 characters) and description (up to 500 characters).")
    with get_connection() as connection:
        connection.execute("UPDATE teams SET name=?, description=? WHERE id=?", (name.strip(), description.strip(), team_id))
    return get_team(user_id, team_id)


def delete_team(user_id: int, team_id: int) -> None:
    require_team_role(user_id, team_id, {"owner"})
    with get_connection() as connection:
        connection.execute("DELETE FROM teams WHERE id=? AND owner_id=?", (team_id, user_id))


def set_member_role(actor_id: int, team_id: int, target_id: int, role: str) -> None:
    if role not in ROLES - {"owner"}:
        raise ValueError("Choose Admin or Member.")
    require_team_role(actor_id, team_id, {"owner", "admin"})
    with get_connection() as connection:
        target = connection.execute("SELECT member_role FROM team_members WHERE team_id=? AND user_id=?", (team_id, target_id)).fetchone()
        if not target:
            raise ValueError("That person is not a team member.")
        if target["member_role"] == "owner":
            raise PermissionError("The team owner role cannot be changed.")
        if member_role(actor_id, team_id) == "admin" and target["member_role"] == "admin":
            raise PermissionError("Admins cannot change another admin's role.")
        connection.execute("UPDATE team_members SET member_role=? WHERE team_id=? AND user_id=?", (role, team_id, target_id))


def remove_member(actor_id: int, team_id: int, target_id: int) -> None:
    actor_role = require_team_role(actor_id, team_id, {"owner", "admin"})
    with get_connection() as connection:
        target = connection.execute("SELECT member_role FROM team_members WHERE team_id=? AND user_id=?", (team_id, target_id)).fetchone()
        if not target:
            raise ValueError("That person is not a team member.")
        if target["member_role"] == "owner" or (actor_role == "admin" and target["member_role"] == "admin"):
            raise PermissionError("You cannot remove this member.")
        connection.execute("DELETE FROM team_members WHERE team_id=? AND user_id=?", (team_id, target_id))


def create_invitation(owner_id: int, team_id: int, email: str) -> dict:
    require_team_role(owner_id, team_id, {"owner", "admin"})
    email = email.strip().lower()
    with get_connection() as connection:
        team = _team(connection, team_id)
        token = str(uuid4())
        connection.execute("UPDATE team_invitations SET status='cancelled' WHERE team_id=? AND invited_email=? AND status='pending'", (team_id, email))
        connection.execute("INSERT INTO team_invitations (team_id, invited_email, token, invited_by) VALUES (?, ?, ?, ?)", (team_id, email, token, owner_id))
        return {"token": token, "team_name": team["name"]}


def cancel_invitation(token: str) -> None:
    with get_connection() as connection:
        connection.execute("UPDATE team_invitations SET status='cancelled' WHERE token=? AND status='pending'", (token,))


def create_invite_link(actor_id: int, team_id: int, expiry_days: int) -> dict:
    require_team_role(actor_id, team_id, {"owner", "admin"})
    if expiry_days not in {1, 7, 30}:
        raise ValueError("Choose a 1, 7, or 30 day expiry.")
    token = str(uuid4())
    expires = datetime.now(timezone.utc) + timedelta(days=expiry_days)
    with get_connection() as connection:
        connection.execute("INSERT INTO team_invite_links (team_id, token, created_by, expires_at) VALUES (?, ?, ?, ?)", (team_id, token, actor_id, expires.strftime("%Y-%m-%d %H:%M:%S")))
    return {"token": token, "expires_at": expires.isoformat()}


def accept_invitation(user_id: int, email: str, token: str) -> str:
    with get_connection() as connection:
        invitation = connection.execute("SELECT team_id, invited_email, status FROM team_invitations WHERE token=?", (token,)).fetchone()
        if not invitation or invitation["status"] != "pending":
            raise ValueError("This invitation is no longer available.")
        if invitation["invited_email"].lower() != email.strip().lower():
            raise PermissionError("Sign in with the email address that received this invitation.")
        _join_team(connection, invitation["team_id"], user_id)
        connection.execute("UPDATE team_invitations SET status='accepted', accepted_at=CURRENT_TIMESTAMP WHERE token=?", (token,))
        return _team(connection, invitation["team_id"])["name"]


def accept_invite_link(user_id: int, token: str) -> str:
    with get_connection() as connection:
        link = connection.execute("SELECT team_id, expires_at, active FROM team_invite_links WHERE token=?", (token,)).fetchone()
        if not link or not link["active"] or link["expires_at"] <= datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"):
            raise ValueError("This shareable invite link has expired or is unavailable.")
        _join_team(connection, link["team_id"], user_id)
        return _team(connection, link["team_id"])["name"]


def _join_team(connection, team_id: int, user_id: int) -> None:
    connection.execute("INSERT OR IGNORE INTO team_members (team_id, user_id, member_role) VALUES (?, ?, 'member')", (team_id, user_id))
    notify(connection, user_id, "team", "You were added to a team.", f"/team-feed?team={team_id}")


def team_feed(user_id: int, team_id: int) -> list[dict]:
    require_team_role(user_id, team_id)
    with get_connection() as connection:
        rows = connection.execute("""SELECT c.session_id, c.original_text, c.simplified_explanation, c.tone, c.user_role, c.language, c.created_at,
            u.full_name AS author_name, u.id AS author_id,
            (SELECT COUNT(*) FROM shared_comments sc WHERE sc.session_id=c.session_id) AS comment_count,
            (SELECT COUNT(*) FROM messages m WHERE m.session_id=c.session_id) AS message_count
            FROM conversations c JOIN users u ON u.id=c.user_id
            WHERE c.team_id=? AND c.shared_with_team=1 ORDER BY c.created_at DESC""", (team_id,)).fetchall()
    return [dict(row) for row in rows]


def share_conversation(user_id: int, team_id: int, session_id: str) -> None:
    require_team_role(user_id, team_id, {"owner", "admin", "member"})
    with get_connection() as connection:
        conversation = connection.execute("SELECT user_id FROM conversations WHERE session_id=?", (session_id,)).fetchone()
        if not conversation or conversation["user_id"] != user_id:
            raise ValueError("Only the item creator can share this simplification.")
        connection.execute("UPDATE conversations SET shared_with_team=1, team_id=? WHERE session_id=?", (team_id, session_id))
        members = connection.execute("SELECT user_id FROM team_members WHERE team_id=? AND user_id<>?", (team_id, user_id)).fetchall()
        for row in members:
            notify(connection, row["user_id"], "shared", "A teammate shared a new simplification.", f"/team-feed?team={team_id}&item={session_id}")


def get_shared_item(user_id: int, team_id: int, session_id: str) -> dict:
    require_team_role(user_id, team_id)
    with get_connection() as connection:
        item = connection.execute("""SELECT c.*, u.full_name AS author_name FROM conversations c JOIN users u ON u.id=c.user_id
            WHERE c.session_id=? AND c.team_id=? AND c.shared_with_team=1""", (session_id, team_id)).fetchone()
        if not item:
            raise ValueError("This shared item could not be found.")
        comments = connection.execute("""SELECT sc.id, sc.parent_id, sc.content, sc.created_at, u.full_name AS author_name
            FROM shared_comments sc JOIN users u ON u.id=sc.author_user_id WHERE sc.session_id=? ORDER BY sc.created_at""", (session_id,)).fetchall()
        messages = connection.execute("SELECT sender_role, content, created_at FROM messages WHERE session_id=? ORDER BY id", (session_id,)).fetchall()
    return {**dict(item), "comments": [dict(row) for row in comments], "messages": [dict(row) for row in messages]}


def add_comment(user_id: int, team_id: int, session_id: str, content: str, parent_id: int | None = None) -> dict:
    require_team_role(user_id, team_id)
    if not content.strip() or len(content.strip()) > 2000:
        raise ValueError("Enter a comment of up to 2,000 characters.")
    with get_connection() as connection:
        item = connection.execute("SELECT user_id FROM conversations WHERE session_id=? AND team_id=? AND shared_with_team=1", (session_id, team_id)).fetchone()
        if not item:
            raise ValueError("This shared item could not be found.")
        cursor = connection.execute("INSERT INTO shared_comments (session_id, author_user_id, parent_id, content) VALUES (?, ?, ?, ?)", (session_id, user_id, parent_id, content.strip()))
        recipients = {item["user_id"]}
        recipients.update(row["author_user_id"] for row in connection.execute("SELECT DISTINCT author_user_id FROM shared_comments WHERE session_id=?", (session_id,)))
        for recipient in recipients - {user_id}:
            notify(connection, recipient, "comment", "A teammate commented on a shared item.", f"/team-feed?team={team_id}&item={session_id}")
        row = connection.execute("""SELECT sc.id, sc.parent_id, sc.content, sc.created_at, u.full_name AS author_name
            FROM shared_comments sc JOIN users u ON u.id=sc.author_user_id WHERE sc.id=?""", (cursor.lastrowid,)).fetchone()
    return dict(row)


def notify(connection, user_id: int, kind: str, message: str, link: str | None) -> None:
    connection.execute("INSERT INTO notifications (user_id, kind, message, link) VALUES (?, ?, ?, ?)", (user_id, kind, message, link))


def notifications(user_id: int) -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute("SELECT id, kind, message, link, is_read, created_at FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 30", (user_id,)).fetchall()
    return [dict(row) for row in rows]


def mark_notifications_read(user_id: int) -> None:
    with get_connection() as connection:
        connection.execute("UPDATE notifications SET is_read=1 WHERE user_id=?", (user_id,))
