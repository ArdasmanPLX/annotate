import os
import base64
import hashlib

API_KEY_FILE = "openai.key"
SECRET = "simple_secret_key"


def _derive_key(secret: str) -> bytes:
    return hashlib.sha256(secret.encode()).digest()


def _xor_bytes(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def encrypt_string(text: str, secret: str = SECRET) -> str:
    key = _derive_key(secret)
    encrypted = _xor_bytes(text.encode(), key)
    return base64.b64encode(encrypted).decode()


def decrypt_string(enc_text: str, secret: str = SECRET) -> str:
    key = _derive_key(secret)
    data = base64.b64decode(enc_text.encode())
    return _xor_bytes(data, key).decode()


def get_openai_api_key() -> str:
    if os.path.exists(API_KEY_FILE):
        with open(API_KEY_FILE, "r") as f:
            encrypted = f.read().strip()
        try:
            return decrypt_string(encrypted)
        except Exception:
            pass
    key = input("Enter OpenAI API key: ").strip()
    with open(API_KEY_FILE, "w") as f:
        f.write(encrypt_string(key))
    return key
