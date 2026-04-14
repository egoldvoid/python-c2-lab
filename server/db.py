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
