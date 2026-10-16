import os
import re
import secrets
import sqlite3
from datetime import date, datetime, timedelta
from functools import wraps
from pathlib import Path

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("AKCARE_DB_PATH", BASE_DIR / "appointments.db"))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("AKCARE_SECRET_KEY")
if not app.config["SECRET_KEY"]:
    # Local-development fallback only. Set a long random key before deployment.
    app.config["SECRET_KEY"] = secrets.token_urlsafe(48)
    print("WARNING: Temporary SECRET_KEY generated. Set AKCARE_SECRET_KEY for stable sessions.")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("AKCARE_HTTPS", "0") == "1"
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024

csrf = CSRFProtect(app)

DEPARTMENTS = [
    "Cardiology", "ED/Casualty", "ICU/Critical Care", "Pediatrics",
    "Obstetrics & Gynecology", "Radiology", "Pathology / Laboratory",
    "Physiotherapy", "General Medicine"
]

def connect_db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connect_db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                department TEXT NOT NULL,
                appointment_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending',
                created_at TEXT NOT NULL
            )
        """)
        con.execute("CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments(appointment_date)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments(status)")

def admin_credentials():
    username = os.environ.get("AKCARE_ADMIN_USER", "").strip()
    password_hash = os.environ.get("AKCARE_ADMIN_PASSWORD_HASH", "").strip()
    raw_password = os.environ.get("AKCARE_ADMIN_PASSWORD", "")
    if not username or (not password_hash and not raw_password):
        return None, None
    if not password_hash and raw_password:
        password_hash = generate_password_hash(raw_password)
    return username, password_hash

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login", next=request.path))
        return fn(*args, **kwargs)
    return wrapper

@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cache-Control"] = "no-store"
    return response

@app.route("/")
def home():
    return render_template("index.html", departments=DEPARTMENTS, today=date.today().isoformat())

@app.route("/book", methods=["POST"])
def book():
    name = " ".join(request.form.get("patient_name", "").split())
    phone = request.form.get("phone", "").strip()
    department = request.form.get("department", "").strip()
    appt_date = request.form.get("appointment_date", "").strip()

    if not name or len(name) > 100:
        flash("कृपया मरीज का सही नाम भरें (अधिकतम 100 अक्षर)।", "error")
        return redirect(url_for("home") + "#appointment")
    if not re.fullmatch(r"[0-9]{10}", phone):
        flash("कृपया 10 अंकों का मोबाइल नंबर भरें।", "error")
        return redirect(url_for("home") + "#appointment")
    if department not in DEPARTMENTS:
        flash("कृपया सही विभाग चुनें।", "error")
        return redirect(url_for("home") + "#appointment")
    try:
        parsed = date.fromisoformat(appt_date)
    except ValueError:
        parsed = None
    if not parsed or parsed < date.today() or parsed > date.today() + timedelta(days=180):
        flash("कृपया आज से अगले 180 दिनों के भीतर की तारीख चुनें।", "error")
        return redirect(url_for("home") + "#appointment")

    with connect_db() as con:
        cur = con.execute(
            """INSERT INTO appointments
               (patient_name, phone, department, appointment_date, status, created_at)
               VALUES (?, ?, ?, ?, 'Pending', ?)""",
            (name, phone, department, parsed.isoformat(), datetime.utcnow().isoformat(timespec="seconds") + "Z")
        )
        booking_id = cur.lastrowid
    return render_template("booking_success.html", booking_id=booking_id, patient_name=name,
                           department=department, appointment_date=parsed.isoformat())

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        expected_user, expected_hash = admin_credentials()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not expected_user:
            flash("Admin login configured नहीं है। README में setup steps देखें।", "error")
        elif secrets.compare_digest(username, expected_user) and check_password_hash(expected_hash, password):
            session.clear()
            session["admin_logged_in"] = True
            session["admin_user"] = expected_user
            session.permanent = True
            app.permanent_session_lifetime = timedelta(minutes=30)
            return redirect(url_for("admin_dashboard"))
        else:
            flash("यूज़रनेम या पासवर्ड सही नहीं है।", "error")
    return render_template("admin_login.html")

@app.route("/admin/logout", methods=["POST"])
@login_required
def admin_logout():
    session.clear()
    flash("आप सुरक्षित रूप से लॉग आउट हो गए हैं।", "success")
    return redirect(url_for("admin_login"))

@app.route("/admin")
@login_required
def admin_dashboard():
    status = request.args.get("status", "").strip()
    allowed_statuses = {"Pending", "Confirmed", "Cancelled", "Completed"}
    with connect_db() as con:
        if status in allowed_statuses:
            rows = con.execute(
                "SELECT * FROM appointments WHERE status = ? ORDER BY appointment_date ASC, id DESC LIMIT 500",
                (status,)
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT * FROM appointments ORDER BY appointment_date ASC, id DESC LIMIT 500"
            ).fetchall()
        total = con.execute("SELECT COUNT(*) FROM appointments").fetchone()[0]
        pending = con.execute("SELECT COUNT(*) FROM appointments WHERE status='Pending'").fetchone()[0]
    return render_template("admin_dashboard.html", appointments=rows, total=total, pending=pending,
                           selected_status=status, statuses=sorted(allowed_statuses))

@app.route("/admin/appointment/<int:appointment_id>/status", methods=["POST"])
@login_required
def update_status(appointment_id):
    new_status = request.form.get("status", "")
    if new_status not in {"Pending", "Confirmed", "Cancelled", "Completed"}:
        abort(400)
    with connect_db() as con:
        cur = con.execute("UPDATE appointments SET status=? WHERE id=?", (new_status, appointment_id))
        if cur.rowcount == 0:
            abort(404)
    flash(f"Appointment #{appointment_id} का status अपडेट हो गया।", "success")
    return redirect(url_for("admin_dashboard"))

@app.errorhandler(413)
def too_large(_error):
    return "Request too large.", 413

init_db()

if __name__ == "__main__":
    # Development server only; use a production WSGI server for deployment.
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=False)
