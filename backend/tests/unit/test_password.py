from infrastructure.auth.password import hash_password, verify_password


def test_hash_returns_string_different_from_input():
    hashed = hash_password("secret123")
    assert isinstance(hashed, str)
    assert hashed != "secret123"


def test_verify_correct_password():
    hashed = hash_password("secret123")
    assert verify_password("secret123", hashed) is True


def test_verify_wrong_password():
    hashed = hash_password("secret123")
    assert verify_password("wrong", hashed) is False


def test_same_password_produces_different_hashes():
    h1 = hash_password("secret123")
    h2 = hash_password("secret123")
    assert h1 != h2  # bcrypt random salt
