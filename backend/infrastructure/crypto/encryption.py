from functools import lru_cache

from cryptography.fernet import Fernet

from backend.config import get_settings


class APIKeyEncryptor:
    def __init__(self, fernet: Fernet) -> None:
        self._fernet = fernet

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        return self._fernet.decrypt(ciphertext.encode()).decode()

    @staticmethod
    def mask(api_key: str) -> str:
        """Return masked key like 'sk-...4f2c'."""
        if len(api_key) <= 8:
            return "***"
        return f"{api_key[:3]}...{api_key[-4:]}"


@lru_cache
def get_encryptor() -> APIKeyEncryptor:
    settings = get_settings()
    key = settings.ENCRYPTION_KEY
    if not key:
        raise RuntimeError(
            "ENCRYPTION_KEY is not set. Generate one with: "
            "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    return APIKeyEncryptor(Fernet(key.encode()))
