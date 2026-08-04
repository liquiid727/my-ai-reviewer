"""Application-level encryption for short-lived resume quarantine objects."""

from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_PREFIX = b"RIP009\x00"


class QuarantineCipher:
    def __init__(self, encoded_key: str) -> None:
        try:
            key = base64.urlsafe_b64decode(encoded_key.encode("ascii"))
        except Exception as exc:
            raise ValueError("Invalid privacy quarantine key") from exc
        if len(key) != 32:
            raise ValueError("Privacy quarantine key must encode 32 bytes")
        self._cipher = AESGCM(key)

    def encrypt(self, source: bytes) -> bytes:
        nonce = os.urandom(12)
        return _PREFIX + nonce + self._cipher.encrypt(nonce, source, _PREFIX)

    def decrypt(self, encrypted: bytes) -> bytes:
        if not encrypted.startswith(_PREFIX) or len(encrypted) < len(_PREFIX) + 13:
            raise ValueError("Invalid privacy quarantine payload")
        offset = len(_PREFIX)
        nonce = encrypted[offset:offset + 12]
        return self._cipher.decrypt(nonce, encrypted[offset + 12:], _PREFIX)

