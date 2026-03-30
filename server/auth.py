import os
import hmac
import secrets
import functools
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask import request, jsonify
from common.cryptography_helpers import AGENT_KEY

SECRET_KEY = os.environ.get("C2_SECRET_KEY")
if not SECRET_KEY:
    SECRET_KEY = secrets.token_hex(32)
    print("[!] C2_SECRET_KEY not set — using ephemeral key. Tokens will not survive restart.")

TOKEN_MAX_AGE = 8 * 3600  # 8 hours

_serializer = URLSafeTimedSerializer(SECRET_KEY)


def create_token(username: str) -> str:
    return _serializer.dumps(username, salt="operator-auth")


def verify_token(token: str):
    try:
        return _serializer.loads(token, salt="operator-auth", max_age=TOKEN_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None


def check_credentials(username: str, password: str) -> bool:
    from server.db import verify_user
    return verify_user(username, password)


def require_operator(f):
    """Protect operator-facing routes. Expects Authorization: Bearer <token>."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify({"error": "Unauthorized"}), 401
        username = verify_token(header[7:])
        if not username:
            return jsonify({"error": "Invalid or expired token"}), 401
        return f(*args, **kwargs)
    return decorated


def require_agent(f):
    """Protect agent-facing routes. Expects X-Agent-Key header matching AGENT_KEY."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not AGENT_KEY:
            print("[!] AGENT_KEY not configured — rejecting all agent requests.")
            return jsonify({"error": "Unauthorized"}), 401
        key = request.headers.get("X-Agent-Key", "")
        if not key or not hmac.compare_digest(key.encode(), AGENT_KEY.encode()):
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated
