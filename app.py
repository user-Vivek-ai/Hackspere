import os
import re
import uuid
import tempfile
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, send_file, abort, jsonify
)
from werkzeug.utils import secure_filename
from database import get_db, init_db
from auth import (
    hash_password, verify_password, validate_signup_inputs,
    get_current_user, login_required, role_required,
    generate_reset_token, verify_reset_token
)
from certificates import generate_certificate_code, generate_certificate_pdf, CERT_DIR

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "hacksphere-super-secure-production-key-2026")

IS_VERCEL = os.environ.get("VERCEL") == "1" or "VERCEL" in os.environ

if IS_VERCEL:
    UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), "uploads")
else:
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CERT_DIR, exist_ok=True)

# Auto-initialize and seed database on startup / serverless cold-start
def ensure_database_ready():
    try:
        init_db()
        db = get_db()
        user_count = db.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
        db.close()
        if user_count == 0:
            from seed import seed_database
            seed_database()
    except Exception as e:
        print("Database auto-prep warning:", e)

ensure_database_ready()

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "pdf", "zip"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def is_valid_url(url):
    if not url:
        return False
    return url.startswith("http://") or url.startswith("https://")

# Context Processor for Templates
@app.context_processor
def inject_global_data():
    current_user = get_current_user()
    return {
        "current_user": current_user,
        "now": datetime.now()
    }

# ==========================================
# AUTHENTICATION ROUTES
# ==========================================

@app.route("/auth/signup", methods=["GET", "POST"])
def auth_signup():
    if "user_id" in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        role = request.form.get("role", "participant").strip().lower()

        # Validation
        is_valid, error_msg = validate_signup_inputs(name, email, password, role)
        if not is_valid:
            flash(error_msg, "danger")
            return render_template("auth/signup.html", name=name, email=email, role=role)

        if password != confirm_password:
            flash("Passwords do not match. Please re-enter.", "danger")
            return render_template("auth/signup.html", name=name, email=email, role=role)

        db = get_db()
        existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            db.close()
            flash("An account with this email address already exists. Please log in.", "warning")
            return render_template("auth/signup.html", name=name, email=email, role=role)

        hashed = hash_password(password)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO users (name, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)",
            (name, email, hashed, role, now_str)
        )
        db.commit()
        new_user_id = cursor.lastrowid
        db.close()

        # Log user in
        session["user_id"] = new_user_id
        session["user_name"] = name
        session["user_email"] = email
        session["user_role"] = role

        flash(f"Welcome to HackSphere, {name}! Your {role.capitalize()} account has been created.", "success")
        if role == "organizer":
            return redirect(url_for("organizer_dashboard"))
        return redirect(url_for("participant_dashboard"))

    return render_template("auth/signup.html")

@app.route("/auth/login", methods=["GET", "POST"])
def auth_login():
    if "user_id" in session:
        return redirect(url_for("index"))

    next_url = request.args.get("next") or request.form.get("next") or url_for("index")

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter both email and password.", "danger")
            return render_template("auth/login.html", email=email, next_url=next_url)

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        db.close()

        if not user or not verify_password(user["password_hash"], password):
            flash("Invalid email or password. Please try again.", "danger")
            return render_template("auth/login.html", email=email, next_url=next_url)

        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["user_email"] = user["email"]
        session["user_role"] = user["role"]

        flash(f"Welcome back, {user['name']}!", "success")
        if next_url and not next_url.startswith("/auth"):
            return redirect(next_url)
        if user["role"] == "organizer":
            return redirect(url_for("organizer_dashboard"))
        return redirect(url_for("participant_dashboard"))

    return render_template("auth/login.html", next_url=next_url)

@app.route("/auth/logout")
def auth_logout():
    session.clear()
    flash("You have been safely logged out.", "info")
    return redirect(url_for("index"))

@app.route("/auth/forgot-password", methods=["GET", "POST"])
def auth_forgot_password():
    reset_link = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        db = get_db()
        user = db.execute("SELECT id, name FROM users WHERE email = ?", (email,)).fetchone()
        if user:
            token = generate_reset_token(user["id"])
            # Generate absolute reset URL
            reset_link = url_for("auth_reset_password", token=token, _external=True)
            flash(
                f"Password reset instructions generated! For local development/testing without SMTP, you can use the direct reset link below.",
                "info"
            )
        else:
            flash("If an account exists for that email, a password reset link has been created.", "info")
        db.close()
    return render_template("auth/forgot.html", reset_link=reset_link)

@app.route("/auth/reset-password/<token>", methods=["GET", "POST"])
def auth_reset_password(token):
    user_id = verify_reset_token(token)
    if not user_id:
        flash("Invalid or expired password reset link. Please request a new one.", "danger")
        return redirect(url_for("auth_forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if len(password) < 8 or not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
            flash("Password must be at least 8 characters and contain both letters and numbers.", "danger")
            return render_template("auth/reset.html", token=token)

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("auth/reset.html", token=token)

        hashed = hash_password(password)
        db = get_db()
        db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hashed, user_id))
        db.execute("UPDATE password_resets SET used = 1 WHERE token = ?", (token,))
        db.commit()
        db.close()

        flash("Your password has been reset successfully! Please log in with your new password.", "success")
        return redirect(url_for("auth_login"))

    return render_template("auth/reset.html", token=token)

# ==========================================
# PUBLIC / DISCOVERY ROUTES
# ==========================================

@app.route("/")
def index():
    db = get_db()
    # Featured / ongoing hackathons
    featured = db.execute("""
        SELECT h.*, u.name as organizer_name,
               (SELECT COUNT(*) FROM registrations WHERE hackathon_id = h.id) as participant_count
        FROM hackathons h
        JOIN users u ON h.organizer_id = u.id
        WHERE h.status IN ('ongoing', 'upcoming')
        ORDER BY h.status DESC, h.start_date ASC
        LIMIT 6;
    """).fetchall()

    # Metrics
    stats = {
        "hackathons": db.execute("SELECT COUNT(*) as count FROM hackathons;").fetchone()["count"],
        "participants": db.execute("SELECT COUNT(*) as count FROM users WHERE role = 'participant';").fetchone()["count"],
        "submissions": db.execute("SELECT COUNT(*) as count FROM submissions;").fetchone()["count"],
        "certificates": db.execute("SELECT COUNT(*) as count FROM certificates;").fetchone()["count"],
    }
    db.close()
    return render_template("index.html", featured_hackathons=featured, stats=stats)

@app.route("/hackathons")
def hackathons_list():
    query = request.args.get("q", "").strip()
    format_filter = request.args.get("format", "").strip()
    theme_filter = request.args.get("theme", "").strip()
    status_filter = request.args.get("status", "").strip()
    sort_by = request.args.get("sort", "date_asc")

    sql = """
        SELECT h.*, u.name as organizer_name,
               (SELECT COUNT(*) FROM registrations WHERE hackathon_id = h.id) as participant_count
        FROM hackathons h
        JOIN users u ON h.organizer_id = u.id
        WHERE 1=1
    """
    params = []

    if query:
        sql += " AND (h.title LIKE ? OR h.description LIKE ? OR h.theme LIKE ? OR h.location LIKE ?)"
        wildcard = f"%{query}%"
        params.extend([wildcard, wildcard, wildcard, wildcard])

    if format_filter and format_filter != "all":
        sql += " AND h.format = ?"
        params.append(format_filter)

    if theme_filter and theme_filter != "all":
        sql += " AND h.theme LIKE ?"
        params.append(f"%{theme_filter}%")

    if status_filter and status_filter != "all":
        sql += " AND h.status = ?"
        params.append(status_filter)

    if sort_by == "date_desc":
        sql += " ORDER BY h.start_date DESC"
    elif sort_by == "deadline":
        sql += " ORDER BY h.submission_deadline ASC"
    else:
        sql += " ORDER BY h.start_date ASC"

    db = get_db()
    hackathons = db.execute(sql, params).fetchall()

    # Get unique themes for filter dropdown
    themes_rows = db.execute("SELECT DISTINCT theme FROM hackathons WHERE theme IS NOT NULL;").fetchall()
    all_themes = sorted(list({t["theme"].strip() for t in themes_rows if t["theme"]}))
    db.close()

    return render_template(
        "hackathons/list.html",
        hackathons=hackathons,
        search_query=query,
        format_filter=format_filter,
        theme_filter=theme_filter,
        status_filter=status_filter,
        sort_by=sort_by,
        all_themes=all_themes
    )

@app.route("/hackathons/<int:hackathon_id>")
def hackathon_detail(hackathon_id):
    db = get_db()
    hackathon = db.execute("""
        SELECT h.*, u.name as organizer_name, u.email as organizer_email, u.bio as organizer_bio
        FROM hackathons h
        JOIN users u ON h.organizer_id = u.id
        WHERE h.id = ?
    """, (hackathon_id,)).fetchone()

    if not hackathon:
        db.close()
        abort(404)

    # Participant count
    participant_count = db.execute(
        "SELECT COUNT(*) as count FROM registrations WHERE hackathon_id = ?",
        (hackathon_id,)
    ).fetchone()["count"]

    # Submission count
    submission_count = db.execute(
        "SELECT COUNT(*) as count FROM submissions WHERE hackathon_id = ?",
        (hackathon_id,)
    ).fetchone()["count"]

    # User-specific registration and submission status
    user_id = session.get("user_id")
    is_registered = False
    user_submission = None
    user_certificate = None

    if user_id:
        reg = db.execute(
            "SELECT id, status FROM registrations WHERE hackathon_id = ? AND user_id = ?",
            (hackathon_id, user_id)
        ).fetchone()
        is_registered = bool(reg)

        user_submission = db.execute(
            "SELECT * FROM submissions WHERE hackathon_id = ? AND user_id = ?",
            (hackathon_id, user_id)
        ).fetchone()

        if user_submission and user_submission["status"] == "accepted":
            user_certificate = db.execute(
                "SELECT * FROM certificates WHERE hackathon_id = ? AND user_id = ?",
                (hackathon_id, user_id)
            ).fetchone()

    db.close()
    return render_template(
        "hackathons/detail.html",
        hackathon=hackathon,
        participant_count=participant_count,
        submission_count=submission_count,
        is_registered=is_registered,
        user_submission=user_submission,
        user_certificate=user_certificate
    )

# ==========================================
# PARTICIPANT ACTIONS
# ==========================================

@app.route("/hackathons/<int:hackathon_id>/register", methods=["POST"])
@login_required
@role_required("participant")
def register_hackathon(hackathon_id):
    user_id = session["user_id"]
    db = get_db()
    hackathon = db.execute("SELECT * FROM hackathons WHERE id = ?", (hackathon_id,)).fetchone()
    if not hackathon:
        db.close()
        abort(404)

    # Check registration deadline
    today = datetime.now().strftime("%Y-%m-%d")
    if hackathon["registration_deadline"] < today:
        db.close()
        flash("Registration for this hackathon has closed.", "danger")
        return redirect(url_for("hackathon_detail", hackathon_id=hackathon_id))

    # Check existing registration
    existing = db.execute(
        "SELECT id FROM registrations WHERE hackathon_id = ? AND user_id = ?",
        (hackathon_id, user_id)
    ).fetchone()

    if existing:
        db.close()
        flash("You are already registered for this hackathon!", "info")
        return redirect(url_for("hackathon_detail", hackathon_id=hackathon_id))

    user = db.execute("SELECT name, email FROM users WHERE id = ?", (user_id,)).fetchone()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    db.execute("""
        INSERT INTO registrations (hackathon_id, user_id, user_email, user_name, status, registered_at)
        VALUES (?, ?, ?, ?, 'registered', ?)
    """, (hackathon_id, user_id, user["email"], user["name"], now_str))
    db.commit()
    db.close()

    flash(f"Successfully registered for {hackathon['title']}! We can't wait to see what you build.", "success")
    return redirect(url_for("hackathon_detail", hackathon_id=hackathon_id))

@app.route("/hackathons/<int:hackathon_id>/submit", methods=["GET", "POST"])
@login_required
@role_required("participant")
def submit_project(hackathon_id):
    user_id = session["user_id"]
    db = get_db()
    hackathon = db.execute("SELECT * FROM hackathons WHERE id = ?", (hackathon_id,)).fetchone()
    if not hackathon:
        db.close()
        abort(404)

    # Check if participant is registered
    registration = db.execute(
        "SELECT id FROM registrations WHERE hackathon_id = ? AND user_id = ?",
        (hackathon_id, user_id)
    ).fetchone()

    if not registration:
        db.close()
        flash("You must register for this hackathon before submitting a project.", "warning")
        return redirect(url_for("hackathon_detail", hackathon_id=hackathon_id))

    # Check submission deadline
    today = datetime.now().strftime("%Y-%m-%d")
    if hackathon["submission_deadline"] < today and hackathon["status"] == "ended":
        db.close()
        flash("The project submission deadline has passed.", "danger")
        return redirect(url_for("hackathon_detail", hackathon_id=hackathon_id))

    existing_submission = db.execute(
        "SELECT * FROM submissions WHERE hackathon_id = ? AND user_id = ?",
        (hackathon_id, user_id)
    ).fetchone()

    if request.method == "POST":
        project_name = request.form.get("project_name", "").strip()
        description = request.form.get("description", "").strip()
        team_members = request.form.get("team_members", "").strip()
        demo_url = request.form.get("demo_url", "").strip()
        repo_url = request.form.get("repo_url", "").strip()

        # Validation
        if not project_name:
            flash("Please provide a project name.", "danger")
            return render_template("participant/submit.html", hackathon=hackathon, submission=existing_submission)

        if not description or len(description) < 20:
            flash("Please provide a meaningful project description (at least 20 characters).", "danger")
            return render_template("participant/submit.html", hackathon=hackathon, submission=existing_submission)

        if not demo_url or not is_valid_url(demo_url):
            flash("Please provide a valid project or demo URL starting with http:// or https://", "danger")
            return render_template("participant/submit.html", hackathon=hackathon, submission=existing_submission)

        if repo_url and not is_valid_url(repo_url):
            flash("Repository URL must start with http:// or https://", "danger")
            return render_template("participant/submit.html", hackathon=hackathon, submission=existing_submission)

        # File upload handling (optional image or document)
        image_url = existing_submission["image_url"] if existing_submission else None
        file_path = existing_submission["file_path"] if existing_submission else None

        if "project_file" in request.files:
            file = request.files["project_file"]
            if file and file.filename != "":
                if allowed_file(file.filename):
                    ext = file.filename.rsplit(".", 1)[1].lower()
                    unique_filename = f"{uuid.uuid4().hex}.{ext}"
                    save_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
                    file.save(save_path)
                    
                    if ext in {"png", "jpg", "jpeg", "gif", "webp"}:
                        image_url = url_for("static", filename=f"uploads/{unique_filename}")
                    else:
                        file_path = save_path
                else:
                    flash("File type not allowed. Please upload an image (PNG, JPG, WEBP) or PDF/ZIP.", "danger")
                    return render_template("participant/submit.html", hackathon=hackathon, submission=existing_submission)

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if existing_submission:
            db.execute("""
                UPDATE submissions
                SET project_name = ?, description = ?, team_members = ?,
                    demo_url = ?, repo_url = ?, image_url = ?, file_path = ?,
                    status = 'pending', submitted_at = ?
                WHERE id = ?
            """, (project_name, description, team_members, demo_url, repo_url, image_url, file_path, now_str, existing_submission["id"]))
            flash("Your project submission has been updated and is pending organizer review!", "success")
        else:
            db.execute("""
                INSERT INTO submissions (
                    hackathon_id, user_id, project_name, description, team_members,
                    demo_url, repo_url, image_url, file_path, status, submitted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
            """, (hackathon_id, user_id, project_name, description, team_members, demo_url, repo_url, image_url, file_path, now_str))
            flash("Project submitted successfully! The organizer will review your project shortly.", "success")

        db.commit()
        db.close()
        return redirect(url_for("participant_dashboard"))

    db.close()
    return render_template("participant/submit.html", hackathon=hackathon, submission=existing_submission)

@app.route("/dashboard")
@login_required
def participant_dashboard():
    if session.get("user_role") == "organizer":
        return redirect(url_for("organizer_dashboard"))

    user_id = session["user_id"]
    db = get_db()

    # Registrations
    registrations = db.execute("""
        SELECT r.*, h.title as hackathon_title, h.start_date, h.end_date, h.format,
               h.submission_deadline, h.status as hackathon_status,
               s.id as submission_id, s.status as submission_status, s.project_name
        FROM registrations r
        JOIN hackathons h ON r.hackathon_id = h.id
        LEFT JOIN submissions s ON s.hackathon_id = h.id AND s.user_id = r.user_id
        WHERE r.user_id = ?
        ORDER BY r.registered_at DESC
    """, (user_id,)).fetchall()

    # Submissions
    submissions = db.execute("""
        SELECT s.*, h.title as hackathon_title, h.start_date, h.end_date,
               u.name as organizer_name, c.certificate_code
        FROM submissions s
        JOIN hackathons h ON s.hackathon_id = h.id
        JOIN users u ON h.organizer_id = u.id
        LEFT JOIN certificates c ON c.submission_id = s.id
        WHERE s.user_id = ?
        ORDER BY s.submitted_at DESC
    """, (user_id,)).fetchall()

    # Certificates
    certificates = db.execute("""
        SELECT c.*, s.project_name
        FROM certificates c
        JOIN submissions s ON c.submission_id = s.id
        WHERE c.user_id = ?
        ORDER BY c.issued_at DESC
    """, (user_id,)).fetchall()

    db.close()
    return render_template(
        "participant/dashboard.html",
        registrations=registrations,
        submissions=submissions,
        certificates=certificates
    )

# ==========================================
# CERTIFICATES DOWNLOAD & VERIFICATION
# ==========================================

@app.route("/certificates/<certificate_code>/download")
@login_required
def download_certificate(certificate_code):
    user_id = session["user_id"]
    user_role = session.get("user_role")

    db = get_db()
    cert = db.execute("""
        SELECT c.*, s.status as submission_status, h.organizer_id
        FROM certificates c
        JOIN submissions s ON c.submission_id = s.id
        JOIN hackathons h ON c.hackathon_id = h.id
        WHERE c.certificate_code = ?
    """, (certificate_code,)).fetchone()

    if not cert:
        db.close()
        abort(404)

    # STRICT ENFORCEMENT: Certificate is only available if project was accepted!
    if cert["submission_status"] != "accepted":
        db.close()
        flash("Participation certificates are only available after an organizer reviews and accepts the project.", "danger")
        return redirect(url_for("participant_dashboard"))

    # Permission check: Only the participant or the hackathon organizer can download
    if cert["user_id"] != user_id and cert["organizer_id"] != user_id and user_role != "admin":
        db.close()
        flash("You are not authorized to download this certificate.", "danger")
        return redirect(url_for("index"))

    # Generate PDF if not yet cached on disk
    pdf_path = cert["pdf_path"]
    if not pdf_path or not os.path.exists(pdf_path):
        filename = f"{cert['certificate_code']}.pdf"
        pdf_path = os.path.join(CERT_DIR, filename)
        
        # Look up project name
        sub = db.execute("SELECT project_name FROM submissions WHERE id = ?", (cert["submission_id"],)).fetchone()
        project_name = sub["project_name"] if sub else None

        generate_certificate_pdf(
            certificate_code=cert["certificate_code"],
            participant_name=cert["participant_name"],
            hackathon_title=cert["hackathon_title"],
            event_dates=cert["event_dates"],
            organizer_name=cert["organizer_name"],
            project_name=project_name,
            output_path=pdf_path
        )
        # Update path
        db.execute("UPDATE certificates SET pdf_path = ? WHERE id = ?", (pdf_path, cert["id"]))
        db.commit()

    db.close()
    return send_file(
        pdf_path,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"Certificate_{cert['certificate_code']}.pdf"
    )

@app.route("/verify-certificate/<certificate_code>")
def verify_certificate(certificate_code):
    db = get_db()
    cert = db.execute("""
        SELECT c.*, s.project_name, s.status as submission_status, h.theme, h.format, h.location
        FROM certificates c
        JOIN submissions s ON c.submission_id = s.id
        JOIN hackathons h ON c.hackathon_id = h.id
        WHERE c.certificate_code = ?
    """, (certificate_code,)).fetchone()
    db.close()

    return render_template("verify_certificate.html", cert=cert, certificate_code=certificate_code)

# ==========================================
# ORGANIZER ROUTES
# ==========================================

@app.route("/organizer/dashboard")
@login_required
@role_required("organizer")
def organizer_dashboard():
    organizer_id = session["user_id"]
    db = get_db()

    # Hosted hackathons
    hackathons = db.execute("""
        SELECT h.*,
               (SELECT COUNT(*) FROM registrations WHERE hackathon_id = h.id) as reg_count,
               (SELECT COUNT(*) FROM submissions WHERE hackathon_id = h.id) as sub_count,
               (SELECT COUNT(*) FROM submissions WHERE hackathon_id = h.id AND status = 'pending') as pending_count,
               (SELECT COUNT(*) FROM submissions WHERE hackathon_id = h.id AND status = 'accepted') as accepted_count
        FROM hackathons h
        WHERE h.organizer_id = ?
        ORDER BY h.created_at DESC
    """, (organizer_id,)).fetchall()

    # Aggregate stats
    stats = {
        "total_hackathons": len(hackathons),
        "total_registrations": sum(h["reg_count"] for h in hackathons),
        "total_submissions": sum(h["sub_count"] for h in hackathons),
        "pending_reviews": sum(h["pending_count"] for h in hackathons),
        "total_certificates": sum(h["accepted_count"] for h in hackathons),
    }

    db.close()
    return render_template("organizer/dashboard.html", hackathons=hackathons, stats=stats)

@app.route("/hackathons/create", methods=["GET", "POST"])
@login_required
@role_required("organizer")
def hackathon_create():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        tagline = request.form.get("tagline", "").strip()
        description = request.form.get("description", "").strip()
        theme = request.form.get("theme", "").strip()
        format_val = request.form.get("format", "online").strip()
        location = request.form.get("location", "").strip()
        start_date = request.form.get("start_date", "").strip()
        end_date = request.form.get("end_date", "").strip()
        reg_deadline = request.form.get("registration_deadline", "").strip()
        sub_deadline = request.form.get("submission_deadline", "").strip()
        team_size_min = int(request.form.get("team_size_min", 1))
        team_size_max = int(request.form.get("team_size_max", 4))
        eligibility = request.form.get("eligibility", "").strip()
        rules = request.form.get("rules", "").strip()
        schedule = request.form.get("schedule", "").strip()
        judging_criteria = request.form.get("judging_criteria", "").strip()
        prizes = request.form.get("prizes", "").strip()
        banner_url = request.form.get("banner_url", "").strip()
        status_val = request.form.get("status", "upcoming").strip()

        # Validation
        if not title or len(title) < 5:
            flash("Please provide a descriptive title (at least 5 characters).", "danger")
            return render_template("hackathons/create.html", form=request.form)

        if not description or len(description) < 30:
            flash("Please provide a thorough description of the hackathon.", "danger")
            return render_template("hackathons/create.html", form=request.form)

        if not start_date or not end_date:
            flash("Please specify valid start and end dates.", "danger")
            return render_template("hackathons/create.html", form=request.form)

        if not reg_deadline:
            reg_deadline = start_date
        if not sub_deadline:
            sub_deadline = end_date

        if not banner_url:
            banner_url = "https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?w=1200&auto=format&fit=crop&q=80"

        organizer_id = session["user_id"]
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO hackathons (
                organizer_id, title, tagline, description, theme, format, location,
                start_date, end_date, registration_deadline, submission_deadline,
                team_size_min, team_size_max, eligibility, rules, schedule,
                judging_criteria, prizes, banner_url, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            organizer_id, title, tagline, description, theme, format_val, location,
            start_date, end_date, reg_deadline, sub_deadline,
            team_size_min, team_size_max, eligibility, rules, schedule,
            judging_criteria, prizes, banner_url, status_val, now_str, now_str
        ))
        db.commit()
        new_id = cursor.lastrowid
        db.close()

        flash(f"Hackathon '{title}' created successfully!", "success")
        return redirect(url_for("organizer_manage_hackathon", hackathon_id=new_id))

    return render_template("hackathons/create.html")

@app.route("/hackathons/<int:hackathon_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("organizer")
def hackathon_edit(hackathon_id):
    organizer_id = session["user_id"]
    db = get_db()
    hackathon = db.execute("SELECT * FROM hackathons WHERE id = ?", (hackathon_id,)).fetchone()
    if not hackathon:
        db.close()
        abort(404)

    if hackathon["organizer_id"] != organizer_id:
        db.close()
        flash("You are not authorized to edit this hackathon.", "danger")
        return redirect(url_for("organizer_dashboard"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        tagline = request.form.get("tagline", "").strip()
        description = request.form.get("description", "").strip()
        theme = request.form.get("theme", "").strip()
        format_val = request.form.get("format", "online").strip()
        location = request.form.get("location", "").strip()
        start_date = request.form.get("start_date", "").strip()
        end_date = request.form.get("end_date", "").strip()
        reg_deadline = request.form.get("registration_deadline", "").strip()
        sub_deadline = request.form.get("submission_deadline", "").strip()
        team_size_min = int(request.form.get("team_size_min", 1))
        team_size_max = int(request.form.get("team_size_max", 4))
        eligibility = request.form.get("eligibility", "").strip()
        rules = request.form.get("rules", "").strip()
        schedule = request.form.get("schedule", "").strip()
        judging_criteria = request.form.get("judging_criteria", "").strip()
        prizes = request.form.get("prizes", "").strip()
        banner_url = request.form.get("banner_url", "").strip()
        status_val = request.form.get("status", "upcoming").strip()

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        db.execute("""
            UPDATE hackathons
            SET title = ?, tagline = ?, description = ?, theme = ?, format = ?, location = ?,
                start_date = ?, end_date = ?, registration_deadline = ?, submission_deadline = ?,
                team_size_min = ?, team_size_max = ?, eligibility = ?, rules = ?, schedule = ?,
                judging_criteria = ?, prizes = ?, banner_url = ?, status = ?, updated_at = ?
            WHERE id = ?
        """, (
            title, tagline, description, theme, format_val, location,
            start_date, end_date, reg_deadline, sub_deadline,
            team_size_min, team_size_max, eligibility, rules, schedule,
            judging_criteria, prizes, banner_url, status_val, now_str, hackathon_id
        ))
        db.commit()
        db.close()

        flash("Hackathon details updated successfully!", "success")
        return redirect(url_for("organizer_manage_hackathon", hackathon_id=hackathon_id))

    db.close()
    return render_template("hackathons/edit.html", hackathon=hackathon)

@app.route("/organizer/hackathons/<int:hackathon_id>/manage")
@login_required
@role_required("organizer")
def organizer_manage_hackathon(hackathon_id):
    organizer_id = session["user_id"]
    db = get_db()
    hackathon = db.execute("SELECT * FROM hackathons WHERE id = ?", (hackathon_id,)).fetchone()
    if not hackathon:
        db.close()
        abort(404)

    if hackathon["organizer_id"] != organizer_id:
        db.close()
        flash("You are not authorized to manage this hackathon.", "danger")
        return redirect(url_for("organizer_dashboard"))

    # Registered participants
    participants = db.execute("""
        SELECT r.*, s.id as submission_id, s.status as submission_status, s.project_name
        FROM registrations r
        LEFT JOIN submissions s ON s.hackathon_id = r.hackathon_id AND s.user_id = r.user_id
        WHERE r.hackathon_id = ?
        ORDER BY r.registered_at DESC
    """, (hackathon_id,)).fetchall()

    # Project submissions
    submissions = db.execute("""
        SELECT s.*, u.name as submitter_name, u.email as submitter_email,
               c.certificate_code, c.id as certificate_id
        FROM submissions s
        JOIN users u ON s.user_id = u.id
        LEFT JOIN certificates c ON c.submission_id = s.id
        WHERE s.hackathon_id = ?
        ORDER BY s.submitted_at DESC
    """, (hackathon_id,)).fetchall()

    # Certificates issued
    certificates = db.execute("""
        SELECT c.*, s.project_name, u.email as participant_email
        FROM certificates c
        JOIN users u ON c.user_id = u.id
        JOIN submissions s ON c.submission_id = s.id
        WHERE c.hackathon_id = ?
        ORDER BY c.issued_at DESC
    """, (hackathon_id,)).fetchall()

    db.close()
    return render_template(
        "organizer/manage.html",
        hackathon=hackathon,
        participants=participants,
        submissions=submissions,
        certificates=certificates
    )

@app.route("/api/submissions/<int:submission_id>/review", methods=["POST"])
@login_required
@role_required("organizer")
def review_submission(submission_id):
    organizer_id = session["user_id"]
    decision = request.form.get("decision", "").strip().lower()  # 'accepted' or 'rejected'
    feedback = request.form.get("feedback", "").strip()

    if decision not in ("accepted", "rejected"):
        flash("Invalid decision value. Must be 'accepted' or 'rejected'.", "danger")
        return redirect(request.referrer or url_for("organizer_dashboard"))

    db = get_db()
    sub = db.execute("""
        SELECT s.*, h.organizer_id, h.title as hackathon_title, h.start_date, h.end_date,
               u.name as participant_name, u.email as participant_email,
               org.name as organizer_name
        FROM submissions s
        JOIN hackathons h ON s.hackathon_id = h.id
        JOIN users u ON s.user_id = u.id
        JOIN users org ON h.organizer_id = org.id
        WHERE s.id = ?
    """, (submission_id,)).fetchone()

    if not sub:
        db.close()
        abort(404)

    if sub["organizer_id"] != organizer_id:
        db.close()
        flash("You are not authorized to review submissions for this hackathon.", "danger")
        return redirect(url_for("organizer_dashboard"))

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Update submission decision & feedback
    db.execute("""
        UPDATE submissions
        SET status = ?, feedback = ?, reviewed_at = ?
        WHERE id = ?
    """, (decision, feedback, now_str, submission_id))

    # CERTIFICATE GENERATION UPON ACCEPTANCE
    if decision == "accepted":
        existing_cert = db.execute(
            "SELECT * FROM certificates WHERE hackathon_id = ? AND user_id = ?",
            (sub["hackathon_id"], sub["user_id"])
        ).fetchone()

        if not existing_cert:
            cert_code = generate_certificate_code()
            pdf_filename = f"{cert_code}.pdf"
            pdf_path = os.path.join(CERT_DIR, pdf_filename)
            event_dates = f"{sub['start_date']} to {sub['end_date']}"

            # Generate real PDF certificate
            generate_certificate_pdf(
                certificate_code=cert_code,
                participant_name=sub["participant_name"],
                hackathon_title=sub["hackathon_title"],
                event_dates=event_dates,
                organizer_name=sub["organizer_name"],
                project_name=sub["project_name"],
                output_path=pdf_path
            )

            db.execute("""
                INSERT INTO certificates (
                    certificate_code, hackathon_id, user_id, submission_id,
                    participant_name, hackathon_title, event_dates, organizer_name,
                    issued_at, pdf_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cert_code, sub["hackathon_id"], sub["user_id"], submission_id,
                sub["participant_name"], sub["hackathon_title"], event_dates,
                sub["organizer_name"], now_str, pdf_path
            ))
            flash(
                f"Project '{sub['project_name']}' by {sub['participant_name']} was ACCEPTED! Participation Certificate {cert_code} has been generated.",
                "success"
            )
        else:
            flash(f"Project '{sub['project_name']}' marked as accepted.", "success")

    elif decision == "rejected":
        # If previously accepted, remove issued certificate
        db.execute("DELETE FROM certificates WHERE submission_id = ?", (submission_id,))
        flash(f"Project '{sub['project_name']}' was rejected with your feedback.", "warning")

    db.commit()
    db.close()

    return redirect(url_for("organizer_manage_hackathon", hackathon_id=sub["hackathon_id"]))

# Error Handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(403)
def forbidden_access(e):
    flash("You do not have permission to access that resource.", "danger")
    return redirect(url_for("index"))

if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=True)
