from cryptography.fernet import Fernet

# Pre-shared key (same value in agent + server)
SHARED_KEY = b"PBij7BOiAykMIjYqmVY-0kpdgyyXbaJJpoQrZRVCl9A="

cipher = Fernet(SHARED_KEY)

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