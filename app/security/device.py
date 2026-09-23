"""
app/security/device.py
Device fingerprinting for session tracking.
"""
import hashlib
import json
from flask import request


def get_device_fingerprint() -> str:
    """
    Build a semi-stable fingerprint from request headers.
    Not crypto-secure; used only for session grouping.
    """
    components = {
        'ua':      request.headers.get('User-Agent', ''),
        'lang':    request.headers.get('Accept-Language', ''),
        'enc':     request.headers.get('Accept-Encoding', ''),
        'ip':      get_client_ip(),
    }
    raw = json.dumps(components, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def get_client_ip() -> str:
    """
    Extract real client IP, respecting X-Forwarded-For (reverse proxy).
    """
    forwarded = request.headers.get('X-Forwarded-For')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.remote_addr or '0.0.0.0'


def build_device_info() -> str:
    """
    Return JSON string with device metadata for Session.device_info.
    """
    return json.dumps({
        'user_agent':  request.headers.get('User-Agent', '')[:500],
        'platform':    request.headers.get('Sec-Ch-Ua-Platform', 'Unknown'),
        'mobile':      request.headers.get('Sec-Ch-Ua-Mobile', '?0'),
        'fingerprint': get_device_fingerprint(),
        'ip':          get_client_ip(),
    })
