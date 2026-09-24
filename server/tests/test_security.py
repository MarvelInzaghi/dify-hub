from app.security import decrypt_token, encrypt_token


def test_roundtrip():
    token = "app-abc123-secret-value"
    enc = encrypt_token(token)
    assert enc is not None
    assert enc != token
    assert decrypt_token(enc) == token


def test_none_and_empty_unchanged():
    assert encrypt_token(None) is None
    assert decrypt_token(None) is None
    assert encrypt_token("") == ""
    assert decrypt_token("") == ""


def test_decrypt_plaintext_falls_back_gracefully():
    # Values written before encryption was enabled stay readable.
    assert decrypt_token("app-plain-legacy-token") == "app-plain-legacy-token"


def test_encryption_is_non_deterministic_but_roundtrips():
    # Fernet uses a random IV per encryption: ciphertexts differ, but both decrypt correctly.
    a = encrypt_token("abc")
    b = encrypt_token("abc")
    assert a != b
    assert decrypt_token(a) == "abc"
    assert decrypt_token(b) == "abc"
