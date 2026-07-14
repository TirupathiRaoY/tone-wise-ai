"""Authentication and first-time onboarding routes for ToneWise AI.

Email passwords use PBKDF2-HMAC-SHA256 with a unique random salt. OAuth uses
the standard free Google and GitHub OAuth endpoints; credentials stay in .env.
"""

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import requests
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, Field

from config import APP_URL, GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
from database import get_connection
from mailer import send_password_reset

router = APIRouter(prefix="/api/auth", tags=["authentication"])
PBKDF2_ITERATIONS = 600_000


class SignUpRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)


class SignInRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class ProfileUpdateRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)


class OnboardingRequest(BaseModel):
    user_type: str
    user_type_other: str | None = Field(default=None, max_length=80)
    field: str
    field_other: str | None = Field(default=None, max_length=80)
    goals: list[str] = Field(min_length=1, max_length=5)
    technical_background: str


USER_TYPES = {"Student", "Working Professional", "Job Seeker", "Business Owner", "Other"}
TECHNICAL_LEVELS = {"None at all", "A little", "Comfortable with basics", "Fairly technical"}
GOALS = {
    "Understanding technical reports/emails at work",
    "Learning industry terms as a student",
    "Preparing for interviews",
    "Helping my team communicate better",
    "Just exploring",
}


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ITERATIONS,
        base64.b64encode(salt).decode(),
        base64.b64encode(digest).decode(),
    )


def verify_password(password: str, stored_value: str | None) -> bool:
    if not stored_value:
        return False
    try:
        algorithm, iterations, salt, expected = stored_value.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), base64.b64decode(salt), int(iterations)
        )
        return hmac.compare_digest(actual, base64.b64decode(expected))
    except (ValueError, TypeError):
        return False


def public_user(row) -> dict:
    return {
        "id": row["id"], "full_name": row["full_name"], "email": row["email"],
        "onboarding_complete": bool(row["onboarding_complete"]),
    }


def login(request: Request, row) -> None:
    request.session.clear()
    request.session["user_id"] = row["id"]


def current_user(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    with get_connection() as connection:
        return connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def app_url(request: Request, path: str) -> str:
    return APP_URL.rstrip("/") + path if APP_URL else str(request.base_url).rstrip("/") + path


def redirect_for_user(row) -> str:
    return "/dashboard" if row["onboarding_complete"] else "/onboarding"


def reset_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@router.post("/signup")
def sign_up(payload: SignUpRequest, request: Request) -> dict:
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords don't match.")
    full_name = payload.full_name.strip()
    if not full_name:
        raise HTTPException(status_code=400, detail="Please enter your full name.")
    with get_connection() as connection:
        try:
            cursor = connection.execute(
                "INSERT INTO users (full_name, email, password_hash) VALUES (?, ?, ?)",
                (full_name, str(payload.email).lower(), hash_password(payload.password)),
            )
            user = connection.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()
        except Exception as error:
            if "UNIQUE constraint failed: users.email" in str(error):
                raise HTTPException(status_code=409, detail="An account with this email already exists.") from error
            raise
    login(request, user)
    return {"success": True, "user": public_user(user), "redirect": "/onboarding"}


@router.post("/signin")
def sign_in(payload: SignInRequest, request: Request) -> dict:
    with get_connection() as connection:
        user = connection.execute("SELECT * FROM users WHERE email = ?", (str(payload.email).lower(),)).fetchone()
    if user is None or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    login(request, user)
    return {"success": True, "user": public_user(user), "redirect": redirect_for_user(user)}


@router.post("/password-reset")
def request_password_reset(payload: PasswordResetRequest, request: Request) -> dict:
    """Email a one-time reset link without revealing whether an account exists."""
    with get_connection() as connection:
        user = connection.execute("SELECT * FROM users WHERE email = ?", (str(payload.email).lower(),)).fetchone()
        if user is None:
            return {"success": True, "message": "If an account exists for that email, a reset link has been sent."}
        token = secrets.token_urlsafe(32)
        token_digest = reset_token_hash(token)
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
        connection.execute("UPDATE password_reset_tokens SET used_at = CURRENT_TIMESTAMP WHERE user_id = ? AND used_at IS NULL", (user["id"],))
        connection.execute("INSERT INTO password_reset_tokens (user_id, token_hash, expires_at) VALUES (?, ?, ?)", (user["id"], token_digest, expires_at))
    try:
        send_password_reset(recipient=user["email"], reset_url=app_url(request, f"/reset-password?token={token}"))
    except RuntimeError as error:
        with get_connection() as connection:
            connection.execute("DELETE FROM password_reset_tokens WHERE token_hash = ?", (token_digest,))
        raise HTTPException(status_code=503, detail=str(error)) from error
    return {"success": True, "message": "If an account exists for that email, a reset link has been sent."}


@router.post("/password-reset/confirm")
def confirm_password_reset(payload: PasswordResetConfirmRequest) -> dict:
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords don't match.")
    token_digest = reset_token_hash(payload.token)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as connection:
        reset = connection.execute(
            "SELECT * FROM password_reset_tokens WHERE token_hash = ? AND used_at IS NULL AND expires_at > ?",
            (token_digest, now),
        ).fetchone()
        if reset is None:
            raise HTTPException(status_code=400, detail="This reset link is invalid or has expired. Request a new one.")
        connection.execute("UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (hash_password(payload.password), reset["user_id"]))
        connection.execute("UPDATE password_reset_tokens SET used_at = CURRENT_TIMESTAMP WHERE id = ?", (reset["id"],))
    return {"success": True, "redirect": "/signin?reset=success"}


@router.post("/logout")
def logout(request: Request) -> dict:
    request.session.clear()
    return {"success": True, "redirect": "/signin"}


@router.get("/me")
def me(request: Request) -> dict:
    user = current_user(request)
    if user is None:
        return {"authenticated": False}
    response = {"authenticated": True, "user": public_user(user)}
    if user["onboarding_complete"]:
        with get_connection() as connection:
            onboarding = connection.execute("SELECT * FROM user_onboarding WHERE user_id = ?", (user["id"],)).fetchone()
        if onboarding:
            response["preferences"] = {
                "default_tone": onboarding["default_tone"], "default_role": onboarding["default_role"],
            }
    return response


@router.patch("/profile")
def update_profile(payload: ProfileUpdateRequest, request: Request) -> dict:
    user = current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Please sign in to continue.")
    full_name = payload.full_name.strip()
    if not full_name:
        raise HTTPException(status_code=400, detail="Please enter your name.")
    with get_connection() as connection:
        connection.execute(
            "UPDATE users SET full_name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (full_name, user["id"]),
        )
        updated_user = connection.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()
    return {"success": True, "user": public_user(updated_user)}


@router.post("/onboarding")
def save_onboarding(payload: OnboardingRequest, request: Request) -> dict:
    user = current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Please sign in to continue.")
    if user["onboarding_complete"]:
        return {"success": True, "redirect": "/dashboard"}
    if payload.user_type not in USER_TYPES or payload.technical_background not in TECHNICAL_LEVELS:
        raise HTTPException(status_code=400, detail="Please choose a valid answer.")
    if not set(payload.goals).issubset(GOALS):
        raise HTTPException(status_code=400, detail="One of the selected goals is not valid.")
    if payload.user_type == "Other" and not (payload.user_type_other or "").strip():
        raise HTTPException(status_code=400, detail="Please describe yourself.")
    if payload.field == "Other" and not (payload.field_other or "").strip():
        raise HTTPException(status_code=400, detail="Please enter your role or field.")
    # A helpful first default; people can still change the selectors on the app.
    role_map = {"HR": "HR Staff", "Sales": "Sales Team", "Admin": "Admin/Operations", "Support": "Customer Support"}
    default_role = role_map.get(payload.field, "General Non-Technical Staff")
    default_tone = "Very Simple (ELI5)" if payload.technical_background in {"None at all", "A little"} else "Casual"
    with get_connection() as connection:
        connection.execute(
            """INSERT INTO user_onboarding
               (user_id, user_type, user_type_other, field, field_other, goals_json, technical_background, default_tone, default_role)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user["id"], payload.user_type, (payload.user_type_other or "").strip() or None,
             payload.field, (payload.field_other or "").strip() or None, json.dumps(payload.goals),
             payload.technical_background, default_tone, default_role),
        )
        connection.execute("UPDATE users SET onboarding_complete = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (user["id"],))
    return {"success": True, "redirect": "/dashboard", "preferences": {"default_tone": default_tone, "default_role": default_role}}


@router.get("/oauth/{provider}")
def oauth_start(provider: str, request: Request) -> RedirectResponse:
    if provider not in {"google", "github"}:
        raise HTTPException(status_code=404, detail="Unknown sign-in provider.")
    client_id, client_secret = (
        (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET)
        if provider == "google"
        else (GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET)
    )
    if not client_id or not client_secret:
        return RedirectResponse(f"/signin?error=oauth_not_configured&provider={provider}", status_code=303)
    state = secrets.token_urlsafe(24)
    request.session["oauth_state"] = state
    request.session["oauth_provider"] = provider
    # Return only to local paths after OAuth; never allow an external redirect.
    next_path = request.query_params.get("next", "")
    request.session["oauth_next"] = next_path if next_path.startswith("/") and not next_path.startswith("//") else ""
    redirect_uri = app_url(request, f"/api/auth/oauth/{provider}/callback")
    if provider == "google":
        params = {"client_id": client_id, "redirect_uri": redirect_uri, "response_type": "code", "scope": "openid email profile", "state": state, "prompt": "select_account"}
        url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    else:
        params = {"client_id": client_id, "redirect_uri": redirect_uri, "scope": "read:user user:email", "state": state}
        url = "https://github.com/login/oauth/authorize?" + urlencode(params)
    return RedirectResponse(url)


@router.get("/oauth/{provider}/callback")
def oauth_callback(provider: str, request: Request, code: str = "", state: str = "") -> RedirectResponse:
    if provider not in {"google", "github"}:
        return RedirectResponse("/signin?error=oauth_failed", status_code=303)
    next_path = request.session.pop("oauth_next", "")
    expected_state = request.session.pop("oauth_state", "")
    if provider != request.session.pop("oauth_provider", None) or not expected_state or not secrets.compare_digest(state, expected_state):
        return RedirectResponse("/signin?error=oauth_state")
    if not code:
        return RedirectResponse("/signin?error=oauth_cancelled")
    redirect_uri = app_url(request, f"/api/auth/oauth/{provider}/callback")
    try:
        if provider == "google":
            token_response = requests.post("https://oauth2.googleapis.com/token", data={"code": code, "client_id": GOOGLE_CLIENT_ID, "client_secret": GOOGLE_CLIENT_SECRET, "redirect_uri": redirect_uri, "grant_type": "authorization_code"}, timeout=10)
            token_response.raise_for_status()
            token = token_response.json()
            profile_response = requests.get("https://www.googleapis.com/oauth2/v3/userinfo", headers={"Authorization": f"Bearer {token['access_token']}"}, timeout=10)
            profile_response.raise_for_status()
            profile = profile_response.json()
            if not profile.get("email_verified"):
                raise ValueError("Google did not provide a verified email")
            subject, email, name = profile["sub"], profile["email"], profile.get("name") or profile["email"]
        else:
            token_response = requests.post("https://github.com/login/oauth/access_token", data={"code": code, "client_id": GITHUB_CLIENT_ID, "client_secret": GITHUB_CLIENT_SECRET, "redirect_uri": redirect_uri}, headers={"Accept": "application/json"}, timeout=10)
            token_response.raise_for_status()
            token = token_response.json()
            if token.get("error") or not token.get("access_token"):
                raise ValueError("GitHub did not return an access token")
            headers = {"Authorization": f"Bearer {token['access_token']}", "Accept": "application/vnd.github+json"}
            profile_response = requests.get("https://api.github.com/user", headers=headers, timeout=10)
            profile_response.raise_for_status()
            profile = profile_response.json()
            emails_response = requests.get("https://api.github.com/user/emails", headers=headers, timeout=10)
            emails_response.raise_for_status()
            emails = emails_response.json()
            email = next((item["email"] for item in emails if item.get("primary") and item.get("verified")), None)
            if not email:
                raise ValueError("GitHub did not provide a verified primary email")
            subject, name = str(profile["id"]), profile.get("name") or profile.get("login") or email
        with get_connection() as connection:
            user = connection.execute(
                """SELECT users.* FROM user_oauth_identities
                   JOIN users ON users.id = user_oauth_identities.user_id
                   WHERE provider = ? AND subject = ?""",
                (provider, subject),
            ).fetchone()
            if user is None:
                user = connection.execute("SELECT * FROM users WHERE email = ?", (email.lower(),)).fetchone()
                if user is None:
                    cursor = connection.execute("INSERT INTO users (full_name, email, oauth_provider, oauth_subject) VALUES (?, ?, ?, ?)", (name, email.lower(), provider, subject))
                    user = connection.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()
                connection.execute(
                    "INSERT OR IGNORE INTO user_oauth_identities (provider, subject, user_id) VALUES (?, ?, ?)",
                    (provider, subject, user["id"]),
                )
    except (KeyError, ValueError, requests.RequestException):
        return RedirectResponse("/signin?error=oauth_failed")
    login(request, user)
    return RedirectResponse(next_path or redirect_for_user(user))
