from extensions import db
from datetime import datetime
from sqlalchemy import func

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