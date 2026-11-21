import hashlib
import secrets
import re
from datetime import datetime, timedelta
from functools import wraps
from flask import session, redirect, url_for, flash, request, abort, jsonify
from database import get_db

EMAIL_REGEX = re.compile(r"^[\w\.\+\-]+@[\w\-]+\.[a-zA-Z]{2,}$")
SALT_LENGTH = 16
HASH_ITERATIONS = 200_000

def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with a unique cryptographic salt."""
    salt = secrets.token_hex(SALT_LENGTH)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        HASH_ITERATIONS
    )
    return f"{salt}${key.hex()}"

def verify_password(stored_password: str, provided_password: str) -> bool:
    """Safely verify provided password against the stored salt$hash in constant time."""
    try:
        salt, stored_hash = stored_password.split('$', 1)
        key = hashlib.pbkdf2_hmac(
            'sha256',
            provided_password.encode('utf-8'),
            salt.encode('utf-8'),
            HASH_ITERATIONS
        )
        return secrets.compare_digest(key.hex(), stored_hash)
    except Exception:
        return False

def validate_signup_inputs(name: str, email: str, password: str, role: str):
    """Validate sign up input parameters. Returns (is_valid, error_message)."""
    if not name or len(name.strip()) < 2:
        return False, "Please enter a valid full name (at least 2 characters)."
    
    if not email or not EMAIL_REGEX.match(email.strip()):
        return False, "Please enter a valid email address (e.g., alex@example.com)."
    
    if not password:
        return False, "Password is required."
    
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    
    if not re.search(r"[A-Za-z]", password):
        return False, "Password must contain at least one letter."
        
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number."
        
    if role not in ('participant', 'organizer'):
        return False, "Please select a valid role (Participant or Organizer)."
        
    return True, None

def get_current_user():
    """Retrieve logged-in user dict from session or None."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    db = get_db()
    try:
        user = db.execute(
            "SELECT id, name, email, role, status, bio, avatar_url, created_at FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
    except Exception:
        # Fallback if status column is pending migration
        user = db.execute(
            "SELECT id, name, email, role, bio, avatar_url, created_at FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
    db.close()
    return user

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required. Please log in."}), 401
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth_login", next=request.path))

        # Validate that the user still exists in DB
        user = get_current_user()
        if not user:
            session.clear()
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"error": "Session expired. Please log in again."}), 401
            flash("Your session has expired. Please sign in to continue.", "info")
            return redirect(url_for("auth_login", next=request.path))

        if dict(user).get("status") == "suspended":
            session.clear()
            flash("Your account has been suspended by a platform administrator.", "danger")
            return redirect(url_for("auth_login"))

        return f(*args, **kwargs)
    return decorated_function

def role_required(required_role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                if request.is_json or request.path.startswith("/api/"):
                    return jsonify({"error": "Authentication required."}), 401
                flash("Please log in to access this page.", "warning")
                return redirect(url_for("auth_login", next=request.path))

            user = get_current_user()
            if not user:
                session.clear()
                flash("Your session has expired. Please log in again.", "info")
                return redirect(url_for("auth_login", next=request.path))

            user_role = user["role"]
            # Admin accounts have full elevated privileges to all management sections
            if user_role != required_role and user_role != "admin":
                if request.is_json or request.path.startswith("/api/"):
                    return jsonify({"error": f"Forbidden: This action requires the '{required_role}' role."}), 403
                flash(f"Access denied. This area is reserved for {required_role}s.", "danger")
                if user_role == "organizer":
                    return redirect(url_for("organizer_dashboard"))
                elif user_role == "participant":
                    return redirect(url_for("participant_dashboard"))
                elif user_role == "admin":
                    return redirect(url_for("admin_dashboard"))
                return redirect(url_for("index"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def generate_reset_token(user_id: int) -> str:
    """Generate and record a secure password reset token valid for 1 hour."""
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    db = get_db()
    db.execute(
        "INSERT INTO password_resets (user_id, token, expires_at, used) VALUES (?, ?, ?, 0)",
        (user_id, token, expires_at)
    )
    db.commit()
    db.close()
    return token

def verify_reset_token(token: str):
    """Verify reset token and return user_id if valid and not expired."""
    db = get_db()
    record = db.execute(
        "SELECT id, user_id, expires_at, used FROM password_resets WHERE token = ? AND used = 0",
        (token,)
    ).fetchone()
    db.close()
    if not record:
        return None
    
    expires_at = datetime.fromisoformat(record["expires_at"])
    if datetime.utcnow() > expires_at:
        return None
        
    return record["user_id"]
