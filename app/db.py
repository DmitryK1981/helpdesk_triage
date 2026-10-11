import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from app.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    client_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    text TEXT NOT NULL,
    category TEXT,
    confidence TEXT,
    escalate INTEGER,
    draft_reply TEXT,
    error TEXT
);
"""


@contextmanager
def get_connection():
    conn = sqlite3.connect(settings.db_path)
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(SCHEMA)
        conn.commit()


def save_ticket(
    *,
    client_id: str,
    channel: str,
    text: str,
    category: str | None,
    confidence: str | None,
    escalate: bool,
    draft_reply: str | None,
    error: str | None,
) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO tickets
                (created_at, client_id, channel, text, category, confidence, escalate, draft_reply, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                client_id,
                channel,
                text,
                category,
                confidence,
                int(escalate),
                draft_reply,
                error,
            ),
        )
        conn.commit()
        return cursor.lastrowid


def list_tickets(
    *,
    limit: int = 20,
    offset: int = 0,
    category: str | None = None,
    confidence: str | None = None,
    escalate: bool | None = None,
    channel: str | None = None,
    q: str | None = None,
    only_errors: bool = False,
) -> tuple[list[dict], int]:
    where: list[str] = []
    params: list = []

    if category:
        where.append("category = ?")
        params.append(category)
    if confidence:
        where.append("confidence = ?")
        params.append(confidence)
    if escalate is not None:
        where.append("escalate = ?")
        params.append(int(escalate))
    if channel:
        where.append("channel = ?")
        params.append(channel)
    if q:
        where.append("(text LIKE ? OR draft_reply LIKE ? OR client_id LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like, like])
    if only_errors:
        where.append("error IS NOT NULL")

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        total = conn.execute(f"SELECT COUNT(*) FROM tickets {where_sql}", params).fetchone()[0]
        cursor = conn.execute(
            f"""
            SELECT id, created_at, client_id, channel, text, category,
                   confidence, escalate, draft_reply, error
            FROM tickets
            {where_sql}
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            (*params, limit, offset),
        )
        rows = [dict(row) for row in cursor.fetchall()]
        for row in rows:
            row["escalate"] = bool(row["escalate"])
        return rows, total


def get_stats() -> dict:
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
        escalated = conn.execute("SELECT COUNT(*) FROM tickets WHERE escalate = 1").fetchone()[0]
        errors = conn.execute("SELECT COUNT(*) FROM tickets WHERE error IS NOT NULL").fetchone()[0]
        by_category = dict(
            conn.execute(
                "SELECT category, COUNT(*) FROM tickets WHERE category IS NOT NULL GROUP BY category"
            ).fetchall()
        )
        by_confidence = dict(
            conn.execute(
                "SELECT confidence, COUNT(*) FROM tickets WHERE confidence IS NOT NULL GROUP BY confidence"
            ).fetchall()
        )
        return {
            "total": total,
            "escalated": escalated,
            "errors": errors,
            "by_category": by_category,
            "by_confidence": by_confidence,
        }
