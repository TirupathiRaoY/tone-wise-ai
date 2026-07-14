"""
database.py
-----------
Module 7: SQLite storage for ToneWise AI.

This module saves conversations and feedback to a small local database file.
SQLite is built into Python, so it is free and needs no account or server.

The database file (tonewise.db) is created automatically beside this file
the first time initialize_database() runs.
"""

from collections import Counter
from pathlib import Path
import re
import sqlite3


DATABASE_PATH = Path(__file__).with_name("tonewise.db")


def get_connection() -> sqlite3.Connection:
    """Open a connection to the local SQLite database."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database() -> None:
    """Create the database tables if they do not already exist.

    Safe to run every time the server starts. Existing saved data is kept.
    """
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                session_id TEXT PRIMARY KEY,
                original_text TEXT NOT NULL,
                simplified_explanation TEXT NOT NULL,
                tone TEXT NOT NULL,
                user_role TEXT NOT NULL,
                language TEXT NOT NULL DEFAULT 'English',
                provider_used TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                sender_role TEXT NOT NULL CHECK (sender_role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES conversations(session_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                was_clear INTEGER NOT NULL CHECK (was_clear IN (0, 1)),
                comment TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES conversations(session_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS team_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                author_name TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES conversations(session_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT,
                oauth_provider TEXT,
                oauth_subject TEXT,
                onboarding_complete INTEGER NOT NULL DEFAULT 0 CHECK (onboarding_complete IN (0, 1)),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(oauth_provider, oauth_subject)
            );

            CREATE TABLE IF NOT EXISTS user_oauth_identities (
                provider TEXT NOT NULL CHECK (provider IN ('google', 'github')),
                subject TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (provider, subject),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                expires_at TEXT NOT NULL,
                used_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS user_onboarding (
                user_id INTEGER PRIMARY KEY,
                user_type TEXT NOT NULL,
                user_type_other TEXT,
                field TEXT NOT NULL,
                field_other TEXT,
                goals_json TEXT NOT NULL,
                technical_background TEXT NOT NULL,
                default_tone TEXT NOT NULL DEFAULT 'Casual',
                default_role TEXT NOT NULL DEFAULT 'General Non-Technical Staff',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                owner_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS team_members (
                team_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                member_role TEXT NOT NULL CHECK (member_role IN ('owner', 'member')),
                joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (team_id, user_id),
                FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS team_invite_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                token TEXT NOT NULL UNIQUE,
                created_by INTEGER NOT NULL,
                expires_at TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
                FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS shared_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                author_user_id INTEGER NOT NULL,
                parent_id INTEGER,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES conversations(session_id) ON DELETE CASCADE,
                FOREIGN KEY (author_user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (parent_id) REFERENCES shared_comments(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                kind TEXT NOT NULL,
                message TEXT NOT NULL,
                link TEXT,
                is_read INTEGER NOT NULL DEFAULT 0 CHECK (is_read IN (0, 1)),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS team_invitations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                invited_email TEXT NOT NULL COLLATE NOCASE,
                token TEXT NOT NULL UNIQUE,
                invited_by INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'cancelled')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                accepted_at TEXT,
                FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
                FOREIGN KEY (invited_by) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_messages_session_id
            ON messages(session_id);

            CREATE INDEX IF NOT EXISTS idx_feedback_session_id
            ON feedback(session_id);

            CREATE INDEX IF NOT EXISTS idx_team_comments_session_id
            ON team_comments(session_id);

            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
            """
        )

        # This keeps databases created before the language feature working.
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(conversations)")}
        if "language" not in columns:
            connection.execute(
                "ALTER TABLE conversations ADD COLUMN language TEXT NOT NULL DEFAULT 'English'"
            )
        # These additions make old conversation records remain usable while
        # enabling private per-user history and optional team sharing.
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(conversations)")}
        if "user_id" not in columns:
            connection.execute("ALTER TABLE conversations ADD COLUMN user_id INTEGER")
        if "shared_with_team" not in columns:
            connection.execute("ALTER TABLE conversations ADD COLUMN shared_with_team INTEGER NOT NULL DEFAULT 0")
        if "team_id" not in columns:
            connection.execute("ALTER TABLE conversations ADD COLUMN team_id INTEGER")
        team_columns = {row["name"] for row in connection.execute("PRAGMA table_info(teams)")}
        if "description" not in team_columns:
            connection.execute("ALTER TABLE teams ADD COLUMN description TEXT NOT NULL DEFAULT ''")
        member_schema = connection.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='team_members'").fetchone()["sql"]
        if "'admin'" not in member_schema.lower():
            connection.execute("ALTER TABLE team_members RENAME TO team_members_legacy")
            connection.execute("""CREATE TABLE team_members (
                team_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
                member_role TEXT NOT NULL CHECK (member_role IN ('owner', 'admin', 'member')),
                joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (team_id, user_id),
                FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )""")
            connection.execute("INSERT INTO team_members (team_id, user_id, member_role, joined_at) SELECT team_id, user_id, member_role, joined_at FROM team_members_legacy")
            connection.execute("DROP TABLE team_members_legacy")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_team_members_user_id ON team_members(user_id)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_team_invitations_token ON team_invitations(token)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_team_invitations_email ON team_invitations(invited_email)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_invite_links_token ON team_invite_links(token)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_shared_comments_session ON shared_comments(session_id)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read, created_at)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_user_oauth_identities_user ON user_oauth_identities(user_id)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_lookup ON password_reset_tokens(token_hash, expires_at)")
        # Preserve OAuth accounts created before multiple providers could be
        # linked to one ToneWise account.
        connection.execute(
            """INSERT OR IGNORE INTO user_oauth_identities (provider, subject, user_id)
               SELECT oauth_provider, oauth_subject, id FROM users
               WHERE oauth_provider IS NOT NULL AND oauth_subject IS NOT NULL"""
        )


def save_conversation(
    session_id: str,
    original_text: str,
    simplified_explanation: str,
    tone: str,
    role: str,
    language: str = "English",
    provider_used: str | None = None,
    user_id: int | None = None,
) -> None:
    """Save the first explanation of one conversation.

    If the same session is saved again, its first explanation is updated
    rather than creating a duplicate conversation.
    """
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO conversations
                (session_id, original_text, simplified_explanation, tone, user_role, language, provider_used, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                original_text = excluded.original_text,
                simplified_explanation = excluded.simplified_explanation,
                tone = excluded.tone,
                user_role = excluded.user_role,
                language = excluded.language,
                provider_used = excluded.provider_used,
                user_id = excluded.user_id
            """,
            (session_id, original_text, simplified_explanation, tone, role, language, provider_used, user_id),
        )


def save_message(session_id: str, sender_role: str, content: str) -> None:
    """Save one user question or AI answer in an existing conversation."""
    if sender_role not in ("user", "assistant"):
        raise ValueError("sender_role must be 'user' or 'assistant'.")

    with get_connection() as connection:
        connection.execute(
            "INSERT INTO messages (session_id, sender_role, content) VALUES (?, ?, ?)",
            (session_id, sender_role, content),
        )


def get_conversation(session_id: str) -> dict | None:
    """Return one saved conversation and all of its follow-up messages."""
    with get_connection() as connection:
        conversation = connection.execute(
            "SELECT * FROM conversations WHERE session_id = ?", (session_id,)
        ).fetchone()

        if conversation is None:
            return None

        messages = connection.execute(
            """
            SELECT sender_role, content, created_at
            FROM messages
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (session_id,),
        ).fetchall()

    return {
        "session_id": conversation["session_id"],
        "original_text": conversation["original_text"],
        "simplified_explanation": conversation["simplified_explanation"],
        "tone": conversation["tone"],
        "role": conversation["user_role"],
        "language": conversation["language"],
        "provider_used": conversation["provider_used"],
        "created_at": conversation["created_at"],
        "messages": [dict(message) for message in messages],
    }


def save_feedback(session_id: str, was_clear: bool, comment: str | None = None) -> None:
    """Save a user's Yes/No answer to 'Was this clear?' and optional note."""
    cleaned_comment = comment.strip() if comment else None
    with get_connection() as connection:
        # One current response per conversation. A later click changes the
        # answer instead of making the dashboard count the same user twice.
        updated = connection.execute(
            "UPDATE feedback SET was_clear = ?, comment = ? WHERE session_id = ?",
            (int(was_clear), cleaned_comment, session_id),
        )
        if updated.rowcount == 0:
            connection.execute(
                "INSERT INTO feedback (session_id, was_clear, comment) VALUES (?, ?, ?)",
                (session_id, int(was_clear), cleaned_comment),
            )


def save_team_comment(session_id: str, author_name: str, content: str) -> dict:
    """Save one short note from a teammate on a shared explanation."""
    clean_name = author_name.strip()
    clean_content = content.strip()
    if not clean_name or not clean_content:
        raise ValueError("A name and note are both required.")

    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO team_comments (session_id, author_name, content) VALUES (?, ?, ?)",
            (session_id, clean_name, clean_content),
        )
        comment = connection.execute(
            "SELECT id, author_name, content, created_at FROM team_comments WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
    return dict(comment)


def get_team_comments(session_id: str) -> list[dict]:
    """Return the saved team notes for one shared explanation."""
    with get_connection() as connection:
        comments = connection.execute(
            """
            SELECT id, author_name, content, created_at
            FROM team_comments
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (session_id,),
        ).fetchall()
    return [dict(comment) for comment in comments]


def get_feedback_stats() -> dict:
    """Return simple feedback totals for the future admin dashboard."""
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                COUNT(*) AS total_feedback,
                COALESCE(SUM(CASE WHEN was_clear = 1 THEN 1 ELSE 0 END), 0) AS clear_yes,
                COALESCE(SUM(CASE WHEN was_clear = 0 THEN 1 ELSE 0 END), 0) AS clear_no
            FROM feedback
            """
        ).fetchone()

    total = row["total_feedback"]
    clear_yes = row["clear_yes"]
    return {
        "total_feedback": total,
        "clear_yes": clear_yes,
        "clear_no": row["clear_no"],
        "clarity_percentage": round((clear_yes / total) * 100, 1) if total else 0.0,
    }


COMMON_WORDS = {
    "about", "after", "again", "also", "been", "before", "could", "does", "explain",
    "from", "have", "into", "mean", "more", "most", "please", "that", "their", "them",
    "this", "what", "when", "which", "will", "with", "would", "your",
}


def get_most_asked_topics(limit: int = 10) -> list[dict]:
    """Return common meaningful words from user follow-up questions.

    This is a lightweight, free way for the admin dashboard to spot topics
    people ask about often. It does not send any saved conversation to an AI.
    """
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT content FROM messages WHERE sender_role = 'user'"
        ).fetchall()

    words = []
    for row in rows:
        found_words = re.findall(r"[a-zA-Z]{4,}", row["content"].lower())
        words.extend(word for word in found_words if word not in COMMON_WORDS)

    return [
        {"topic": word, "count": count}
        for word, count in Counter(words).most_common(limit)
    ]


def get_admin_summary() -> dict:
    """Return all database numbers needed by the future admin dashboard."""
    with get_connection() as connection:
        conversation_count = connection.execute(
            "SELECT COUNT(*) FROM conversations"
        ).fetchone()[0]

    return {
        "total_conversations": conversation_count,
        "feedback": get_feedback_stats(),
        "most_asked_topics": get_most_asked_topics(),
    }


if __name__ == "__main__":
    # A safe local test. Run: python database.py
    initialize_database()
    print(f"Database is ready: {DATABASE_PATH}")
    print("Current dashboard summary:")
    print(get_admin_summary())
