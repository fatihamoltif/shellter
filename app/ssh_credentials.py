import secrets
import string

from cryptography.fernet import Fernet
from flask import current_app


def _get_fernet():
    key = current_app.config["INSTANCE_ENCRYPTION_KEY"]
    if not key:
        raise RuntimeError("INSTANCE_ENCRYPTION_KEY n'est pas configuree")
    return Fernet(key.encode())


def generate_ssh_username(instance_id):
    return f"user{instance_id}"


def generate_ssh_password(length=16):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def encrypt_password(plain_password):
    return _get_fernet().encrypt(plain_password.encode()).decode()


def decrypt_password(encrypted_password):
    return _get_fernet().decrypt(encrypted_password.encode()).decode()


def reveal_password(secret):
    """Déchiffre un secret stocké ; tolère un ancien secret en clair (retourné tel quel)."""
    if not secret:
        return secret
    try:
        return decrypt_password(secret)
    except Exception:
        return secret


def build_ssh_command(username, worker_ip, port):
    return f"ssh {username}@{worker_ip} -p {port}"
