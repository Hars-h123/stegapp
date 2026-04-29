from cryptography.fernet import Fernet
import base64
import hashlib


def generate_key(password):
    key = hashlib.sha256(password.encode()).digest()
    return base64.urlsafe_b64encode(key)


def encrypt_message(message, password):
    """Encrypt a string. Returns bytes."""
    key = generate_key(password)
    cipher = Fernet(key)
    encrypted = cipher.encrypt(message.encode())
    return encrypted


def decrypt_message(encrypted_data, password):
    """Decrypt bytes produced by encrypt_message. Returns string."""
    key = generate_key(password)
    cipher = Fernet(key)
    decrypted = cipher.decrypt(encrypted_data)
    return decrypted.decode()


# ── NEW: binary variants (no base64 round-trip for file payloads) ──────────

def encrypt_bytes(data: bytes, password: str) -> bytes:
    """Encrypt raw bytes directly. Much faster for large binary files."""
    key = generate_key(password)
    cipher = Fernet(key)
    return cipher.encrypt(data)


def decrypt_bytes(encrypted_data: bytes, password: str) -> bytes:
    """Decrypt bytes produced by encrypt_bytes. Returns raw bytes."""
    key = generate_key(password)
    cipher = Fernet(key)
    return cipher.decrypt(encrypted_data)