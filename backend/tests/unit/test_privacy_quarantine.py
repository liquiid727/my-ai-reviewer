"""Encrypted upload quarantine contracts."""

from cryptography.fernet import Fernet

from backend.infrastructure.privacy.quarantine import QuarantineCipher


def test_quarantine_cipher_round_trip_does_not_expose_source_bytes() -> None:
    source = b"private resume: zhangsan@example.com"
    cipher = QuarantineCipher(Fernet.generate_key().decode("ascii"))

    encrypted = cipher.encrypt(source)

    assert source not in encrypted
    assert cipher.decrypt(encrypted) == source
