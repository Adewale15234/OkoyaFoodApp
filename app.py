from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
import os
import logging

# Logging setup
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# Use environment variable for secret key in production
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key')

# Database setup for Render: use DATABASE_URL if provided, else fallback to local SQLite
if os.environ.get("DATABASE_URL"):
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ["DATABASE_URL"].replace("postgres://", "postgresql://")
else:
    db_path = os.path.join(os.getcwd(), 'database', 'site.db')
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
    
    attendance_records = db.relationship('Attendance', backref='worker', lazy=True, cascade="all, delete-orphan")
    salary_records = db.relationship('Salary', backref='worker', lazy=True, cascade="all, delete-orphan")

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('workers.id'), nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    status = db.Column(db.String(10), nullable=False)

class Salary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('workers.id'), nullable=False)
    total_days_present = db.Column(db.Integer, nullable=False)
    daily_rate = db.Column(db.Float, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())

# Hardcoded credentials (Not secure! Replace with real auth for production)
USERNAME = os.environ.get('ADMIN_USERNAME', 'Admin')
PASSWORD = os.environ.get('ADMIN_PASSWORD', 'Alayinde001')

# Routes
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == USERNAME and password == PASSWORD:
            session['admin'] = username
            session.permanent = True
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid username or password.'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('admin', None)
    flash("You have been logged out.")
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'admin' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/register', methods=['GET', 'POST'])
def register_worker():
    if 'admin' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            new_worker = Worker(
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
            )
            db.session.add(new_worker)
            db.session.commit()
            flash("Worker registered successfully.")
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

@app.route('/delete_worker/<int:worker_id>', methods=['POST'])
def delete_worker(worker_id):
    if 'admin' not in session:
        return redirect(url_for('login'))
    worker = Worker.query.get_or_404(worker_id)
    db.session.delete(worker)
    db.session.commit()
    flash('Worker deleted successfully.')
    return redirect(url_for('workers_name'))

@app.route('/attendance', methods=['GET', 'POST'])
def attendance():
    if 'admin' not in session:
        return redirect(url_for('login'))
    workers = Worker.query.all()
    if request.method == 'POST':
        worker_id = request.form.get('worker_id')
        status = request.form.get('attendance_status')
        if worker_id and status:
            attendance = Attendance(
                worker_id=worker_id,
                status=status,
                date=datetime.now()
            )
            db.session.add(attendance)
            db.session.commit()
            flash('Attendance marked successfully.')
            return redirect(url_for('attendance'))
    return render_template('attendance.html', workers=workers)

@app.route('/salary', methods=['GET', 'POST'])
def salary():
    if 'admin' not in session:
        return redirect(url_for('login'))
    workers = Worker.query.all()
    salary_data = []
    for worker in workers:
        total_days_present = Attendance.query.filter_by(worker_id=worker.id, status="Present").count()
        salary_data.append({
            'id': worker.id,
            'name': worker.name,
            'worker_code': worker.worker_code,
            'total_days_present': total_days_present
        })
    if request.method == 'POST':
        worker_id = request.form.get('worker_id')
        daily_rate = request.form.get('daily_rate')
        if worker_id and daily_rate:
            worker = Worker.query.get(int(worker_id))
            total_days_present = Attendance.query.filter_by(worker_id=worker.id, status="Present").count()
            amount = total_days_present * float(daily_rate)
            # Save salary record
            new_salary = Salary(
                worker_id=worker.id,
                total_days_present=total_days_present,
                daily_rate=float(daily_rate),
                amount=amount
            )
            db.session.add(new_salary)
            db.session.commit()
            flash(f"Salary recorded for {worker.name}")
            return redirect(url_for('salary_history'))
        else:
            flash("Missing information for salary record.", "error")
    return render_template('salary.html', salary_data=salary_data)

@app.route('/attendance_history')
def attendance_history():
    if 'admin' not in session:
        return redirect(url_for('login'))
    records = Attendance.query.order_by(Attendance.date.desc()).all()
    return render_template('attendance_history.html', attendance_records=records)

@app.route('/salary_history')
def salary_history():
    if 'admin' not in session:
        return redirect(url_for('login'))
    salary_records = Salary.query.order_by(Salary.payment_date.desc()).all()
    return render_template('salary_history.html', salary_records=salary_records)

# Function to ensure tables are created — works both locally and on Render
def create_tables():
    with app.app_context():
        db.create_all()

# Call it globally (for Render)
create_tables()

# Route to serve favicon.ico from static folder
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

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