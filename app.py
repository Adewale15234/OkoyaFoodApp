from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os
import logging
logging.basicConfig(level=logging.DEBUG)

# ✅ App setup
app = Flask(__name__)
app.secret_key = 'your-secret-key'

# ✅ Database setup
db_path = os.path.join(os.getcwd(), 'database', 'site.db')
os.makedirs(os.path.dirname(db_path), exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# ✅ Models
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

    attendance_records = db.relationship('Attendance', backref='worker', lazy=True, cascade="all, delete")
    salary_records = db.relationship('Salary', backref='worker', lazy=True, cascade="all, delete")

    def __repr__(self):
        return f"<Worker {self.name}>"

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

# You should set ADMIN_PASSWORD_HASH in Render environment variables!
admin_password_hash = os.getenv('ADMIN_PASSWORD_HASH') or generate_password_hash('Alayinde001', method='pbkdf2:sha256')

@app.route('/')
def home():
    return redirect(url_for('dashboard' if 'admin' in session else 'login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and check_password_hash(admin_password_hash, password):
            session['admin'] = username
            session.permanent = True
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid credentials.'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'admin' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/register_worker', methods=['GET', 'POST'])
def register_worker():
    if request.method == 'POST':
        try:
            new_worker = Worker(
                name=request.form['name'],
                phone_number=request.form['phone_number'],
                date_of_birth=datetime.strptime(request.form['date_of_birth'], "%Y-%m-%d"),
                gender=request.form['gender'],
                qualifications=request.form['qualifications'],
                position=request.form['position'],
                national_id=request.form['national_id'],
                nationality=request.form['nationality'],
                home_address=request.form['home_address'],
                ethnic_group=request.form['ethnic_group'],
                place_of_residence=request.form['place_of_residence'],
                disability=request.form.get('disability', ''),
                email=request.form['email'],
                date_of_employment=datetime.strptime(request.form['date_of_employment'], "%Y-%m-%d")
            )
            db.session.add(new_worker)
            db.session.commit()

            new_worker.worker_code = f"WK{new_worker.id:03d}"
            db.session.commit()

            flash('Worker registered successfully!')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            return f"Error registering worker: {e}", 500

    return render_template('register_worker.html')

@app.route('/attendance', methods=['GET', 'POST'])
def attendance():
    if not session.get('admin'):
        return redirect(url_for('login'))
    workers = Worker.query.order_by(Worker.name).all()
    if request.method == 'POST':
        try:
            worker_id = int(request.form['worker_id'])
            status = request.form['attendance_status']
            rec = Attendance(
                worker_id=worker_id,
                status=status
            )
            db.session.add(rec)
            db.session.commit()
            flash('Attendance recorded!')
        except Exception as e:
            db.session.rollback()
            flash(f"Error recording attendance: {e}")
        return redirect(url_for('attendance'))
    return render_template('attendance.html', workers=workers)

@app.route('/attendance_history')
def attendance_history():
    if not session.get('admin'):
        return redirect(url_for('login'))

    records = Attendance.query.join(Worker).order_by(Attendance.date.desc()).all()
    month = request.args.get('month')
    if month:
        records = [r for r in records if r.date.strftime('%Y-%m') == month]
    return render_template('attendance_history.html', attendance_records=records)

@app.route('/salary', methods=['GET', 'POST'])
def salary():
    if not session.get('admin'):
        return redirect(url_for('login'))

    workers = Worker.query.all()
    salary_data = []

    if request.method == 'POST':
        worker_id = int(request.form['worker_id'])
        daily_rate = float(request.form['daily_rate'])

        attendance_count = Attendance.query.filter_by(worker_id=worker_id).count()
        amount = daily_rate * attendance_count

        salary_record = Salary(
            worker_id=worker_id,
            total_days_present=attendance_count,
            daily_rate=daily_rate,
            amount=amount
        )
        db.session.add(salary_record)
        db.session.commit()

        return redirect(url_for('salary'))

    for worker in workers:
        attendance_count = Attendance.query.filter_by(worker_id=worker.id).count()
        salary_data.append({
            'id': worker.id,
            'name': worker.name,
            'total_days_present': attendance_count,
            'total_salary': None
        })

    return render_template('salary.html', salary_data=salary_data)

@app.route('/salary_history')
def salary_history():
    if not session.get('admin'):
        return redirect(url_for('login'))

    salary_records = Salary.query.all()
    return render_template('salary_history.html', salary_records=salary_records)

@app.route('/print_attendance_pdf')
def print_attendance_pdf():
    if not session.get('admin'):
        return redirect(url_for('login'))
    return '<h1>PDF export for attendance not yet implemented</h1>'

@app.route('/print_salary_history_pdf')
def print_salary_history_pdf():
    if not session.get('admin'):
        return redirect(url_for('login'))
    return '<h1>PDF export for salary history not yet implemented</h1>'

@app.route('/workers_name')
def workers_name():
    if not session.get('admin'):
        return redirect(url_for('login'))

    workers = Worker.query.order_by(Worker.name).all()
    return render_template('workers_name.html', workers=workers)

@app.route('/delete_worker/<int:worker_id>', methods=['POST'])
def delete_worker(worker_id):
    if not session.get('admin'):
        return redirect(url_for('login'))

    worker = Worker.query.get_or_404(worker_id)
    try:
        db.session.delete(worker)
        db.session.commit()
        flash(f"Deleted {worker.name} successfully.")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting worker: {e}")
    return redirect(url_for('workers_name'))

# ✅ Entry point
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))