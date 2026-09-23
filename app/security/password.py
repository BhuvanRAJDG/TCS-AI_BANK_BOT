"""
app/security/password.py
bcrypt password hashing + validation helpers.
"""
import re
import bcrypt


# ── hashing ──────────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """Return bcrypt-hashed password string."""
    return bcrypt.hashpw(plain.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches hashed."""
    try:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False


# ── strength validation ───────────────────────────────────────────────────────

class PasswordStrengthError(ValueError):
    pass


_RULES = [
    (r'.{8,}',       'Password must be at least 8 characters.'),
    (r'[A-Z]',       'Password must contain at least one uppercase letter.'),
    (r'[a-z]',       'Password must contain at least one lowercase letter.'),
    (r'\d',          'Password must contain at least one digit.'),
    (r'[^A-Za-z\d]', 'Password must contain at least one special character.'),
]


def validate_password_strength(password: str) -> list[str]:
    """Return a list of error messages; empty list means password is strong."""
    errors = []
    for pattern, msg in _RULES:
        if not re.search(pattern, password):
            errors.append(msg)
    return errors


def assert_password_strong(password: str):
    """Raise PasswordStrengthError if password is weak."""
    errors = validate_password_strength(password)
    if errors:
        raise PasswordStrengthError(' '.join(errors))
