from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, upgrade  # ✅ 'upgrade' is now imported
from datetime import datetime, date
from calendar import monthrange   # ✅ Add this line
from sqlalchemy import extract
import os
import logging

# Secretary entrance (hardcoded for now)
SECRETARY_PASSWORD = os.environ.get('SECRETARY_PASSWORD', 'secret123')

# Logging setup
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# Use environment variable for secret key in production
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key')

# Database setup for Render: use DATABASE_URL if provided, else fallback to local SQLite
if os.environ.get("DATABASE_URL"):
    uri = os.environ["DATABASE_URL"].replace("postgres://", "postgresql://")
    app.config['SQLALCHEMY_DATABASE_URI'] = uri
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "pool_pre_ping": True,   # ✅ checks connection before using it
        "pool_recycle": 300,     # ✅ recycle connections every 5 mins
    }
else:
    db_path = os.path.join('/tmp', 'site.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Database models
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
    disability = db.Column(db.String(100))
    email = db.Column(db.String(100), nullable=False)
    date_of_employment = db.Column(db.Date, nullable=False)

    amount_of_salary = db.Column(db.Float, nullable=False)
    bank_name = db.Column(db.String(100), nullable=True)
    bank_account = db.Column(db.String(50), nullable=True)
    bank_account_name = db.Column(db.String(100), nullable=False)
    guarantor = db.Column(db.String(100), nullable=False)

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
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    name = db.Column(db.String(150))
    email = db.Column(db.String(150))
    items = db.Column(db.String(50))
    tonnage = db.Column(db.Float, nullable=True)
    number_of_bags = db.Column(db.Integer, nullable=True)
    kilograms = db.Column(db.Float, nullable=True)
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
    if 'admin' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            # Generate worker code
            last_worker = Worker.query.order_by(Worker.id.desc()).first()
            if last_worker and last_worker.worker_code and last_worker.worker_code.startswith("WKD"):
                last_code = int(last_worker.worker_code[3:])
                new_code = f"WKD{last_code + 1:03d}"
            else:
                new_code = "WKD001"

            # Safely parse numeric inputs
            amount_of_salary = float(request.form.get('amount_of_salary', '0') or 0)

            new_worker = Worker(
                worker_code=new_code,
                name=request.form['name'],
                phone_number=request.form['phone_number'],
                date_of_birth=datetime.strptime(request.form['date_of_birth'], '%Y-%m-%d'),
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
                date_of_employment=datetime.strptime(request.form['date_of_employment'], '%Y-%m-%d'),

                amount_of_salary=amount_of_salary,
                bank_name=request.form.get('bank_name'),
                bank_account=request.form.get('bank_account'),
                guarantor=request.form.get('guarantor'),
                bank_account_name=request.form.get('bank_account_name')
            )

            db.session.add(new_worker)
            db.session.commit()

            flash(f"Worker {new_code} registered successfully.")
            return redirect(url_for('workers_name'))
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error registering worker: {e}")
            flash("Error registering worker. Please check your input and try again.")
    return render_template('register_worker.html')

@app.route('/workers')
def workers_name():
    if 'admin' not in session:
        return redirect(url_for('login'))
    workers = Worker.query.all()
    return render_template('workers_name.html', workers=workers)
@app.route('/client_form', methods=['GET', 'POST'])
def client_form():
    products = ["CASHEW NUT", "MAIZE", "SOYA BEANS", "RICE"]

    if request.method == 'POST':
        try:
            data = request.form
            order = Order(
                name=data.get('name', '').strip(),
                email=data.get('email', '').strip(),
                date_needed=data.get('date', '').strip(),
                bank_name=data.get('bank_name', '').strip(),
                items=data.get('items', '').strip(),
                description=data.get('description', '').strip(),
                tonnage=float(data.get('tonnage')) if data.get('tonnage') else None,
                number_of_bags=int(data.get('number_of_bags')) if data.get('number_of_bags') else None,
                kilograms=float(data.get('kilograms')) if data.get('kilograms') else None,
                unit_price=float(data.get('unit_price')) if data.get('unit_price') else None,
                total_amount=float(data.get('total_amount')) if data.get('total_amount') else None,
                driver_name=data.get('driver_name', '').strip(),
                vehicle_plate_number=data.get('vehicle_plate_number', '').strip(),
                phone_number=data.get('phone_number', '').strip(),
                account_number=data.get('account_number', '').strip(),
                account_bank_name=data.get('account_bank_name', '').strip()
            )
            db.session.add(order)
            db.session.commit()
            flash("Client order submitted successfully!", "success")
            return redirect(url_for('client_form'))
        except Exception:
            db.session.rollback()
            flash("Error submitting order. Please check your input.", "error")

    return render_template('client_form.html', products=products)


@app.route('/orders_overview')
def orders_overview():
    if 'admin' not in session:
        flash("Please login as Admin to continue.", "danger")
        return redirect(url_for('login'))

    # Fetch orders grouped by product type
    soya_orders = Order.query.filter(Order.items == "SOYA BEANS").all()
    cashew_orders = Order.query.filter(Order.items == "CASHEW NUT").all()
    maize_orders = Order.query.filter(Order.items == "MAIZE").all()
    rice_orders = Order.query.filter(Order.items == "RICE").all()

    return render_template('orders_overview.html',
                           soya_orders=soya_orders,
                           cashew_orders=cashew_orders,
                           maize_orders=maize_orders,
                           rice_orders=rice_orders)


@app.route('/confirm_order/<int:order_id>', methods=['POST'])
def confirm_order(order_id):
    if 'admin' not in session:
        flash("Please login as Admin to continue.", "danger")
        return redirect(url_for('login'))

    order = Order.query.get_or_404(order_id)
    order.status = "Confirmed"
    db.session.commit()
    flash(f"Order {order.id} marked as Confirmed!", "success")
    return redirect(request.referrer)  # redirect back to the same page


@app.route('/edit_worker/<int:worker_id>', methods=['GET', 'POST'])
def edit_worker(worker_id):
    if 'admin' not in session:
        return redirect(url_for('login'))

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
def delete_worker(worker_id):
    if 'admin' not in session:
        return redirect(url_for('login'))
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
def attendance():
    if 'admin' not in session and 'secretary' not in session:
        return redirect(url_for('login'))

    workers = Worker.query.all()
    secretary = 'secretary' in session  # ✅ detect if secretary

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
def salary():
    if 'admin' not in session and 'secretary' not in session:
        return redirect(url_for('login'))

    workers = Worker.query.all()
    today = datetime.today()
    current_year = today.year
    current_month = today.month
    total_days_in_month = monthrange(current_year, current_month)[1]

    # Safety: monthrange should never return 0, but guard anyway
    if total_days_in_month == 0:
        total_days_in_month = 1

    salary_data = []
    for worker in workers:
        # Count days present this month
        total_days_present = Attendance.query.filter(
            Attendance.worker_id == worker.id,
            Attendance.status == "Present",
            db.extract('year', Attendance.date) == current_year,
            db.extract('month', Attendance.date) == current_month
        ).count()

        # Calculate salary proportionally
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
                db.extract('year', Attendance.date) == current_year,
                db.extract('month', Attendance.date) == current_month
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
def attendance_history():
    if 'admin' not in session and 'secretary' not in session:
        return redirect(url_for('login'))

    selected_month = request.args.get('month')

    # Query all attendance records
    attendance_records = Attendance.query.order_by(Attendance.date.desc()).all()

    # Generate available months dynamically
    available_months = sorted(
        list(set(record.date.strftime("%B %Y") for record in attendance_records)),
        reverse=True
    )

    # Filter by selected month using SQLAlchemy extract
    if selected_month:
        month_dt = datetime.strptime(selected_month, "%B %Y")
        attendance_records = Attendance.query.filter(
            extract('month', Attendance.date) == month_dt.month,
            extract('year', Attendance.date) == month_dt.year
        ).order_by(Attendance.date.desc()).all()

    return render_template(
        "attendance_history.html",
        attendance_records=attendance_records,
        available_months=available_months,
        selected_month=selected_month,
        now=datetime.now()
    )


@app.route('/salary_history')
def salary_history():
    if 'admin' not in session and 'secretary' not in session:
        return redirect(url_for('login'))

    selected_month = request.args.get('month')

    query = Salary.query

    # Filter by selected month if provided
    if selected_month:
        month_dt = datetime.strptime(selected_month, "%B %Y")
        query = query.filter(
            extract('month', Salary.payment_date) == month_dt.month,
            extract('year', Salary.payment_date) == month_dt.year
        )

    # Order by latest payment
    salary_records = query.order_by(Salary.payment_date.desc()).all()

    # Generate available months dynamically
    available_months = sorted(
        list(set(record.payment_date.strftime("%B %Y") for record in Salary.query.all())),
        reverse=True
    )

    # Attach total_days_present for display
    for record in salary_records:
        if selected_month:
            month_dt = datetime.strptime(selected_month, "%B %Y")
            record.total_days_present = Attendance.query.filter(
                Attendance.worker_id == record.worker_id,
                Attendance.status == "Present",
                extract('month', Attendance.date) == month_dt.month,
                extract('year', Attendance.date) == month_dt.year
            ).count()
        else:
            record.total_days_present = Attendance.query.filter_by(
                worker_id=record.worker_id, status="Present"
            ).count()

    return render_template(
        'salary_history.html',
        salary_records=salary_records,
        available_months=available_months,
        selected_month=selected_month,
        now=datetime.now()
    )


# ===============================
# LOGIN ROUTES (Admin & Secretary)
# ===============================

@app.route('/')
def choose_login():
    """Landing page: choose between Admin or Secretary login"""
    return render_template('choose_login.html')


# --- Admin login ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        USERNAME = 'admin'
        PASSWORD = 'Alayinde001'

        if username == USERNAME and password == PASSWORD:
            session['admin'] = username
            session.permanent = True
            flash("Welcome Admin!", "success")
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid username or password.'

    return render_template('login.html', error=error)


# --- Secretary login ---
@app.route('/secretary_login', methods=['GET', 'POST'])
def secretary_login():
    error = None
    if request.method == 'POST':
        password = request.form.get('password')

        SECRETARY_PASSWORD = os.environ.get('SECRETARY_PASSWORD', 'secret123')

        if password == SECRETARY_PASSWORD:
            session['secretary'] = True
            session.permanent = True
            flash("Welcome Secretary!", "success")
            return redirect(url_for('secretary_dashboard'))
        else:
            error = "Invalid entrance password."

    return render_template('secretary_login.html', error=error)


    # --- Admin Dashboard ---
@app.route('/dashboard')
def dashboard():
    if 'admin' not in session:
        flash("Please login as Admin to continue.", "danger")
        return redirect(url_for('login'))
    # ... your existing dashboard logic ...
    return render_template('dashboard.html')


# --- Secretary Dashboard ---
@app.route('/secretary_dashboard')
def secretary_dashboard():
    if 'secretary' not in session:
        flash("Please login as Secretary to continue.", "danger")
        return redirect(url_for('secretary_login'))
    # ... your existing secretary dashboard logic ...
    return render_template('secretary_dashboard.html')


@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for('choose_login'))


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


# For local development
if __name__ == '__main__':
    app.debug = True
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
