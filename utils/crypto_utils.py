from cryptography.fernet import Fernet
import base64
import hashlib


def generate_key(password):
    key = hashlib.sha256(password.encode()).digest()
    return base64.urlsafe_b64encode(key)


def encrypt_message(message, password):
    key = generate_key(password)
    cipher = Fernet(key)
    encrypted = cipher.encrypt(message.encode())
    return encrypted


def decrypt_message(encrypted_data, password):
    key = generate_key(password)
    cipher = Fernet(key)
    decrypted = cipher.decrypt(encrypted_data)
    return decrypted.decode()