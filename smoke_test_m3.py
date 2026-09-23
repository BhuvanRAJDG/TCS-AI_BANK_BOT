"""
Smoke test for Milestone 3 – Auth & Security.
Run from the project root:
    python smoke_test_m3.py
Does NOT require a running database – tests import chains and in-memory logic only.
"""
import sys
import os
import traceback
import io

# Force UTF-8 output on Windows consoles
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

results = []

def ok(label):
    results.append(('PASS', label))
    print(f"  ✓  {label}")

def fail(label, detail=''):
    results.append(('FAIL', label))
    print(f"  ✗  {label}")
    if detail:
        print(f"       {detail}")


# ── 1. Module imports ──────────────────────────────────────────────────────────
print("\n[1] Imports")

try:
    from app.security.password import hash_password, verify_password, validate_password_strength
    ok("app.security.password imports")
except Exception as e:
    fail("app.security.password imports", str(e))

try:
    from app.security.device import get_device_fingerprint, get_client_ip, build_device_info
    ok("app.security.device imports")
except Exception as e:
    fail("app.security.device imports", str(e))

try:
    from app.security.rate_limit import _sliding_window_check
    ok("app.security.rate_limit imports")
except Exception as e:
    fail("app.security.rate_limit imports", str(e))

try:
    from app.auth.otp_service import generate_otp, verify_otp, invalidate_otp
    ok("app.auth.otp_service imports")
except Exception as e:
    fail("app.auth.otp_service imports", str(e))


# ── 2. Password hashing ───────────────────────────────────────────────────────
print("\n[2] Password utilities")

try:
    hashed = hash_password("MySecureP@ss1")
    assert verify_password("MySecureP@ss1", hashed), "verify_password returned False"
    assert not verify_password("wrongpass", hashed),  "verify_password should be False"
    ok("bcrypt hash + verify")
except Exception as e:
    fail("bcrypt hash + verify", str(e))

try:
    errors = validate_password_strength("weak")
    assert len(errors) > 0, "Expected strength errors for 'weak'"
    ok("password strength validation (weak password rejected)")
except Exception as e:
    fail("password strength validation", str(e))

try:
    errors = validate_password_strength("Str0ng@Pass!")
    assert len(errors) == 0, f"Expected no errors, got: {errors}"
    ok("password strength validation (strong password accepted)")
except Exception as e:
    fail("password strength validation (strong)", str(e))


# ── 3. OTP service ────────────────────────────────────────────────────────────
print("\n[3] OTP service")

try:
    otp = generate_otp(9999)
    assert len(otp) == 6 and otp.isdigit(), f"Bad OTP format: {otp}"
    ok("OTP generation (6-digit)")
except Exception as e:
    fail("OTP generation", str(e))

try:
    otp = generate_otp(8888)
    valid, msg = verify_otp(8888, otp)
    assert valid, f"Expected valid=True, got: {msg}"
    ok("OTP verify (correct code)")
except Exception as e:
    fail("OTP verify (correct code)", str(e))

try:
    generate_otp(7777)
    valid, msg = verify_otp(7777, "000000")
    assert not valid, "Expected valid=False for wrong OTP"
    ok("OTP reject (wrong code)")
except Exception as e:
    fail("OTP reject", str(e))

try:
    # Exhaust attempts
    generate_otp(6666)
    for _ in range(3):
        verify_otp(6666, "000000")
    valid, msg = verify_otp(6666, "000000")
    assert not valid, "Expected lockout after 3 failed attempts"
    ok("OTP lockout after 3 failed attempts")
except Exception as e:
    fail("OTP lockout", str(e))


# ── 4. Rate limiter ───────────────────────────────────────────────────────────
print("\n[4] Rate limiter")

try:
    from app.security.rate_limit import _sliding_window_check, _STORE
    _STORE.clear()
    for i in range(5):
        allowed, _ = _sliding_window_check("test:smoke", 5, 60)
        assert allowed, f"Request {i+1} should be allowed"
    allowed, retry = _sliding_window_check("test:smoke", 5, 60)
    assert not allowed, "6th request should be blocked"
    assert retry > 0, "retry_after should be > 0"
    ok("sliding window rate limiter (5/60s)")
    _STORE.clear()
except Exception as e:
    fail("rate limiter", str(e))


# ── 5. JWT creation (needs app context) ──────────────────────────────────────
print("\n[5] JWT tokens (app context)")

try:
    class TestConfig:
        SECRET_KEY                    = 'smoke-test-secret'
        JWT_SECRET_KEY                = 'smoke-jwt-secret'
        JWT_ACCESS_MINUTES            = '15'
        JWT_REFRESH_DAYS              = '30'
        SQLALCHEMY_DATABASE_URI       = 'sqlite:///:memory:'
        SQLALCHEMY_TRACK_MODIFICATIONS= False
        FLASK_DEBUG                   = True
        DEBUG                         = True
        TESTING                       = True
        OTP_EXPIRATION_SECONDS        = 300
        CHROMA_PERSIST_DIRECTORY      = '/tmp/chroma_test'
        LLM_PROVIDER                  = 'mock'
        LLM_API_KEY                   = ''
        TRANSLATION_PROVIDER          = 'mock'
        TRANSLATION_API_KEY           = ''
        LANGUAGES                     = ['en']
        DEFAULT_LANGUAGE              = 'en'

    from app import create_app
    test_app = create_app(config_object=TestConfig)
    with test_app.app_context():
        from app.security.jwt import create_access_token, create_refresh_token, decode_token

        access = create_access_token(1, 'customer')
        payload = decode_token(access)
        assert payload['sub'] == '1'
        assert payload['role'] == 'customer'
        assert payload['type'] == 'access'
        ok("JWT access token create + decode")

        refresh, exp = create_refresh_token(1)
        rpayload = decode_token(refresh)
        assert rpayload['type'] == 'refresh'
        ok("JWT refresh token create + decode")

except Exception as e:
    fail("JWT tokens", traceback.format_exc())


# ── 6. Blueprint registration ─────────────────────────────────────────────────
print("\n[6] Blueprint registration")

try:
    with test_app.app_context():
        rules = [str(r) for r in test_app.url_map.iter_rules()]
        expected = ['/auth/register', '/auth/login', '/auth/mfa/request',
                    '/auth/mfa/verify', '/auth/refresh', '/auth/logout',
                    '/auth/logout-all', '/auth/me', '/health']
        for ep in expected:
            assert ep in rules, f"Route {ep!r} not registered. Got: {rules}"
        ok(f"All {len(expected)} routes registered")
except Exception as e:
    fail("Blueprint registration", traceback.format_exc())


# ── Summary ───────────────────────────────────────────────────────────────────
passed = sum(1 for s, _ in results if s == 'PASS')
failed = sum(1 for s, _ in results if s == 'FAIL')
print(f"\n{'='*50}")
print(f"  Results: {passed} passed / {failed} failed")
print(f"{'='*50}\n")
sys.exit(0 if failed == 0 else 1)
