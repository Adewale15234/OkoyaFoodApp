from extensions import db
from datetime import date
from datetime import datetime, timedelta
from sqlalchemy import func

class Worker(db.Model):
    __tablename__ = 'workers'

    id = db.Column(db.Integer, primary_key=True)
    worker_code = db.Column(db.String(20), unique=True, nullable=True)
    name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    qualifications = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(100), nullable=False)
    national_id = db.Column(db.String(50), nullable=False)
    nationality = db.Column(db.String(50), nullable=False)
    
    # Increased from 200 to 255 to fit longer addresses
    home_address = db.Column(db.String(255), nullable=False)
    
    ethnic_group = db.Column(db.String(50), nullable=False)
    
    # Increased from 100 to 255 to fit Cloudinary URLs
    place_of_residence = db.Column(db.String(255), nullable=False)
    
    disability = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(100), nullable=False)
    date_of_employment = db.Column(db.Date, nullable=False)
    
    # Keep for legacy, but we’ll use daily_rate for salary calc
    amount_of_salary = db.Column(db.Float, nullable=False)
    daily_rate = db.Column(db.Float, nullable=False, default=0.0)
    
    bank_name = db.Column(db.String(100), nullable=True)
    bank_account = db.Column(db.String(50), nullable=True)
    bank_account_name = db.Column(db.String(100), nullable=False)
    guarantor = db.Column(db.String(100), nullable=False)
    
    # Increased from 100 to 255 to fit Cloudinary URLs like https://res.cloudinary.com/...
    passport = db.Column(db.String(255), nullable=True)

    department = db.Column(db.String(50), nullable=True)

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # =========================
    # STATUS FIELDS
    # =========================
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    status_type = db.Column(db.String(30), nullable=True)
    status_reason = db.Column(db.Text, nullable=True)
    status_date = db.Column(db.DateTime, nullable=True)
    status_letter = db.Column(db.Text, nullable=True)
    warning_count = db.Column(db.Integer, default=0)
    last_action_by = db.Column(db.String(100), nullable=True)
    last_action_date = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    # =========================
    # RELATIONSHIPS
    # =========================
    attendance_records = db.relationship(
        'Attendance',
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy='dynamic'
    )

    salaries = db.relationship(
        'Salary',
        backref='worker',
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy='dynamic'
    )

    email_logs = db.relationship(
        'EmailLog',
        backref=db.backref('worker_ref', lazy=True),
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    def __repr__(self):
        return f'<Worker {self.worker_code} - {self.name}>'

    def get_month_attendance(self, month_str):
        """Get attendance count for a specific month. month_str = '2025-10'"""
        year, month = map(int, month_str.split('-'))
        return self.attendance_records.filter(
            func.extract('year', Attendance.date) == year,
            func.extract('month', Attendance.date) == month,
            Attendance.status.in_(['present', 'Present', 'P'])
        ).count()

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

    def __repr__(self):
        return f'<EmailLog {self.email} - {self.status}>'

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

    def __repr__(self):
        return f'<Order {self.id} - {self.name}>'

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
        default=date.today,
        index=True
    )
    
    status = db.Column(db.String(20), nullable=False)  # Present, Absent, Late, Leave
    
    time_in = db.Column(db.Time, nullable=True)
    time_out = db.Column(db.Time, nullable=True)
    notes = db.Column(db.String(100), nullable=True)
    
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now()
    )

    # Relationship
    worker = db.relationship('Worker', backref='attendances', lazy='joined')

    # Prevent duplicate attendance for same worker on same date
    __table_args__ = (
        db.UniqueConstraint('worker_id', 'date', name='_worker_date_uc'),
    )

    def __repr__(self):
        return f'<Attendance {self.worker_id} - {self.date} - {self.status}>'

    @property
    def duration(self):
        """Calculate duration between time_in and time_out"""
        if self.time_in and self.time_out:
            dt_in = datetime.combine(date.today(), self.time_in)
            dt_out = datetime.combine(date.today(), self.time_out)
            
            # Handle overnight shifts
            if dt_out < dt_in:
                dt_out += timedelta(days=1)
            
            diff = dt_out - dt_in
            hours = diff.total_seconds() / 3600
            return round(hours, 2)
        return None

class Salary(db.Model):
    __tablename__ = 'salary'

    id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(
        db.Integer,
        db.ForeignKey('workers.id', ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # New fields for monthly payroll system
    month = db.Column(db.String(7), nullable=False, index=True)  # Format: "2025-10"
    
    total_days_present = db.Column(db.Integer, nullable=False, default=0)
    daily_rate = db.Column(db.Float, nullable=False, default=0.0)
    deductions = db.Column(db.Float, nullable=False, default=0.0)
    gross_salary = db.Column(db.Float, nullable=False, default=0.0)
    net_salary = db.Column(db.Float, nullable=False, default=0.0)
    amount = db.Column(db.Float, nullable=False, default=0.0)  # Keep for backward compatibility
    is_processed = db.Column(db.Boolean, nullable=False, default=False)
    
    # Bank details cached at time of payroll
    bank_name = db.Column(db.String(100), nullable=True)
    bank_account = db.Column(db.String(50), nullable=True)
    bank_account_name = db.Column(db.String(100), nullable=True)
    
    payment_date = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    # Unique constraint: one salary record per worker per month
    __table_args__ = (
        db.UniqueConstraint('worker_id', 'month', name='uq_worker_month_salary'),
    )

    def calculate(self):
        """Recalculate gross and net salary"""
        self.gross_salary = float(self.total_days_present) * float(self.daily_rate)
        self.net_salary = float(self.gross_salary) - float(self.deductions)
        self.amount = self.net_salary  # Keep backward compatibility
        return self

    def auto_fill_from_worker(self):
        """Fill salary record with worker's current data"""
        self.daily_rate = float(self.worker.daily_rate or self.worker.amount_of_salary or 0)
        self.bank_name = self.worker.bank_name
        self.bank_account = self.worker.bank_account
        self.bank_account_name = self.worker.bank_account_name
        return self

    def __repr__(self):
        return f'<Salary {self.worker_id} - {self.month} - ₦{self.net_salary}>'

class PayrollLock(db.Model):
    __tablename__ = 'payroll_lock'

    id = db.Column(db.Integer, primary_key=True)
    month = db.Column(db.String(7), unique=True, nullable=False)  # "2025-10"
    locked_by = db.Column(db.String(100), nullable=True)
    locked_at = db.Column(db.DateTime, default=datetime.utcnow)
    note = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<PayrollLock {self.month}>'

class AuditLog(db.Model):
    __tablename__ = 'audit_log'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True)
    user_name = db.Column(db.String(100), nullable=True)
    action = db.Column(db.String(50), nullable=False)  # created, updated, processed, deleted
    table_name = db.Column(db.String(50), nullable=False)
    record_id = db.Column(db.Integer, nullable=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('workers.id'), nullable=True)
    worker_name = db.Column(db.String(100), nullable=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    worker = db.relationship('Worker', backref='audit_logs')

    def __repr__(self):
        return f'<AuditLog {self.action} - {self.table_name} - {self.record_id}>'