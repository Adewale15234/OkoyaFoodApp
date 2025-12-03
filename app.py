from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, upgrade  # ✅ 'upgrade' is now imported
from datetime import datetime, date
from calendar import monthrange   # ✅ Add this line
from sqlalchemy import extract, create_engine
from sqlalchemy.orm import sessionmaker
import os
import logging
from functools import wraps
import uuid
from werkzeug.utils import secure_filename

# ------------------------------
# Login decorator
# ------------------------------
def login_required(role=None):
    """
    Protect a route with login and optional role-based access.

    Usage:
        @login_required()                  -> any logged-in user
        @login_required(role='admin')      -> only admin
        @login_required(role='secretary')  -> only secretary
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_role = session.get('role')
            if not user_role or (role and user_role != role):
                flash("Please login with proper credentials.", "danger")
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
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key')

# ------------------------------
# Passport upload folder
# ------------------------------
UPLOAD_FOLDER = os.path.join(app.root_path, 'static/passports')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ------------------------------
# Main Database (primary)
# ------------------------------
if os.environ.get("DATABASE_URL"):
    main_db_uri = os.environ["DATABASE_URL"].replace("postgres://", "postgresql://")
    app.config['SQLALCHEMY_DATABASE_URI'] = main_db_uri
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }
else:
    db_path = os.path.join('/tmp', 'site.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# SQLAlchemy for main DB (existing ORM models)
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# ------------------------------
# Second Database (optional)
# ------------------------------
second_db_uri = os.environ.get("DATABASE_URL_2")
second_engine = None
SecondSession = None

if second_db_uri:
    # Convert if starts with old "postgres://"
    second_db_uri = second_db_uri.replace("postgres://", "postgresql://")
    second_engine = create_engine(second_db_uri, pool_pre_ping=True)
    SecondSession = sessionmaker(bind=second_engine)
    logging.info("✅ Second database connected successfully.")
else:
    logging.info("⚠️ No second database URL found.")

# ------------------------------
# Example usage of second DB:
# session2 = SecondSession()
# result = session2.execute("SELECT * FROM some_table").fetchall()
# session2.close()
# ------------------------------


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
    #passport = db.Column(db.String(100))  # Added field for passport filename

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
    date_needed = db.Column(db.String(50))
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
...

@app.route('/register', methods=['GET', 'POST'])
def register_worker():
    if request.method == 'POST':
        try:
            # Validate required fields
            required_fields = [
                'name', 'phone_number', 'date_of_birth', 'gender',
                'qualifications', 'position', 'national_id', 'nationality',
                'home_address', 'ethnic_group', 'place_of_residence',
                'email', 'date_of_employment', 'bank_account_name', 'guarantor'
            ]
            for field in required_fields:
                if not request.form.get(field):
                    flash(f"{field.replace('_', ' ').title()} is required.", "error")
                    return redirect(url_for('register_worker'))

            # Check for existing email or national_id
            if Worker.query.filter_by(email=request.form['email']).first():
                flash("Email already exists.", "error")
                return redirect(url_for('register_worker'))
            if Worker.query.filter_by(national_id=request.form['national_id']).first():
                flash("National ID already exists.", "error")
                return redirect(url_for('register_worker'))

            # Generate unique worker code
            last_worker = Worker.query.order_by(Worker.id.desc()).first()
            if last_worker and last_worker.worker_code and last_worker.worker_code.startswith("OFCL"):
                last_code = int(last_worker.worker_code[4:])
                new_code = f"OFCL{last_code + 1:03d}"
            else:
                new_code = "OFCL001"

            # Parse numeric inputs safely
            amount_of_salary = float(request.form.get('amount_of_salary', 0) or 0)

            # Handle passport upload
            passport_file = request.files.get('passport')
            passport_filename = None
            if passport_file and passport_file.filename != "":
                passport_filename = f"{uuid.uuid4().hex}_{secure_filename(passport_file.filename)}"
                passport_folder = os.path.join(app.root_path, 'static', 'passports')
                os.makedirs(passport_folder, exist_ok=True)
                passport_path = os.path.join(passport_folder, passport_filename)
                passport_file.save(passport_path)

            # Parse dates safely
            date_of_birth = datetime.strptime(request.form['date_of_birth'], '%Y-%m-%d')
            date_of_employment = datetime.strptime(request.form['date_of_employment'], '%Y-%m-%d')

            # Create Worker record
            new_worker = Worker(
                worker_code=new_code,
                name=request.form['name'],
                phone_number=request.form['phone_number'],
                date_of_birth=date_of_birth,
                gender=request.form['gender'],
                qualifications=request.form['qualifications'],
                position=request.form['position'],
                national_id=request.form['national_id'],
                nationality=request.form['nationality'],
                home_address=request.form['home_address'],
                ethnic_group=request.form['ethnic_group'],
                place_of_residence=request.form['place_of_residence'],
                disability=request.form.get('disability'),
                email=request.form['email'],
                date_of_employment=date_of_employment,
                amount_of_salary=amount_of_salary,
                bank_name=request.form.get('bank_name'),
                bank_account=request.form.get('bank_account'),
                guarantor=request.form.get('guarantor'),
                bank_account_name=request.form.get('bank_account_name'),
                passport=passport_filename
            )

            db.session.add(new_worker)
            db.session.commit()
            flash(f"Worker {new_code} registered successfully.", "success")

            # Redirect with highlight ID
            return redirect(url_for('workers_name', new_id=new_worker.id))

        except ValueError as ve:
            db.session.rollback()
            logging.error(f"Date parsing error: {ve}")
            flash("Invalid date format. Please use YYYY-MM-DD.", "error")
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error registering worker: {e}")
            flash("Error registering worker. Please check your input and try again.", "error")

    return render_template('register_worker.html')


@app.route('/workers')
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


@app.route('/fix_workers_table')
def fix_workers_table():
    try:
        db.session.execute("ALTER TABLE workers ADD COLUMN passport VARCHAR(255);")
        db.session.commit()
        return "Passport column successfully added!"
    except Exception as e:
        return f"Error: {e}"


# Client Form
@app.route('/client_form', methods=['GET', 'POST'])
def client_form():
    products = ["Soya Beans", "Cashew Nut", "Maize", "Rice"]
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        items = request.form.get('items')
        kilograms = int(request.form.get('kilograms') or 0)
        unit_price = float(request.form.get('unit_price') or 0)
        total_amount = kilograms * unit_price
        date_needed = request.form.get('date')
        driver_name = request.form.get('driver_name')
        vehicle_plate_number = request.form.get('vehicle_plate_number')
        bank_name = request.form.get('bank_name')
        account_number = request.form.get('account_number')
        account_bank_name = request.form.get('account_bank_name')
        description = request.form.get('description')
        phone_number = request.form.get('phone_number')

        order = Order(
            name=name,
            email=email,
            items=items,
            kilograms=kilograms,
            unit_price=unit_price,
            total_amount=total_amount,
            date_needed=date_needed,
            driver_name=driver_name,
            vehicle_plate_number=vehicle_plate_number,
            bank_name=bank_name,
            account_number=account_number,
            account_bank_name=account_bank_name,
            description=description,
            phone_number=phone_number
        )
        db.session.add(order)
        db.session.commit()
        return redirect(url_for('orders_overview'))

    return render_template('client_form.html', products=products)

# Orders Overview
@app.route('/orders_overview')
def orders_overview():
    all_orders = Order.query.order_by(Order.created_at.desc()).all()
    soya_orders = [o for o in all_orders if o.items.lower() == 'soya beans']
    cashew_orders = [o for o in all_orders if o.items.lower() == 'cashew nut']
    maize_orders = [o for o in all_orders if o.items.lower() == 'maize']
    rice_orders = [o for o in all_orders if o.items.lower() == 'rice']
    return render_template('orders_overview.html',
                           soya_orders=soya_orders,
                           cashew_orders=cashew_orders,
                           maize_orders=maize_orders,
                           rice_orders=rice_orders)

# Delete order
@app.route('/delete_order/<int:order_id>', methods=['POST'])
def delete_order(order_id):
    order = Order.query.get_or_404(order_id)
    db.session.delete(order)
    db.session.commit()
    return redirect(url_for('orders_overview'))

@app.route('/confirm_order/<int:order_id>', methods=['POST'])
def confirm_order(order_id):
    order = Order.query.get_or_404(order_id)
    order.status = 'Confirmed'
    db.session.commit()
    flash('Order has been confirmed successfully!', 'success')
    return redirect(url_for('orders_overview'))


@app.route('/edit_worker/<int:worker_id>', methods=['GET', 'POST'])
@login_required(role='admin')
def edit_worker(worker_id):
    worker = Worker.query.get_or_404(worker_id)

    if request.method == 'POST':
        try:
            # Update worker fields from form
            worker.name = request.form['name']
            worker.phone_number = request.form['phone_number']
            worker.date_of_birth = datetime.strptime(request.form['date_of_birth'], '%Y-%m-%d')
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
            worker.date_of_employment = datetime.strptime(request.form['date_of_employment'], '%Y-%m-%d')
            worker.amount_of_salary = float(request.form.get('amount_of_salary', 0))
            worker.bank_name = request.form.get('bank_name')
            worker.bank_account = request.form.get('bank_account')
            worker.guarantor = request.form.get('guarantor')
            worker.bank_account_name = request.form.get('bank_account_name')

            db.session.commit()
            flash('Worker details updated successfully.')
            return redirect(url_for('workers_name'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating worker: {e}", "error")

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
@login_required()  # admin or secretary
def attendance():
    # no manual role check needed


    workers = Worker.query.all()
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
    workers = Worker.query.all()
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
def salary_history():
        # Restrict access to admin and secretary only
    if session.get('role') not in ['admin', 'secretary']:
        return redirect(url_for('login'))

    # Base query (join to include worker details)
    salary_query = Salary.query.join(Worker).order_by(Salary.payment_date.desc())

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
        ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
        ADMIN_PASS = os.environ.get('ADMIN_PASS', 'Alayinde001')

        # --- Secretary credentials ---
        SECRETARY_USER = os.environ.get('SECRETARY_USER', 'secretary')
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


# Route to serve favicon.ico from static folder
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )

# Optional: Global error handler for debugging 500s on Render
@app.errorhandler(Exception)
def handle_exception(e):
    import traceback
    return f"<pre>{traceback.format_exc()}</pre>", 500

# Ensure all tables exist (runs both locally and on Render)
with app.app_context():
    db.create_all()
    try:
        upgrade()
        print("✅ Database schema upgraded successfully.")
    except Exception as e:
        print("⚠️ Migration upgrade skipped or failed:", e)

print("🚀 Okoya Co,. Food Staff Manager app is starting...")

# Single run block for local development / Render
if __name__ == '__main__':
    app.debug = True
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
