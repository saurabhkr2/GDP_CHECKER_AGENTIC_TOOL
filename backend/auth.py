"""
Authentication for the agentic backend.

LDAP (Active Directory) login folded into the existing Flask app as a
Blueprint. A successful bind issues an opaque session id stored server-side
(Redis, with an in-memory fallback for local dev) and returned to the browser
as an httponly cookie.

Endpoints
---------
POST /api/login    authenticate against LDAP, create a session, set cookie
POST /api/logout   destroy the current session + clear the cookie
GET  /api/me       return the logged-in user for the current session

The ``register_auth`` helper also installs a ``before_request`` guard that
protects every other ``/api/*`` route when ``AUTH_ENABLED`` is true.
"""
from __future__ import annotations

import time
import uuid
from functools import wraps
from typing import Any, Dict, Optional

from flask import Blueprint, Flask, jsonify, request

from agentic.config import settings

SESSION_COOKIE = "session_id"

# Routes that must stay reachable without a valid session.
_PUBLIC_PATHS = {
    "/api/login",
    "/api/logout",
    "/api/me",
    "/api/health",
    # Machine-to-machine monitoring API — guarded by its own API key,
    # not the LDAP session cookie.
    "/api/monitoring/usage",
    "/api/monitoring/summary",
}


# ---------------------------------------------------------------------------
# Session store (Redis with in-memory fallback)
# ---------------------------------------------------------------------------
class InMemorySessionStore:
    """Minimal drop-in replacement for redis when no Redis server is available.

    Supports the subset of the Redis API used here: ping, setex, get, delete.
    Note: per-process only, so it is unsuitable for multi-worker deployments —
    use a real Redis there.
    """

    def __init__(self) -> None:
        self._data: Dict[str, Any] = {}  # key -> (value, expires_at_epoch | None)

    def ping(self) -> bool:
        return True

    def setex(self, key: str, seconds: int, value: str) -> None:
        self._data[key] = (value, time.time() + seconds)

    def get(self, key: str) -> Optional[str]:
        item = self._data.get(key)
        if item is None:
            return None
        value, expires_at = item
        if expires_at is not None and time.time() > expires_at:
            self._data.pop(key, None)
            return None
        return value

    def delete(self, *keys: str) -> None:
        for key in keys:
            self._data.pop(key, None)


def _create_session_store():
    try:
        import redis  # imported lazily so the dependency is optional in dev

        client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=True,
        )
        client.ping()
        print(f"[auth] connected to Redis at {settings.redis_host}:{settings.redis_port}")
        return client
    except Exception as exc:  # pragma: no cover - depends on environment
        print(f"[auth] Redis unavailable, using in-memory session store: {exc}")
        return InMemorySessionStore()


_store = None


def _session_store():
    global _store
    if _store is None:
        _store = _create_session_store()
    return _store


def _session_key(session_id: str) -> str:
    return f"session:{session_id}"


# ---------------------------------------------------------------------------
# LDAP authentication
# ---------------------------------------------------------------------------
def authenticate_and_get_user(email: str, password: str) -> Optional[Dict[str, str]]:
    """Bind to LDAP as ``email`` and, on success, fetch the user's attributes."""
    try:
        from ldap3 import ALL, Connection, Server

        srv = Server(settings.ldap_server, port=settings.ldap_port, get_info=ALL)

        # Step 1: authenticate the user directly (bind with their email).
        conn = Connection(srv, user=email, password=password, auto_bind=True)

        # Step 2: fetch user details.
        conn.search(
            search_base=settings.ldap_base,
            search_filter=f"(mail={email})",
            attributes=["mail", "employeeID", "displayName", "sAMAccountName"],
        )

        if not conn.entries:
            return None

        user = conn.entries[0]
        return {
            "email": user.mail.value,
            "employeeID": user.employeeID.value,
            # Keep UI/session username as the login email id.
            "username": user.mail.value,
            "code_id": user.sAMAccountName.value,
            "name": user.displayName.value,
        }
    except Exception as exc:  # pragma: no cover - depends on environment
        print(f"[auth] LDAP error: {exc}")
        return None


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------
def current_user() -> Optional[str]:
    """Return the username bound to the request's session cookie, or None."""
    session_id = request.cookies.get(SESSION_COOKIE)
    if not session_id:
        return None
    try:
        return _session_store().get(_session_key(session_id))
    except Exception:
        return None


def login_required(view):
    """Decorator that rejects unauthenticated requests with HTTP 401."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        if settings.auth_enabled and not current_user():
            return jsonify({"error": "authentication required"}), 401
        return view(*args, **kwargs)

    return wrapper


# ---------------------------------------------------------------------------
# Blueprint
# ---------------------------------------------------------------------------
auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    try:
        _session_store().ping()
    except Exception as redis_err:
        return jsonify({"error": f"session service error: {redis_err}"}), 503

    user = authenticate_and_get_user(username, password)
    if not user:
        return jsonify({"error": "invalid credentials"}), 401

    session_id = str(uuid.uuid4())
    _session_store().setex(
        _session_key(session_id), settings.session_expire_seconds, user["username"]
    )

    resp = jsonify(
        {
            "message": "Login successful",
            "employeeID": user["employeeID"],
            "username": user["username"],
            "name": user["name"],
            "email": user["email"],
        }
    )
    resp.set_cookie(
        SESSION_COOKIE,
        session_id,
        httponly=True,
        max_age=settings.session_expire_seconds,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
    )
    return resp


@auth_bp.post("/api/logout")
def logout():
    session_id = request.cookies.get(SESSION_COOKIE)
    if session_id:
        try:
            _session_store().delete(_session_key(session_id))
        except Exception:
            pass
    resp = jsonify({"message": "Logged out"})
    resp.delete_cookie(SESSION_COOKIE, samesite=settings.session_cookie_samesite)
    return resp


@auth_bp.get("/api/me")
def me():
    username = current_user()
    if not username:
        return jsonify({"error": "not authenticated"}), 401
    return jsonify({"username": username, "authenticated": True})


# ---------------------------------------------------------------------------
# Wiring
# ---------------------------------------------------------------------------
def register_auth(app: Flask) -> None:
    """Register the auth blueprint and the API access guard on ``app``."""
    app.register_blueprint(auth_bp)

    @app.before_request
    def _guard():  # pragma: no cover - exercised via integration
        if not settings.auth_enabled:
            return None
        # Always allow CORS preflight and public/auth endpoints.
        if request.method == "OPTIONS":
            return None
        path = request.path
        if not path.startswith("/api/"):
            return None
        if path in _PUBLIC_PATHS:
            return None
        if not current_user():
            return jsonify({"error": "authentication required"}), 401
        return None
