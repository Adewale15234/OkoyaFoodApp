from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, date
from calendar import monthrange
from sqlalchemy import extract, create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy import func
from io import BytesIO
from backup_manager import create_backup
import os
import logging
import psycopg2
import uuid
import io
import traceback
import qrcode
import base64
import json
import threading
import time

from dotenv import load_dotenv
load_dotenv()

from functools import wraps
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message

# ------------------------------
# Allowed image extensions
# ------------------------------
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return (
        '.' in filename and
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    )

# ==============================
# HELPER FUNCTION (ADD HERE)
# ==============================

import time
from flask import url_for

def get_passport_url(worker):
    if worker.passport:
        return url_for('static', filename=f'uploads/{worker.passport}') + f"?v={int(time.time())}"
    return url_for('static', filename='default.png')
# ------------------------------
# Login decorator (FINAL CLEAN VERSION)
# ------------------------------
def login_required(role=None):
    """
    Protect routes with login and optional role-based access.
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):

            # 1. Check login
            if 'role' not in session:
                flash("Please login first.", "warning")
                return redirect(url_for('login'))

            # 2. Check role only if required
            if role is not None and session.get('role') != role:
                flash("You are not authorized to access this page.", "danger")

                # redirect based on user role (better UX)
                if session.get('role') == 'secretary':
                    return redirect(url_for('secretary_dashboard'))
                elif session.get('role') == 'admin':
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('login'))

            return f(*args, **kwargs)

        return decorated_function

    return decorator


# ------------------------------
# Logging setup
# ------------------------------
logging.basicConfig(level=logging.INFO)

# ------------------------------
# Flask app & secret key
# ------------------------------
# ------------------------------
# Flask app & secret key
# ------------------------------
app = Flask(__name__)
app.config['PROPAGATE_EXCEPTIONS'] = True
app.config['DEBUG'] = True

app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB upload limit

app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# ==============================
# GLOBAL ERROR DEBUG (ADD HERE)
# ==============================

# Secret key
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME')

# Upload folder
app.config['UPLOAD_FOLDER'] = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Mail config (BREVO SMTP - FIXED)
# Mail config (BREVO SMTP - FIXED)
# Mail config (BREVO SMTP)
# ==============================
# BREVO SMTP CONFIG
# ==============================

# ==============================
# BREVO SMTP CONFIG
# ==============================

# ==============================
# BREVO SMTP CONFIG
# ==============================

app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))

app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_TIMEOUT'] = 60
app.config['MAIL_SUPPRESS_SEND'] = False

app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')

app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')

mail = Mail(app)

print("MAIL USER:", app.config['MAIL_USERNAME'])
print("MAIL PASSWORD EXISTS:", bool(app.config['MAIL_PASSWORD']))
print("MAIL SERVER:", app.config['MAIL_SERVER'])
print("MAIL PORT:", app.config['MAIL_PORT'])
print("MAIL TLS:", app.config['MAIL_USE_TLS'])
print("MAIL SSL:", app.config['MAIL_USE_SSL'])
# ------------------------------
# Database config
# ------------------------------
# ------------------------------
# Database config
# ------------------------------
db_url = os.environ.get("DATABASE_URL")

# Fallback to SQLite only for local development
if not db_url:
    db_url = "sqlite:///okoya.db"

# Fix Render PostgreSQL URL
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# IMPORTANT: put BEFORE SQLAlchemy(app)
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_pre_ping": True,
    "pool_recycle": 280,
    "pool_timeout": 30,
    "max_overflow": 20
}

db = SQLAlchemy(app)

@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.remove()

migrate = Migrate(app, db)



class Worker(db.Model):
    __tablename__ = 'workers'

    id = db.Column(db.Integer, primary_key=True)

    worker_code = db.Column(db.String(10), unique=True, nullable=True)

    name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    qualifications = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(100), nullable=False)
    national_id = db.Column(db.String(50), nullable=False)
    nationality = db.Column(db.String(50), nullable=False)
    home_address = db.Column(db.String(200), nullable=False)
    ethnic_group = db.Column(db.String(50), nullable=False)
    place_of_residence = db.Column(db.String(100), nullable=False)
    disability = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(100), nullable=False)
    date_of_employment = db.Column(db.Date, nullable=False)

    amount_of_salary = db.Column(db.Float, nullable=False)

    bank_name = db.Column(db.String(100), nullable=True)
    bank_account = db.Column(db.String(50), nullable=True)
    bank_account_name = db.Column(db.String(100), nullable=False)

    guarantor = db.Column(db.String(100), nullable=False)

    passport = db.Column(db.String(100), nullable=True)

    # ADD THIS
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # STATUS
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    status_type = db.Column(db.String(30), nullable=True)
    status_reason = db.Column(db.Text, nullable=True)
    status_date = db.Column(db.DateTime, nullable=True)
    status_letter = db.Column(db.Text, nullable=True)

    warning_count = db.Column(db.Integer, default=0)
    last_action_by = db.Column(db.String(100), nullable=True)
    last_action_date = db.Column(db.DateTime, nullable=True)

    notes = db.Column(db.Text, nullable=True)

    # RELATIONSHIPS
    attendance_records = db.relationship(
        'Attendance',
        backref='worker',
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    salaries = db.relationship(
        'Salary',
        backref='worker',
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    email_logs = db.relationship(
        'EmailLog',
        backref=db.backref('worker_ref', lazy=True),
        cascade="all, delete-orphan",
        passive_deletes=True
    )

class EmailLog(db.Model):
    __tablename__ = 'email_logs'

    id = db.Column(db.Integer, primary_key=True)

    worker_id = db.Column(
        db.Integer,
        db.ForeignKey('workers.id', ondelete="CASCADE"),
        nullable=False
    )

    email = db.Column(db.String(120), nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="Sent")

    # ❌ REMOVE THIS (VERY IMPORTANT)
    # worker = db.relationship('Worker', backref='email_logs')  

 # ===============================
# AI OFFENCE REVIEW FUNCTION (UPGRADED)
# ===============================
def ai_offence_review(worker, reason):

    if not reason:
        reason = "No reason provided"

    reason_lower = reason.lower()

    # Weighted severity scoring (better than simple keyword match)
    high_severity_words = ["theft", "steal", "fight", "violence", "assault", "fraud", "dismissed"]
    medium_severity_words = ["absent", "lateness", "late", "insult", "disrespect", "warning"]

    score = 0

    for word in high_severity_words:
        if word in reason_lower:
            score += 3

    for word in medium_severity_words:
        if word in reason_lower:
            score += 1

    # Determine severity level
    if score >= 3:
        severity = "HIGH"
        recommendation = "Immediate Suspension / Investigation"
    elif score == 2:
        severity = "MEDIUM"
        recommendation = "Formal Warning Required"
    else:
        severity = "LOW"
        recommendation = "Verbal Warning / Monitoring"

    # Auto escalation suggestion
    escalation = "HR Director Review Required" if severity == "HIGH" else "Supervisor Review"

    return f"""
==============================
AI OFFENCE REVIEW REPORT
==============================

Worker Name: {worker.name}
Worker Code: {worker.worker_code}
Position: {worker.position}

Reported Issue:
{reason}

------------------------------
AI ANALYSIS
------------------------------
Severity Level: {severity}
Risk Score: {score}

Recommendation: {recommendation}
Escalation Level: {escalation}

------------------------------
SUMMARY
------------------------------
This case has been automatically analyzed based on HR behavioural patterns.
Further human verification is recommended before final disciplinary action.
"""


# ===============================
# HR LETTER GENERATOR FUNCTION (UPGRADED)
# ===============================
def generate_hr_letter(worker, reason, status_type):

    name = worker.name or "Unknown"
    code = worker.worker_code or "N/A"
    position = worker.position or "N/A"
    date = datetime.utcnow().strftime('%Y-%m-%d')

    reason_text = reason if reason else "No reason provided"

    # =========================
    # DEACTIVATION LETTER
    # =========================
    if status_type in ["deactivated", "suspended"]:

        return f"""
========================================
OKOYA FOOD COMPANY LIMITED
HUMAN RESOURCES DEPARTMENT
OFFICIAL DISCIPLINARY NOTICE
========================================

Employee Name: {name}
Employee Code: {code}
Position: {position}

STATUS: {status_type.upper()}

REASON FOR ACTION:
{reason_text}

----------------------------------------
HR DECISION
----------------------------------------
Following internal review and company policy guidelines,
you have been placed under disciplinary action and
temporarily removed from active duty pending further review.

You are advised to report to the HR department for clarification.

Effective Date: {date}

----------------------------------------
NOTE:
Failure to comply may lead to permanent termination.
========================================
OKOYA FOOD HR MANAGEMENT SYSTEM
"""

    # =========================
    # REINSTATEMENT LETTER
    # =========================
    elif status_type in ["reactivated", "reinstated"]:

        return f"""
========================================
OKOYA FOOD COMPANY LIMITED
HUMAN RESOURCES DEPARTMENT
REINSTATEMENT NOTICE
========================================

Employee Name: {name}
Employee Code: {code}
Position: {position}

STATUS: REINSTATED

----------------------------------------
HR DECISION
----------------------------------------
After careful review of your case,
management has approved your return to active duty.

You are expected to resume duties immediately and
maintain proper conduct going forward.

Effective Date: {date}

----------------------------------------
HR DEPARTMENT
OKOYA FOOD COMPANY LIMITED
========================================
"""

    # =========================
    # DEFAULT SAFETY FALLBACK
    # =========================
    else:
        return f"""
OKOYA FOOD HR SYSTEM

Employee: {name}
Code: {code}

Status Update: {status_type}

No formal HR letter template matched this status.
Please verify the worker status configuration.

Date: {date}
"""

# --- Client Order Model ---
class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    name = db.Column(db.String(150))
    email = db.Column(db.String(150))
    items = db.Column(db.String(50))
    kilograms = db.Column(db.Integer, nullable=True)
    unit_price = db.Column(db.Float, nullable=True)
    total_amount = db.Column(db.Float, nullable=True)

    date_needed = db.Column(db.DateTime)

    driver_name = db.Column(db.String(100))
    vehicle_plate_number = db.Column(db.String(50))

    bank_name = db.Column(db.String(100))
    account_number = db.Column(db.String(50))
    account_bank_name = db.Column(db.String(200))

    description = db.Column(db.String(255))
    phone_number = db.Column(db.String(100))

    status = db.Column(db.String(20), default="Pending")

    # ✅ FIX ADDED (important for tracking)
    confirmed_at = db.Column(db.DateTime, nullable=True)

class Attendance(db.Model):
    __tablename__ = 'attendance'

    id = db.Column(db.Integer, primary_key=True)

    worker_id = db.Column(
        db.Integer,
        db.ForeignKey('workers.id', ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    date = db.Column(
        db.Date,
        nullable=False,
        default=db.func.current_date(),
        index=True
    )

    status = db.Column(db.String(10), nullable=False)

    created_at = db.Column(db.DateTime, server_default=db.func.now())

    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now()
    )


# =========================
# FIXED SALARY MODEL (OUTSIDE Attendance)
# =========================
class Salary(db.Model):
    __tablename__ = 'salary'

    id = db.Column(db.Integer, primary_key=True)

    worker_id = db.Column(
        db.Integer,
        db.ForeignKey('workers.id', ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    total_days_present = db.Column(db.Integer, nullable=False)
    daily_rate = db.Column(db.Float, nullable=False, default=0.0)
    amount = db.Column(db.Float, nullable=False)

    bank_name = db.Column(db.String(100), nullable=True)
    bank_account = db.Column(db.String(50), nullable=True)
    bank_account_name = db.Column(db.String(100), nullable=True)

    payment_date = db.Column(
        db.DateTime,
        nullable=False,
        default=db.func.current_timestamp(),
        index=True
    )

    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
# Hardcoded credentials (Not secure! Replace with real auth for production)
# USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
# PASSWORD = os.environ.get('ADMIN_PASSWORD', 'Alayinde001')


# Routes

@app.route('/register_worker', methods=['GET', 'POST'])
@login_required(role='admin')
def register_worker():

    if request.method == 'POST':

        try:
            # ===============================
            # 1. COLLECT & CLEAN INPUTS
            # ===============================
            name = (request.form.get('name') or "").strip()
            phone_number = (request.form.get('phone_number') or "").strip()
            gender = (request.form.get('gender') or "").strip().title()
            email = (request.form.get('email') or "").strip().lower()

            qualifications = (request.form.get('qualifications') or "").strip()
            position = (request.form.get('position') or "").strip()

            guarantor = (request.form.get('guarantor') or "").strip()
            national_id = (request.form.get('national_id') or "").strip()
            nationality = (request.form.get('nationality') or "").strip()
            ethnic_group = (request.form.get('ethnic_group') or "").strip()
            disability = (request.form.get('disability') or "").strip()

            home_address = (request.form.get('home_address') or "").strip()
            place_of_residence = (request.form.get('place_of_residence') or "").strip()

            bank_account_name = (request.form.get('bank_account_name') or "").strip()
            bank_name = (request.form.get('bank_name') or "").strip()
            bank_account = (request.form.get('bank_account') or "").strip()

            # salary safe parse
            try:
                amount_of_salary = float(request.form.get('amount_of_salary') or 0)
            except ValueError:
                amount_of_salary = 0.0

            # ===============================
            # 2. DATE VALIDATION
            # ===============================
            def safe_date(value):
                try:
                    return datetime.strptime(value, "%Y-%m-%d").date()
                except:
                    return None

            date_of_birth = safe_date(request.form.get('date_of_birth'))
            date_of_employment = safe_date(request.form.get('date_of_employment'))

            # ===============================
            # 3. BASIC VALIDATION
            # ===============================
            if not name or not phone_number or not position:
                flash("Name, Phone number and Position are required.", "danger")
                return redirect(url_for('register_worker'))

            if amount_of_salary < 0:
                flash("Salary cannot be negative.", "danger")
                return redirect(url_for('register_worker'))

            # ===============================
            # 4. DUPLICATE CHECK
            # ===============================
            existing_worker = Worker.query.filter(
                (Worker.phone_number == phone_number) |
                (Worker.email == email)
            ).first()

            if existing_worker:
                flash("Worker with this phone or email already exists.", "warning")
                return redirect(url_for('register_worker'))

            # ===============================
            # 5. NIN CHECK
            # ===============================
            if national_id:
                existing_nin = Worker.query.filter_by(national_id=national_id).first()
                if existing_nin:
                    flash("This National ID is already registered.", "warning")
                    return redirect(url_for('register_worker'))

            # ===============================
            # 6. PASSPORT UPLOAD (FIXED)
            # ===============================
            passport_filename = None
            passport_file = request.files.get('passport')

            if passport_file and passport_file.filename.strip():

                if not allowed_file(passport_file.filename):
                    flash("Only image files (jpg, jpeg, png) allowed.", "danger")
                    return redirect(url_for('register_worker'))

                # ALWAYS save inside static/uploads
                upload_folder = os.path.join(app.root_path, 'static', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)

                original_name = secure_filename(passport_file.filename)
                unique_name = f"{uuid.uuid4().hex}_{original_name}"

                save_path = os.path.join(upload_folder, unique_name)

                passport_file.save(save_path)

                passport_filename = unique_name

                print(f"[PASSPORT SAVED] {save_path}")

            # ===============================
            # 7. AUTO WORKER CODE
            # ===============================
            last_worker = Worker.query.order_by(Worker.id.desc()).first()

            if last_worker and last_worker.worker_code:
                try:
                    last_number = int(last_worker.worker_code.replace("OFCL", ""))
                    new_number = last_number + 1
                except:
                    new_number = (last_worker.id or 0) + 1
            else:
                new_number = 1

            worker_code = f"OFCL{new_number:04d}"

            # ===============================
            # 8. CREATE WORKER
            # ===============================
            new_worker = Worker(
                worker_code=worker_code,
                name=name,
                phone_number=phone_number,
                date_of_birth=date_of_birth,
                gender=gender,
                email=email,
                qualifications=qualifications,
                position=position,
                amount_of_salary=amount_of_salary,
                date_of_employment=date_of_employment,
                guarantor=guarantor,
                national_id=national_id,
                nationality=nationality,
                ethnic_group=ethnic_group,
                disability=disability,
                home_address=home_address,
                place_of_residence=place_of_residence,
                bank_account_name=bank_account_name,
                bank_name=bank_name,
                bank_account=bank_account,
                passport=passport_filename,
                is_active=True
            )

            # ===============================
            # 9. SAVE
            # ===============================
            db.session.add(new_worker)
            db.session.commit()

            print(f"[WORKER CREATED] {worker_code} - {name}")

            flash(f"Worker registered successfully! Code: {worker_code}", "success")

            return redirect(url_for('workers_name'))

        except Exception as e:
            db.session.rollback()
            logging.error(f"REGISTER WORKER ERROR: {e}", exc_info=True)
            flash("Unexpected error occurred while saving worker.", "danger")
            return redirect(url_for('register_worker'))

    return render_template('register_worker.html')


@app.route('/workers')
@login_required()
def workers_name():
    if session.get('role') not in ['admin', 'secretary']:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    # Get all workers
    workers = Worker.query.order_by(Worker.id.desc()).all()

    # Get new worker ID for highlight
    new_worker_id = request.args.get('new_id', type=int)

    return render_template(
        'workers_name.html',
        workers=workers,
        new_worker_id=new_worker_id
    )


@app.route('/toggle_worker_status/<int:worker_id>', methods=['POST'])
@login_required(role='admin')
def toggle_worker_status(worker_id):

    worker = Worker.query.get_or_404(worker_id)

    reason = request.form.get('reason', '').strip()

    if not reason:
        flash("Reason is required before changing worker status.", "danger")
        return redirect(url_for('workers_name'))

    now = datetime.utcnow()

    # =========================
    # TOGGLE STATUS
    # =========================
    worker.is_active = not worker.is_active

    if worker.is_active:
        worker.status_type = "reactivated"
    else:
        worker.status_type = "deactivated"

    worker.status_reason = reason
    worker.status_date = now

    # =========================
    # TRACK ADMIN ACTION
    # =========================
    worker.last_action_by = session.get('role')
    worker.last_action_date = now

    # =========================
    # WARNING AUTO COUNT
    # =========================
    if not worker.is_active:
        worker.warning_count = (worker.warning_count or 0) + 1

    # =========================
    # REGENERATE LETTER
    # =========================
    worker.status_letter = generate_hr_letter(
        worker,
        reason,
        worker.status_type
    )

    db.session.commit()

    flash(f"{worker.name} status updated successfully.", "success")

    return redirect(url_for('workers_name'))


@app.route('/worker_history/<int:worker_id>')
@login_required()
def worker_history(worker_id):

    worker = Worker.query.get_or_404(worker_id)

    return render_template(
        'worker_history.html',
        worker=worker
    )


@app.route('/active-workers')
@login_required()
def active_workers():
    workers = Worker.query.filter_by(is_active=True).all()
    return render_template('workers_name.html', workers=workers)


@app.route('/inactive-workers')
@login_required()
def inactive_workers():
    workers = Worker.query.filter_by(is_active=False).all()
    return render_template('workers_name.html', workers=workers)


@app.route('/worker_letter/<int:worker_id>')
@login_required()
def worker_letter(worker_id):
    worker = Worker.query.get_or_404(worker_id)

    if not worker.status_letter:
        flash("No letter available for this worker.", "warning")
        return redirect(url_for('workers_name'))

    return render_template('worker_letter.html', worker=worker)


@app.route('/send_worker_letter/<int:worker_id>', methods=['POST'])
@login_required(role='admin')
def send_worker_letter(worker_id):

    worker = Worker.query.get_or_404(worker_id)

    # -----------------------
    # VALIDATION
    # -----------------------
    if not worker.email:
        flash("Worker has no email address.", "danger")
        return redirect(url_for('worker_letter', worker_id=worker.id))

    if not worker.status_letter:
        flash("No HR letter available.", "danger")
        return redirect(url_for('worker_letter', worker_id=worker.id))

    try:
        # -----------------------
        # DEBUG (PUT EXACTLY HERE)
        # -----------------------
        print("SENDING EMAIL TO:", worker.email)
        print("SMTP USER:", app.config['MAIL_USERNAME'])
        print("SMTP SERVER:", app.config['MAIL_SERVER'])

        # -----------------------
        # CREATE EMAIL MESSAGE
        # -----------------------
        msg = Message(
            subject="Official HR Letter - Okoya Food Ltd",
            sender=app.config['MAIL_DEFAULT_SENDER'],
            recipients=[worker.email],
            body=worker.status_letter
        )

        # -----------------------
        # SEND EMAIL
        # -----------------------
        mail.send(msg)

        flash("Letter sent successfully!", "success")

    except Exception as e:
        print("EMAIL ERROR:", str(e))
        traceback.print_exc()
        flash("Email failed. Check SMTP or network.", "danger")

    return redirect(url_for('worker_letter', worker_id=worker.id))

@app.route("/smtp-test")
def smtp_test():
    try:
        msg = Message(
            subject="Test Email",
            sender=app.config['MAIL_DEFAULT_SENDER'],
            recipients=[app.config['MAIL_USERNAME']],
            body="SMTP is working"
        )
        mail.send(msg)
        return "EMAIL SENT OK"
    except Exception as e:
        import traceback
        return f"<pre>{traceback.format_exc()}</pre>"
    

@app.route('/mail-debug-test')
def mail_debug_test():
    try:
        msg = Message(
            subject="TEST",
            sender=app.config['MAIL_DEFAULT_SENDER'],
            recipients=[app.config['MAIL_USERNAME']],
            body="Test email"
        )

        mail.send(msg)
        return "MAIL SENT"

    except Exception as e:
        return str(e)

@app.route("/mail-test")
def mail_test():
    try:
        print("STARTING EMAIL TEST")

        msg = Message(
            subject="Okoya SMTP Test",
            sender=app.config['MAIL_DEFAULT_SENDER'],
            recipients=["wismailadewale@gmail.com"],
            body="Brevo SMTP is now working from Render."
        )

        print("MESSAGE CREATED")

        mail.send(msg)

        print("EMAIL SENT SUCCESSFULLY")

        return "MAIL SENT SUCCESSFULLY"

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"<pre>{traceback.format_exc()}</pre>"


@app.route('/client_form', methods=['GET', 'POST'])
@login_required()
def client_form():
    if 'role' not in session:
        return redirect(url_for('login'))

    products = ["Soya Beans", "Cashew Nut", "Maize", "Rice"]

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        items = request.form.get('items')

        # ✅ SAFE conversion (prevents crash)
        try:
            kilograms = float(request.form.get('kilograms') or 0)
            unit_price = float(request.form.get('unit_price') or 0)
        except ValueError:
            kilograms = 0
            unit_price = 0

        total_amount = kilograms * unit_price

        # ✅ SAFE date handling
        date_str = request.form.get('date')
        try:
            date_needed = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None
        except:
            date_needed = None

        order = Order(
            name=name,
            email=email,
            items=items,
            kilograms=kilograms,
            unit_price=unit_price,
            total_amount=total_amount,
            date_needed=date_needed,
            driver_name=request.form.get('driver_name'),
            vehicle_plate_number=request.form.get('vehicle_plate_number'),
            bank_name=request.form.get('bank_name'),
            account_number=request.form.get('account_number'),
            account_bank_name=request.form.get('account_bank_name'),
            description=request.form.get('description'),
            phone_number=request.form.get('phone_number'),
            status="Pending"
        )

        db.session.add(order)
        db.session.commit()

        return redirect(
            url_for('orders_overview') if session['role'] == 'admin'
            else url_for('secretary_dashboard')
        )

    return render_template('client_form.html', products=products)

@app.route('/orders_overview')
@login_required(role='admin')
def orders_overview():

    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    all_orders = Order.query.order_by(Order.created_at.desc()).all()

    # -------------------------
    # PRODUCT GROUPING
    # -------------------------
    soya_orders = [o for o in all_orders if o.items and "soya" in o.items.lower()]
    cashew_orders = [o for o in all_orders if o.items and "cashew" in o.items.lower()]
    maize_orders = [o for o in all_orders if o.items and "maize" in o.items.lower()]
    rice_orders = [o for o in all_orders if o.items and "rice" in o.items.lower()]

    # -------------------------
    # ANALYTICS (NEW)
    # -------------------------
    total_orders = len(all_orders)
    total_revenue = sum(o.total_amount or 0 for o in all_orders)

    today = datetime.utcnow().date()
    today_sales = sum(
        o.total_amount or 0
        for o in all_orders
        if o.created_at and o.created_at.date() == today
    )

    pending_orders = len([o for o in all_orders if o.status == "Pending"])
    confirmed_orders = len([o for o in all_orders if o.status == "Confirmed"])
    delivered_orders = len([o for o in all_orders if o.status == "Delivered"])

    # -------------------------
    # TOP PRODUCT PERFORMANCE
    # -------------------------
    product_stats = {}
    for o in all_orders:
        if o.items:
            key = o.items.lower()
            product_stats[key] = product_stats.get(key, 0) + 1

    return render_template(
        'orders_overview.html',

        soya_orders=soya_orders,
        cashew_orders=cashew_orders,
        maize_orders=maize_orders,
        rice_orders=rice_orders,

        all_orders=all_orders,

        # analytics
        total_orders=total_orders,
        total_revenue=total_revenue,
        today_sales=today_sales,
        pending_orders=pending_orders,
        confirmed_orders=confirmed_orders,
        delivered_orders=delivered_orders,
        product_stats=product_stats,

        now=datetime.utcnow()
    )


@app.route('/confirm_order/<int:order_id>', methods=['POST'])
@login_required(role='admin')
def confirm_order(order_id):
    order = Order.query.get_or_404(order_id)

    order.status = "Confirmed"
    order.confirmed_at = datetime.utcnow()  # ✅ FIX ADDED

    db.session.commit()
    return redirect(url_for('orders_overview'))


@app.route('/delete_order/<int:order_id>', methods=['POST'])
@login_required(role='admin')
def delete_order(order_id):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    order = Order.query.get_or_404(order_id)
    db.session.delete(order)
    db.session.commit()

    return redirect(url_for('orders_overview'))

@app.route('/print_order/<int:order_id>')
@login_required()
def print_order(order_id):
    order = Order.query.get_or_404(order_id)  # Fetch the order by ID
    return render_template('print_order.html', order=order)


@app.route('/favicon.ico')
def favicon():
    return "", 204


from openpyxl import Workbook

@app.route('/export_order/<int:order_id>')
@login_required()
def export_order(order_id):
    order = Order.query.get_or_404(order_id)

    wb = Workbook()
    ws = wb.active
    ws.title = "Order"

    ws.append([
        "Client Name", "Email", "Phone", "Item",
        "Description", "Kilograms", "Unit Price",
        "Total", "Driver", "Vehicle",
        "Account Number", "Bank", "Date"
    ])

    ws.append([
        order.name,
        order.email,
        order.phone_number,
        order.items,
        order.description,
        order.kilograms,
        order.unit_price,
        order.total_amount,
        order.driver_name,
        order.vehicle_plate_number,
        order.account_number,
        order.account_bank_name,
        order.date_needed
    ])

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        download_name=f"order_{order.id}.xlsx",
        as_attachment=True
    )


@app.route('/export_all_orders')
@login_required(role='admin')
def export_all_orders():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    orders = Order.query.order_by(Order.created_at.desc()).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "All Orders"

    ws.append([
        "Client Name", "Email", "Phone", "Item",
        "Description", "Kilograms", "Unit Price",
        "Total", "Driver", "Vehicle",
        "Account Number", "Bank", "Date",
        "Status", "Created At"
    ])

    for order in orders:
        ws.append([
            order.name,
            order.email,
            order.phone_number,
            order.items,
            order.description,
            order.kilograms,
            order.unit_price,
            order.total_amount,
            order.driver_name,
            order.vehicle_plate_number,
            order.account_number,
            order.account_bank_name,
            str(order.date_needed) if order.date_needed else "",
            order.status,
            order.created_at.strftime('%Y-%m-%d %H:%M') if order.created_at else ""
        ])

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        download_name="all_orders.xlsx",
        as_attachment=True
    )


@app.route('/edit_worker/<int:worker_id>', methods=['GET', 'POST'])
@login_required(role='admin')
def edit_worker(worker_id):
    worker = Worker.query.get_or_404(worker_id)

    if request.method == 'POST':
        try:
            # =========================
            # UPDATE FIELDS
            # =========================
            worker.name = (request.form.get('name') or "").strip()
            worker.phone_number = (request.form.get('phone_number') or "").strip()
            worker.gender = (request.form.get('gender') or "").strip()
            worker.email = (request.form.get('email') or "").strip().lower()

            worker.qualifications = (request.form.get('qualifications') or "").strip()
            worker.position = (request.form.get('position') or "").strip()

            worker.national_id = (request.form.get('national_id') or "").strip()
            worker.nationality = (request.form.get('nationality') or "").strip()

            worker.home_address = (request.form.get('home_address') or "").strip()
            worker.ethnic_group = (request.form.get('ethnic_group') or "").strip()
            worker.place_of_residence = (request.form.get('place_of_residence') or "").strip()

            worker.disability = (request.form.get('disability') or "").strip()

            worker.bank_name = (request.form.get('bank_name') or "").strip()
            worker.bank_account = (request.form.get('bank_account') or "").strip()
            worker.bank_account_name = (request.form.get('bank_account_name') or "").strip()

            worker.guarantor = (request.form.get('guarantor') or "").strip()

            try:
                worker.amount_of_salary = float(request.form.get('amount_of_salary') or 0)
            except ValueError:
                worker.amount_of_salary = 0

            # =========================
            # SAFE DATE
            # =========================
            def safe_date(value):
                try:
                    return datetime.strptime(value, "%Y-%m-%d").date()
                except:
                    return None

            worker.date_of_birth = safe_date(request.form.get('date_of_birth'))
            worker.date_of_employment = safe_date(request.form.get('date_of_employment'))

            # =========================
            # PASSPORT UPDATE
            # =========================
            passport_file = request.files.get('passport')

            if passport_file and passport_file.filename:

                if allowed_file(passport_file.filename):

                    upload_folder = app.config.get('UPLOAD_FOLDER', 'static/uploads')
                    os.makedirs(upload_folder, exist_ok=True)

                    # delete old file
                    if worker.passport:
                        old_file = os.path.join(upload_folder, worker.passport)
                        if os.path.exists(old_file):
                            try:
                                os.remove(old_file)
                            except:
                                pass

                    # save new file
                    safe_name = secure_filename(passport_file.filename)
                    new_filename = f"{uuid.uuid4().hex}_{safe_name}"

                    passport_file.save(
                        os.path.join(upload_folder, new_filename)
                    )

                    worker.passport = new_filename
                    worker.updated_at = datetime.utcnow()
    
                else:
                    flash("Only jpg, jpeg and png files allowed.", "danger")
                    return redirect(url_for('edit_worker', worker_id=worker.id))

            # =========================
            # SAVE
            # =========================
            db.session.commit()

            flash('Worker details updated successfully.', 'success')
            return redirect(url_for('workers_name'))

        except Exception as e:
            db.session.rollback()
            flash(f"Error updating worker: {e}", "danger")

    return render_template('edit_worker.html', worker=worker)


@app.route('/worker_id_card/<int:worker_id>')
@login_required(role='admin')
def worker_id_card(worker_id):

    worker = Worker.query.get_or_404(worker_id)

    # ============================
    # PASSPORT URL (NEW FIX)
    # ============================
    passport_url = get_passport_url(worker)

    # ============================
    # BUILD VERIFICATION PAYLOAD
    # ============================
    verify_url = url_for(
        'verify_worker',
        worker_code=worker.worker_code,
        _external=True
    )

    qr_data = {
        "company": "OKOYA FOOD COMPANY LIMITED",
        "worker_code": worker.worker_code,
        "name": worker.name,
        "position": worker.position,
        "phone": worker.phone_number or "N/A",
        "status": "Active" if worker.is_active else "Inactive",
        "verify_url": verify_url
    }

    qr_string = json.dumps(qr_data, ensure_ascii=False)

    # ============================
    # GENERATE QR CODE
    # ============================
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=4,
        border=2
    )

    qr.add_data(qr_string)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    qr_base64 = base64.b64encode(buffer.read()).decode('utf-8')

    return render_template(
        'worker_id_card.html',
        worker=worker,
        qr_code=qr_base64,
        passport_url=passport_url
    )


@app.route('/verify/<worker_code>')
def verify_worker(worker_code):

    worker = Worker.query.filter_by(worker_code=worker_code).first_or_404()

    return render_template('verify_worker.html', worker=worker)


@app.route('/routes')
def routes():
    import urllib
    return "<br>".join(sorted(str(r) for r in app.url_map.iter_rules()))


@app.route('/delete_worker/<int:worker_id>', methods=['POST'])
@login_required(role='admin')
def delete_worker(worker_id):

    worker = Worker.query.get_or_404(worker_id)

    try:
        # 1. delete passport file safely
        if worker.passport:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], worker.passport)
            if os.path.exists(file_path):
                os.remove(file_path)

        # 2. delete related records FIRST (safe cascade alternative)
        db.session.query(EmailLog).filter_by(worker_id=worker.id).delete()
        db.session.query(Attendance).filter_by(worker_id=worker.id).delete()
        db.session.query(Salary).filter_by(worker_id=worker.id).delete()

        # 3. delete worker
        db.session.delete(worker)
        db.session.commit()

        flash('Worker deleted successfully.', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting worker: {str(e)}', 'danger')

    return redirect(url_for('workers_name'))


# Alias route for secretary_attendance (fix BuildError)
@app.route('/secretary_attendance', methods=['GET', 'POST'])
def secretary_attendance():
    # Reuse the attendance function logic
    return redirect(url_for('attendance'))


@app.route('/attendance', methods=['GET', 'POST'])
@login_required()
def attendance():

    workers = Worker.query.filter_by(is_active=True).all()
    secretary = session.get('role') == 'secretary'

    today = date.today()

    # 🔥 DAILY SUMMARY (useful for dashboard analytics later)
    total_workers = len(workers)
    today_present_count = Attendance.query.filter_by(
        date=today,
        status="Present"
    ).count()

    today_absent_count = Attendance.query.filter_by(
        date=today,
        status="Absent"
    ).count()

    if request.method == 'POST':

        worker_id = request.form.get('worker_id')
        status = request.form.get('attendance_status')

        # 🔐 Validation
        if not worker_id or not status:
            flash("Missing attendance data.", "error")
            return redirect(url_for('attendance'))

        try:
            worker_id = int(worker_id)
        except ValueError:
            flash("Invalid worker ID.", "error")
            return redirect(url_for('attendance'))

        worker = Worker.query.get(worker_id)

        if not worker:
            flash("Worker not found.", "error")
            return redirect(url_for('attendance'))

        # 🚫 Prevent duplicate attendance per day
        existing = Attendance.query.filter_by(
            worker_id=worker_id,
            date=today
        ).first()

        if existing:
            flash(f"{worker.name} already marked for today.", "warning")
            return redirect(url_for('attendance'))

        try:
            new_attendance = Attendance(
                worker_id=worker_id,
                status=status,
                date=today
            )

            db.session.add(new_attendance)
            db.session.commit()

            flash(f"Attendance marked for {worker.name}.", "success")

        except Exception as e:
            db.session.rollback()
            logging.error(f"Attendance error: {e}")
            flash("System error while saving attendance.", "error")

        return redirect(url_for('attendance'))

    return render_template(
        'attendance.html',
        workers=workers,
        secretary=secretary,
        total_workers=total_workers,
        today_present_count=today_present_count,
        today_absent_count=today_absent_count,
        today=today
    )


@app.route('/salary', methods=['GET', 'POST'])
@login_required(role='admin')
def salary():

    workers = Worker.query.filter_by(is_active=True).all()

    today = datetime.today()
    current_year = today.year
    current_month = today.month

    total_days_in_month = monthrange(current_year, current_month)[1]

    if total_days_in_month < 1:
        total_days_in_month = 1

    salary_data = []

    total_payroll = 0  # 🔥 future analytics

    for worker in workers:

        total_days_present = Attendance.query.filter(
            Attendance.worker_id == worker.id,
            Attendance.status == "Present",
            extract('year', Attendance.date) == current_year,
            extract('month', Attendance.date) == current_month
        ).count()

        daily_rate = (worker.amount_of_salary or 0) / total_days_in_month

        calculated_salary = total_days_present * daily_rate

        total_payroll += calculated_salary

        salary_data.append({
            'id': worker.id,
            'name': worker.name,
            'total_days_present': total_days_present,
            'calculated_salary': round(calculated_salary, 2),
            'bank_name': worker.bank_name or '',
            'bank_account': worker.bank_account or '',
            'bank_account_name': worker.bank_account_name or ''
        })

    if request.method == 'POST':

        try:
            worker_id = int(request.form.get('worker_id'))
            worker = Worker.query.get(worker_id)

            if not worker:
                flash("Worker not found.", "error")
                return redirect(url_for('salary'))

            # 🚫 Prevent duplicate salary for same month
            existing_salary = Salary.query.filter_by(
                worker_id=worker_id
            ).filter(
                extract('year', Salary.payment_date) == current_year,
                extract('month', Salary.payment_date) == current_month
            ).first()

            if existing_salary:
                flash(f"Salary already recorded for {worker.name} this month.", "warning")
                return redirect(url_for('salary_history'))

            total_days_present = Attendance.query.filter(
                Attendance.worker_id == worker.id,
                Attendance.status == "Present",
                extract('year', Attendance.date) == current_year,
                extract('month', Attendance.date) == current_month
            ).count()

            daily_rate = (worker.amount_of_salary or 0) / total_days_in_month
            calculated_salary = total_days_present * daily_rate

            new_salary = Salary(
                worker_id=worker.id,
                total_days_present=total_days_present,
                daily_rate=daily_rate,
                amount=round(calculated_salary, 2),
                bank_name=worker.bank_name,
                bank_account=worker.bank_account,
                bank_account_name=worker.bank_account_name,
                payment_date=datetime.now()
            )

            db.session.add(new_salary)
            db.session.commit()

            flash(f"Salary recorded successfully for {worker.name}.", "success")

            return redirect(url_for('salary_history'))

        except Exception as e:
            db.session.rollback()
            logging.error(f"Salary error: {e}")
            flash("Error recording salary. Try again.", "error")

    return render_template(
        'salary.html',
        salary_data=salary_data,
        total_payroll=round(total_payroll, 2),
        current_month=current_month,
        current_year=current_year
    )


@app.route('/attendance_history')
@login_required()  # admin or secretary
def attendance_history():
    """
    Display attendance records with optional month filtering.
    Admins and secretaries can view all attendance records.
    """
    if session.get('role') not in ['admin', 'secretary']:
        flash("Please login first.", "warning")
        return redirect(url_for('login'))

    selected_month = request.args.get('month')  # Format: 'Month Year', e.g., 'December 2025'

    # Base query: all attendance records
    attendance_query = Attendance.query.join(Worker).order_by(Attendance.date.desc())

    # Generate available months dynamically
    all_records = attendance_query.all()
    available_months = sorted(
        list({record.date.strftime("%B %Y") for record in all_records}),
        reverse=True
    )

    # Filter records by selected month if provided
    if selected_month:
        try:
            month_dt = datetime.strptime(selected_month, "%B %Y")
            attendance_query = attendance_query.filter(
                extract('month', Attendance.date) == month_dt.month,
                extract('year', Attendance.date) == month_dt.year
            )
        except ValueError:
            flash("Invalid month format for filtering.", "error")

    attendance_records = attendance_query.all()

    return render_template(
        "attendance_history.html",
        attendance_records=attendance_records,
        available_months=available_months,
        selected_month=selected_month,
        now=datetime.now()
    )


@app.route('/salary_history')
@login_required()
def salary_history():
        # Restrict access to admin and secretary only
    if session.get('role') not in ['admin', 'secretary']:
        return redirect(url_for('login'))

    # Base query (join to include worker details)
    salary_query = db.session.query(Salary).join(Worker).order_by(Salary.payment_date.desc())

    # Get month filter from query string (format: 'YYYY-MM')
    selected_month = request.args.get('month')

    # Apply month filter if selected
    if selected_month:
        from sqlalchemy import extract
        try:
            year, month = map(int, selected_month.split('-'))
            salary_query = salary_query.filter(
                extract('year', Salary.payment_date) == year,
                extract('month', Salary.payment_date) == month
            )
        except ValueError:
            # In case month string is malformed, skip filtering
            pass

    # Fetch salary records (after filtering)
    salary_records = salary_query.all()

    # Generate available months dynamically (from fetched records)
    available_months_set = set()
    for record in Salary.query.order_by(Salary.payment_date.desc()).all():
        if record.payment_date:  # Ensure valid date
            available_months_set.add(record.payment_date.strftime("%Y-%m"))
    available_months = sorted(list(available_months_set), reverse=True)

    # Current date/time (for print view or footer)
    now = datetime.now()

    # Render the salary history page
    return render_template(
        'salary_history.html',
        salary_records=salary_records,
        available_months=available_months,
        selected_month=selected_month,
        now=now
    )


@app.route("/backup-now")
@login_required(role='admin')
def backup_now():

    db_url = app.config['SQLALCHEMY_DATABASE_URI']

    file_path = create_backup(db_url)

    if file_path:
        flash("Backup created successfully!", "success")
        return send_file(file_path, as_attachment=True)

    flash("Backup failed!", "danger")
    return redirect(url_for("admin_dashboard"))


# ===============================
# UNIVERSAL LOGIN + DASHBOARDS
# ===============================

@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # --- Admin credentials ---
        ADMIN_USER = os.environ.get('ADMIN_USERNAME', 'admin')
        ADMIN_PASS = os.environ.get('ADMIN_PASSWORD', 'Alayinde001')


        # --- Secretary credentials ---
        SECRETARY_USER = os.environ.get('SECRETARY_USERNAME', 'secretary')
        SECRETARY_PASS = os.environ.get('SECRETARY_PASS', 'Sec001')

        # --- Check credentials ---
        if username == ADMIN_USER and password == ADMIN_PASS:
            session['role'] = 'admin'
            flash("Welcome Admin!", "success")
            return redirect(url_for('admin_dashboard'))

        elif username == SECRETARY_USER and password == SECRETARY_PASS:
            session['role'] = 'secretary'
            flash("Welcome Secretary!", "success")
            return redirect(url_for('secretary_dashboard'))

        else:
            error = 'Invalid username or password.'

    return render_template('login.html', error=error)
    
@app.route('/admin_dashboard')
@login_required(role='admin')
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/secretary_dashboard')
@login_required(role='secretary')
def secretary_dashboard():
    return render_template('secretary_dashboard.html')

@app.route('/logout_admin')
def logout_admin():
    session.clear()
    return redirect(url_for('login'))
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for('login'))


# ================= HEALTH CHECK (UPTIME ROBOT) =================
@app.route("/health")
def health():
    return "OK", 200

    
@app.route('/test')
def test_routes():
    try:
        url = url_for('attendance')
        return f"Attendance URL: {url}"
    except Exception as e:
        return f"Error: {e}"


# ------------------------------
# Main block
# ------------------------------
# ------------------------------
# Create database tables safely
# ------------------------------
@app.errorhandler(Exception)
def handle_exception(e):
    import traceback
    traceback.print_exc()
    return f"<pre>{traceback.format_exc()}</pre>", 500


def auto_backup_loop():
    while True:
        try:
            print("Running auto backup...")

            db_url = app.config['SQLALCHEMY_DATABASE_URI']
            create_backup(db_url)

            print("Backup completed")

        except Exception as e:
            print("Backup error:", e)

        time.sleep(86400)  # 24 hours
        
if os.environ.get("RENDER") != "true":
    threading.Thread(target=auto_backup_loop, daemon=True).start()

if __name__ == '__main__':
    with app.app_context():
        pass  # REMOVE db.create_all()

    print("🚀 Okoya Food Staff Manager app is starting...")
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)