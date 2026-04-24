"""
SQLite credential store with encrypted hash storage.

Passwords are hashed with pbkdf2:sha256:600000, then the hash is
Fernet-encrypted with a dedicated key stored in config/db_key before
being written to disk. The SQLite file is useless without that key file.
"""
import os
import sqlite3
import time

from cryptography.fernet import Fernet
from werkzeug.security import check_password_hash, generate_password_hash

_CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "config")
DB_PATH     = os.path.join(_CONFIG_DIR, "credentials.db")
DB_KEY_FILE = os.path.join(_CONFIG_DIR, "db_key")

# ── Fernet key ────────────────────────────────────────────────────────────────

def _load_or_create_db_key() -> Fernet:
    """Load the DB encryption key, generating it on first run."""
    os.makedirs(_CONFIG_DIR, exist_ok=True)
    if os.path.exists(DB_KEY_FILE):
        with open(DB_KEY_FILE, "rb") as f:
            return Fernet(f.read().strip())
    key = Fernet.generate_key()
    with open(DB_KEY_FILE, "wb") as f:
        f.write(key)
    os.chmod(DB_KEY_FILE, 0o600)
    print(f"[+] Generated DB encryption key at {DB_KEY_FILE}  (mode 600) — back this up.")
    return Fernet(key)

_fernet = _load_or_create_db_key()


# ── DB setup ──────────────────────────────────────────────────────────────────

def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username     TEXT PRIMARY KEY,
                password_enc TEXT NOT NULL,
                created_at   REAL NOT NULL,
                last_login   REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id      TEXT PRIMARY KEY,
                agent_id     TEXT NOT NULL,
                task_type    TEXT NOT NULL,
                task_json    TEXT NOT NULL,
                status       TEXT NOT NULL DEFAULT 'queued',
                result_json  TEXT,
                created_at   REAL NOT NULL,
                delivered_at REAL,
                completed_at REAL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_agent_status
            ON tasks (agent_id, status)
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                agent_id  TEXT PRIMARY KEY,
                hostname  TEXT,
                os        TEXT,
                user      TEXT,
                last_seen REAL NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS login_attempts (
                ip           TEXT NOT NULL,
                attempted_at REAL NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_login_attempts_ip_time
            ON login_attempts (ip, attempted_at)
        """)


# ── Public API ────────────────────────────────────────────────────────────────

def create_user(username: str, password: str):
    """Hash and encrypt the password, then store the user."""
    pw_hash = generate_password_hash(password, method="pbkdf2:sha256:600000")
    pw_enc  = _fernet.encrypt(pw_hash.encode()).decode()

    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO users (username, password_enc, created_at) VALUES (?, ?, ?)",
            (username, pw_enc, time.time()),
        )


def verify_user(username: str, password: str) -> bool:
    """Decrypt stored hash and verify the password."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT password_enc FROM users WHERE username = ?", (username,)
        ).fetchone()

    if not row:
        return False

    try:
        pw_hash = _fernet.decrypt(row["password_enc"].encode()).decode()
    except Exception:
        return False

    if not check_password_hash(pw_hash, password):
        return False

    with _connect() as conn:
        conn.execute(
            "UPDATE users SET last_login = ? WHERE username = ?",
            (time.time(), username),
        )
    return True


def delete_user(username: str):
    with _connect() as conn:
        conn.execute("DELETE FROM users WHERE username = ?", (username,))


def list_users() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT username, created_at, last_login FROM users ORDER BY created_at"
        ).fetchall()
    return [dict(r) for r in rows]


# ── Task store ────────────────────────────────────────────────────────────────

def _task_row_to_dict(row) -> dict:
    import json as _json
    return {
        "task_id":      row["task_id"],
        "task":         row["task_json"],
        "task_type":    row["task_type"],
        "status":       row["status"],
        "result":       _json.loads(row["result_json"]) if row["result_json"] else None,
        "created_at":   row["created_at"],
        "delivered_at": row["delivered_at"],
        "completed_at": row["completed_at"],
    }


def task_create(task_id: str, agent_id: str, task_type: str, task_json: str) -> dict:
    now = time.time()
    with _connect() as conn:
        conn.execute(
            """INSERT INTO tasks
               (task_id, agent_id, task_type, task_json, status, created_at)
               VALUES (?, ?, ?, ?, 'queued', ?)""",
            (task_id, agent_id, task_type, task_json, now),
        )
        row = conn.execute(
            "SELECT * FROM tasks WHERE task_id = ?", (task_id,)
        ).fetchone()
    return _task_row_to_dict(row)


def task_count_queued(agent_id: str) -> int:
    with _connect() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE agent_id = ? AND status = 'queued'",
            (agent_id,),
        ).fetchone()[0]


def task_get_next_queued(agent_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            """SELECT * FROM tasks
               WHERE agent_id = ? AND status = 'queued'
               ORDER BY created_at ASC LIMIT 1""",
            (agent_id,),
        ).fetchone()
    return _task_row_to_dict(row) if row else None


def task_mark_delivered(task_id: str):
    with _connect() as conn:
        conn.execute(
            "UPDATE tasks SET status = 'delivered', delivered_at = ? WHERE task_id = ?",
            (time.time(), task_id),
        )


def task_mark_completed(task_id: str, result_json: str):
    with _connect() as conn:
        conn.execute(
            """UPDATE tasks
               SET status = 'completed', result_json = ?, completed_at = ?
               WHERE task_id = ?""",
            (result_json, time.time(), task_id),
        )


def task_list_for_agent(agent_id: str) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE agent_id = ? ORDER BY created_at ASC",
            (agent_id,),
        ).fetchall()
    return [_task_row_to_dict(r) for r in rows]


def task_clear_for_agent(agent_id: str):
    with _connect() as conn:
        conn.execute("DELETE FROM tasks WHERE agent_id = ?", (agent_id,))


# ── Agent registry ────────────────────────────────────────────────────────────

def task_requeue_stale(delivered_timeout: float = 300):
    """Re-queue tasks stuck in 'delivered' for longer than delivered_timeout seconds.

    Called on server startup to recover tasks that were handed to an agent but
    never resulted in an upload (e.g. server was killed between delivery and result).
    """
    cutoff = time.time() - delivered_timeout
    with _connect() as conn:
        conn.execute(
            """UPDATE tasks SET status = 'queued', delivered_at = NULL
               WHERE status = 'delivered' AND delivered_at < ?""",
            (cutoff,),
        )


# ── Login rate limiter (SQLite-backed, safe across multiple workers) ──────────

def record_login_attempt(ip: str):
    with _connect() as conn:
        conn.execute(
            "INSERT INTO login_attempts (ip, attempted_at) VALUES (?, ?)",
            (ip, time.time()),
        )


def count_recent_attempts(ip: str, window: float) -> int:
    cutoff = time.time() - window
    with _connect() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM login_attempts WHERE ip = ? AND attempted_at > ?",
            (ip, cutoff),
        ).fetchone()[0]


def purge_old_attempts(window: float):
    """Remove attempt records outside the window to keep the table small."""
    cutoff = time.time() - window
    with _connect() as conn:
        conn.execute("DELETE FROM login_attempts WHERE attempted_at < ?", (cutoff,))


def agent_upsert(agent_id: str, hostname: str, os_name: str, user: str):
    with _connect() as conn:
        conn.execute(
            """INSERT INTO agents (agent_id, hostname, os, user, last_seen)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(agent_id) DO UPDATE SET
                   hostname  = excluded.hostname,
                   os        = excluded.os,
                   user      = excluded.user,
                   last_seen = excluded.last_seen""",
            (agent_id, hostname, os_name, user, time.time()),
        )


def agent_list() -> dict:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM agents").fetchall()
    return {r["agent_id"]: dict(r) for r in rows}
