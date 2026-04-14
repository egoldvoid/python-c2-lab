from cryptography.fernet import Fernet
import os

# Agent authentication key — set C2_AGENT_KEY env var, or place in config/agent_key
def _load_agent_key() -> str:
    val = os.environ.get("C2_AGENT_KEY")
    if val:
        return val
    key_path = os.path.join(os.path.dirname(__file__), "..", "config", "agent_key")
    try:
        with open(key_path) as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""

# Shared encryption key — set C2_SHARED_KEY env var, or place in config/shared_key
def _load_shared_key() -> bytes:
    val = os.environ.get("C2_SHARED_KEY")
    if val:
        return val.encode()
    key_path = os.path.join(os.path.dirname(__file__), "..", "config", "shared_key")
    try:
        with open(key_path, "rb") as f:
            return f.read().strip()
    except FileNotFoundError:
        raise RuntimeError(
            "No shared encryption key found. "
            "Set C2_SHARED_KEY env var or create config/shared_key."
        )

AGENT_KEY = _load_agent_key()

cipher = Fernet(_load_shared_key())

def encrypt_string(plaintext: str) -> str:
    """
    Takes a UTF-8 string, returns base64 string.
    """
    return cipher.encrypt(plaintext.encode()).decode()

def decrypt_string(ciphertext: str) -> str:
    """
    Takes base64 string, returns UTF-8 string.
    Raises exception on failure.
    """
    return cipher.decrypt(ciphertext.encode()).decode()