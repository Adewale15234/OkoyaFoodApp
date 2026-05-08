from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, date
from calendar import monthrange
from sqlalchemy import extract, create_engine, text
from sqlalchemy.orm import sessionmaker
import os
import logging
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()
import psycopg2
from functools import wraps
import uuid
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
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

# Secret key
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME')

# Upload folder
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Mail config
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USE_SSL=False,
    MAIL_USERNAME=os.environ.get('MAIL_USERNAME'),
    MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD'),
    MAIL_DEFAULT_SENDER=os.environ.get('MAIL_USERNAME')
)

mail = Mail(app)

# ------------------------------
# Database config
# ------------------------------
if os.environ.get("RENDER"):
    db_url = os.environ.get("DATABASE_URL")
else:
    db_url = "sqlite:///okoya.db"

if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
from sqlalchemy import create_engine

@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.remove()


app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_pre_ping": True,
    "pool_recycle": 280,
}
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

    # =========================
    # STATUS SYSTEM
    # =========================
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    status_reason = db.Column(db.Text, nullable=True)
    status_date = db.Column(db.DateTime, nullable=True)
    status_type = db.Column(db.String(30), nullable=True)
    status_letter = db.Column(db.Text, nullable=True)

    # Relationships
    attendance_records = db.relationship(
        'Attendance',
        backref='worker',
        lazy=True,
        cascade="all, delete-orphan"
    )
    salary_records = db.relationship(
        'Salary',
        backref='worker',
        lazy=True,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Worker {self.name}>"


class EmailLog(db.Model):
    __tablename__ = 'email_logs'

    id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('workers.id'), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="Sent")

    # ✅ KEEP THIS ONLY (DO NOT CREATE relationship in Worker again)
    worker = db.relationship('Worker', backref='email_logs')
      

      # ===============================
# AI OFFENCE REVIEW FUNCTION
# ===============================
def ai_offence_review(worker, reason):
    severity_keywords = ["theft", "fight", "absent", "steal", "violence", "insult", "late"]

    severity = "Low"
    for word in severity_keywords:
        if word in reason.lower():
            severity = "High"
            break

    explanation = f"""
OFFENCE REVIEW ANALYSIS

Worker: {worker.name}
Position: {worker.position}
Code: {worker.worker_code}

Reported Issue:
{reason}

AI Assessment:
- Severity Level: {severity}
- Recommendation: {"Immediate Suspension" if severity == "High" else "Warning or Review"}

Summary:
This case requires {"strict disciplinary action" if severity == "High" else "HR monitoring and caution"}.
"""

    return explanation


# ===============================
# HR LETTER GENERATOR FUNCTION
# ===============================
def generate_hr_letter(worker, reason, status_type):

    name = worker.name or "Unknown"
    code = worker.worker_code or "N/A"
    position = worker.position or "N/A"
    date = datetime.utcnow().strftime('%Y-%m-%d')

    if status_type == "deactivated":
        return f"""
OKOYA FOOD LTD
OFFICIAL DISCIPLINARY NOTICE

Employee: {name}
Code: {code}
Position: {position}

STATUS: DEACTIVATED

Reason:
{reason or 'No reason provided'}

HR Decision:
You are temporarily suspended pending review.

Date: {date}

HR Department
"""

    else:
        return f"""
OKOYA FOOD LTD
REINSTATEMENT NOTICE

Employee: {name}
Code: {code}

STATUS: REACTIVATED

You have been reinstated back to duty.

Date: {date}

HR Department
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
    # confirmed_at = db.Column(db.DateTime)   # <-- ADD THIS (you are using it!)
    driver_name = db.Column(db.String(100))
    vehicle_plate_number = db.Column(db.String(50))
    bank_name = db.Column(db.String(100))
    account_number = db.Column(db.String(50))
    account_bank_name = db.Column(db.String(200))
    description = db.Column(db.String(255))
    phone_number = db.Column(db.String(100))
    status = db.Column(db.String(20), default="Pending")

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('workers.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=db.func.current_date())
    status = db.Column(db.String(10), nullable=False)

class Salary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('workers.id'), nullable=False)
    total_days_present = db.Column(db.Integer, nullable=False)
    daily_rate = db.Column(db.Float, nullable=False, default=0.0)
    amount = db.Column(db.Float, nullable=False)
    bank_name = db.Column(db.String(100), nullable=True)
    bank_account = db.Column(db.String(50), nullable=True)
    bank_account_name = db.Column(db.String(100), nullable=True)
    payment_date = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())

# Hardcoded credentials (Not secure! Replace with real auth for production)
USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
PASSWORD = os.environ.get('ADMIN_PASSWORD', 'Alayinde001')


# Routes

@app.route('/register_worker', methods=['GET', 'POST'])
@login_required(role='admin')
def register_worker():
    if request.method == 'POST':
        try:
            # -------------------------
            # Collect form data
            # -------------------------
            name = request.form.get('name')
            phone_number = request.form.get('phone_number')
            date_of_birth_str = request.form.get('date_of_birth')
            gender = request.form.get('gender')
            email = request.form.get('email')
            qualifications = request.form.get('qualifications')
            position = request.form.get('position')
            amount_of_salary = float(request.form.get('amount_of_salary', 0))
            date_of_employment_str = request.form.get('date_of_employment')
            guarantor = request.form.get('guarantor')
            national_id = request.form.get('national_id')
            nationality = request.form.get('nationality')
            ethnic_group = request.form.get('ethnic_group')
            disability = request.form.get('disability')
            home_address = request.form.get('home_address')
            place_of_residence = request.form.get('place_of_residence')
            bank_account_name = request.form.get('bank_account_name')
            bank_name = request.form.get('bank_name')
            bank_account = request.form.get('bank_account')

            # -------------------------
            # Convert date strings to date objects
            # -------------------------
            date_of_birth = datetime.strptime(date_of_birth_str, '%Y-%m-%d').date()
            date_of_employment = datetime.strptime(date_of_employment_str, '%Y-%m-%d').date()

            # -------------------------
            # Passport upload handling
            # -------------------------
            passport_file = request.files.get('passport')
            passport_filename = None


            if passport_file and passport_file.filename != "":
                passport_folder = app.config['UPLOAD_FOLDER']
                os.makedirs(passport_folder, exist_ok=True)

                passport_filename = str(uuid.uuid4()) + "_" + secure_filename(passport_file.filename)
                passport_file.save(os.path.join(passport_folder, passport_filename))

            # -------------------------
            # Auto-generate worker code
            # -------------------------
            last_worker = Worker.query.order_by(Worker.id.desc()).first()
            if last_worker and last_worker.worker_code:
                # Extract number from code, e.g., OFCL005 -> 5
                last_number = int(last_worker.worker_code.replace("OFCL", ""))
                new_number = last_number + 1
            else:
                new_number = 1

            worker_code = f"OFCL{new_number:03d}"  # Zero-padded to 3 digits

            # -------------------------
            # Create Worker object
            # -------------------------
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
                passport=passport_filename
            )

            # -------------------------
            # Save to database
            # -------------------------
            db.session.add(new_worker)
            db.session.commit()
            flash(f'Worker registered successfully! Worker Code: {worker_code}', 'success')
            return redirect(url_for('workers_name'))

        except Exception as e:
            db.session.rollback()
            flash(f"Error saving worker: {e}", 'danger')
            return redirect(url_for('register_worker'))

    # GET request: show form
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
    action = request.form.get('action')  # review or confirm
    now = datetime.utcnow()

    # =========================
    # STEP 1: AI REVIEW MODE
    # =========================
    if action == "review":
        ai_report = ai_offence_review(worker, reason)

        return render_template(
            "offence_review.html",
            worker=worker,
            reason=reason,
            ai_report=ai_report
        )

    # =========================
    # STEP 2: CONFIRM DEACTIVATION
    # =========================
    if worker.is_active:
        worker.is_active = False
        worker.status_reason = reason or "No reason provided"
        worker.status_type = "deactivated"
        worker.status_date = now

        worker.status_letter = generate_hr_letter(worker, reason, "deactivated")

    else:
        worker.is_active = True
        worker.status_type = "reactivated"
        worker.status_reason = None
        worker.status_date = now

        worker.status_letter = generate_hr_letter(worker, reason, "reactivated")

    db.session.commit()
    return redirect(url_for('workers_name'))


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


@app.route('/send_worker_letter/<int:worker_id>')
@login_required(role='admin')
def send_worker_letter(worker_id):
    worker = Worker.query.get_or_404(worker_id)

    if not worker.email:
        flash("Worker has no email address.", "danger")
        return redirect(url_for('worker_letter', worker_id=worker_id))

    if not worker.status_letter:
        flash("No letter found for this worker.", "warning")
        return redirect(url_for('worker_letter', worker_id=worker_id))

    try:
        sender_email = app.config.get("MAIL_DEFAULT_SENDER") or app.config.get("MAIL_USERNAME")

        msg = Message(
            subject="Official HR Letter - Okoya Food Ltd",
            sender=sender_email,
            recipients=[worker.email]
        )

        msg.body = f"""
Dear {worker.name},

Please find your official HR letter below:

---------------------------------
{worker.status_letter}
---------------------------------

Regards,
HR Department
Okoya Food Ltd
"""

        mail.send(msg)

        # log success
        log = EmailLog(
            worker_id=worker.id,
            email=worker.email,
            status="Sent"
        )
        db.session.add(log)
        db.session.commit()

        flash("Letter sent successfully to worker email.", "success")

    except Exception as e:
        db.session.rollback()

        # log failure
        log = EmailLog(
            worker_id=worker.id,
            email=worker.email,
            status=f"Failed: {str(e)}"
        )
        db.session.add(log)
        db.session.commit()

        flash(f"Failed to send email: {e}", "danger")

    return redirect(url_for('worker_letter', worker_id=worker_id))


@app.route('/mail-debug')
def mail_debug():
    return {
        "MAIL_USERNAME": app.config.get("MAIL_USERNAME"),
        "MAIL_DEFAULT_SENDER": app.config.get("MAIL_DEFAULT_SENDER"),
        "MAIL_PASSWORD_EXISTS": bool(app.config.get("MAIL_PASSWORD"))
    }

@app.route('/mail-test')
def mail_test():
    try:
        msg = Message(
            subject="Test Email",
            sender=app.config['MAIL_USERNAME'],
            recipients=[app.config['MAIL_USERNAME']]
        )

        msg.body = "Testing Gmail SMTP"

        mail.send(msg)

        return "Email sent successfully"

    except Exception as e:
        return str(e)


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

    # ✅ FLEXIBLE matching (prevents missing records)
    soya_orders = [o for o in all_orders if o.items and "soya" in o.items.lower()]
    cashew_orders = [o for o in all_orders if o.items and "cashew" in o.items.lower()]
    maize_orders = [o for o in all_orders if o.items and "maize" in o.items.lower()]
    rice_orders = [o for o in all_orders if o.items and "rice" in o.items.lower()]

    return render_template(
        'orders_overview.html',
        soya_orders=soya_orders,
        cashew_orders=cashew_orders,
        maize_orders=maize_orders,
        rice_orders=rice_orders,
        now=datetime.utcnow()
    )


@app.route('/confirm_order/<int:order_id>', methods=['POST'])
@login_required(role='admin')
def confirm_order(order_id):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    order = Order.query.get_or_404(order_id)
    order.status = "Confirmed"
    # order.confirmed_at = datetime.utcnow()

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

        
@app.route('/export_order/<int:order_id>')
@login_required()
def export_order(order_id):
    if session.get('role') not in ['admin', 'secretary']:
        return redirect(url_for('login'))

    order = Order.query.get_or_404(order_id)

    data = [{
        "Client Name": order.name,
        "Email": order.email,
        "Phone": order.phone_number,
        "Item": order.items,
        "Description": order.description,
        "Kilograms": order.kilograms,
        "Unit Price": order.unit_price,
        "Total": order.total_amount,
        "Driver": order.driver_name,
        "Vehicle": order.vehicle_plate_number,
        "Account Number": order.account_number,
        "Bank": order.account_bank_name,
        "Date": order.date_needed
    }]

    df = pd.DataFrame(data)

    output = io.BytesIO()
    df.to_excel(output, index=False)
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

    data = []
    for order in orders:
        data.append({
            "Client Name": order.name,
            "Email": order.email,
            "Phone": order.phone_number,
            "Item": order.items,
            "Description": order.description,
            "Kilograms": order.kilograms,
            "Unit Price": order.unit_price,
            "Total": order.total_amount,
            "Driver": order.driver_name,
            "Vehicle": order.vehicle_plate_number,
            "Account Number": order.account_number,
            "Bank": order.account_bank_name,
            "Date": order.date_needed,
            "Status": order.status,
            "Created At": order.created_at.strftime('%Y-%m-%d %H:%M')
        })

    df = pd.DataFrame(data)

    output = io.BytesIO()
    df.to_excel(output, index=False)
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
            # -------------------------
            # Update worker fields from form
            # -------------------------
            worker.name = request.form['name']
            worker.phone_number = request.form['phone_number']
            worker.date_of_birth = datetime.strptime(request.form['date_of_birth'], '%Y-%m-%d').date()
            worker.date_of_employment = datetime.strptime(request.form['date_of_employment'], '%Y-%m-%d').date()
            worker.gender = request.form['gender']
            worker.qualifications = request.form['qualifications']
            worker.position = request.form['position']
            worker.national_id = request.form['national_id']
            worker.nationality = request.form['nationality']
            worker.home_address = request.form['home_address']
            worker.ethnic_group = request.form['ethnic_group']
            worker.place_of_residence = request.form['place_of_residence']
            worker.disability = request.form.get('disability')
            worker.email = request.form['email']
            worker.amount_of_salary = float(request.form.get('amount_of_salary', 0))
            worker.bank_name = request.form.get('bank_name')
            worker.bank_account = request.form.get('bank_account')
            worker.guarantor = request.form.get('guarantor')
            worker.bank_account_name = request.form.get('bank_account_name')

            # -------------------------
            # Handle passport update
            # -------------------------
            passport_file = request.files.get('passport')
            if passport_file and passport_file.filename != "":
                passport_filename = str(uuid.uuid4()) + "_" + secure_filename(passport_file.filename)
                passport_folder = app.config['UPLOAD_FOLDER']
                os.makedirs(passport_folder, exist_ok=True)
                passport_file.save(os.path.join(passport_folder, passport_filename))
                worker.passport = passport_filename  # update database field

            db.session.commit()
            flash('Worker details updated successfully.', 'success')
            return redirect(url_for('workers_name'))

        except Exception as e:
            db.session.rollback()
            flash(f"Error updating worker: {e}", "danger")

    return render_template('edit_worker.html', worker=worker)


@app.route('/delete_worker/<int:worker_id>', methods=['POST'])
@login_required(role='admin')
def delete_worker(worker_id):
    worker = Worker.query.get_or_404(worker_id)
    db.session.delete(worker)
    db.session.commit()
    flash('Worker deleted successfully.')
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
    secretary = session.get('role') == 'secretary'  # detect if secretary

    if request.method == 'POST':
        worker_id = request.form.get('worker_id')
        status = request.form.get('attendance_status')

        if worker_id and status:
            today = date.today()
            try:
                worker_id_int = int(worker_id)
            except ValueError:
                flash("Invalid worker ID.", "error")
                return redirect(url_for('attendance'))

            existing = Attendance.query.filter_by(worker_id=worker_id_int, date=today).first()
            if existing:
                flash('Attendance already submitted for this worker today.', 'warning')
            else:
                attendance = Attendance(worker_id=worker_id_int, status=status, date=today)
                db.session.add(attendance)
                db.session.commit()
                flash('Attendance marked successfully.', 'success')

        return redirect(url_for('attendance'))

    return render_template('attendance.html', workers=workers, secretary=secretary)


@app.route('/salary', methods=['GET', 'POST'])
@login_required(role='admin')  # Only admin can access
def salary():
    workers = Worker.query.filter_by(is_active=True).all()
    today = datetime.today()
    current_year = today.year
    current_month = today.month
    total_days_in_month = monthrange(current_year, current_month)[1]

    if total_days_in_month == 0:
        total_days_in_month = 1

    salary_data = []
    for worker in workers:
        total_days_present = Attendance.query.filter(
            Attendance.worker_id == worker.id,
            Attendance.status == "Present",
            extract('year', Attendance.date) == current_year,
            extract('month', Attendance.date) == current_month
        ).count()

        calculated_salary = (total_days_present / total_days_in_month) * worker.amount_of_salary

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
            total_days_present = Attendance.query.filter(
                Attendance.worker_id == worker.id,
                Attendance.status == "Present",
                extract('year', Attendance.date) == current_year,
                extract('month', Attendance.date) == current_month
            ).count()

            calculated_salary = (total_days_present / total_days_in_month) * worker.amount_of_salary

            new_salary = Salary(
                worker_id=worker.id,
                total_days_present=total_days_present,
                daily_rate=worker.amount_of_salary / total_days_in_month,
                amount=round(calculated_salary, 2),
                bank_name=worker.bank_name,
                bank_account=worker.bank_account,
                bank_account_name=worker.bank_account_name
            )
            db.session.add(new_salary)
            db.session.commit()
            flash(f"Salary for {worker.name} recorded successfully.")
            return redirect(url_for('salary_history'))
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error recording salary: {e}")
            flash("There was an error recording the salary. Please try again.", "error")

    return render_template('salary.html', salary_data=salary_data)


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
if __name__ == '__main__':
    print("🚀 Okoya Co,. Food Staff Manager app is starting...")
    app.debug = True
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)