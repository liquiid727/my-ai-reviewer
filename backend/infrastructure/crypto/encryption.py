"""API Key 加密模块 —— 使用 Fernet 对称加密保护敏感的 API 密钥。"""

from functools import lru_cache

from cryptography.fernet import Fernet

from backend.config import get_settings


class APIKeyEncryptor:
    """API Key 加密/解密/脱敏工具类。"""

    def __init__(self, fernet: Fernet) -> None:
        self._fernet = fernet

    def encrypt(self, plaintext: str) -> str:
        """加密明文 API Key。"""
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """解密已加密的 API Key。"""
        return self._fernet.decrypt(ciphertext.encode()).decode()

    @staticmethod
    def mask(api_key: str) -> str:
        """脱敏显示 API Key，如 'sk-...4f2c'。"""
        if len(api_key) <= 8:
            return "***"
        return f"{api_key[:3]}...{api_key[-4:]}"


@lru_cache
def get_encryptor() -> APIKeyEncryptor:
    """获取全局加密器单例。首次调用时从环境变量加载密钥。"""
    settings = get_settings()
    key = settings.ENCRYPTION_KEY
    if not key:
        raise RuntimeError(
            "ENCRYPTION_KEY is not set. Generate one with: "
            "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    return APIKeyEncryptor(Fernet(key.encode()))
