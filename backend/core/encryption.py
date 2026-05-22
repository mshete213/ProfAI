from cryptography.fernet import Fernet, InvalidToken

from config import get_settings

settings = get_settings()


def _get_fernet() -> Fernet:
    key = settings.credentials_encryption_key
    # If the placeholder is still in place, generate a deterministic dev key from the JWT secret.
    if key == "your-fernet-key-here":
        import base64
        import hashlib

        digest = hashlib.sha256(settings.jwt_secret.encode()).digest()
        key = base64.urlsafe_b64encode(digest).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Failed to decrypt credential — encryption key may have rotated") from exc
