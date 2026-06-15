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
    
    home_address = db.Column(db.String(255), nullable=False)
    ethnic_group = db.Column(db.String(50), nullable=False)
    place_of_residence = db.Column(db.String(255), nullable=False)
    
    disability = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(100), nullable=False)
    date_of_employment = db.Column(db.Date, nullable=False)
    
    amount_of_salary = db.Column(db.Float, nullable=False)
    daily_rate = db.Column(db.Float, nullable=False, default=0.0)
    
    bank_name = db.Column(db.String(100), nullable=True)
    bank_account = db.Column(db.String(50), nullable=True)
    bank_account_name = db.Column(db.String(100), nullable=False)
    guarantor = db.Column(db.String(100), nullable=False)
    
    passport = db.Column(db.String(255), nullable=True)
    department = db.Column(db.String(50), nullable=True)

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    status_type = db.Column(db.String(30), nullable=True)
    status_reason = db.Column(db.Text, nullable=True)
    status_date = db.Column(db.DateTime, nullable=True)
    status_letter = db.Column(db.Text, nullable=True)
    warning_count = db.Column(db.Integer, default=0)
    last_action_by = db.Column(db.String(100), nullable=True)
    last_action_date = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    attendance_records = db.relationship(
        'Attendance',
        back_populates='worker',  # <-- YOU MISSED THIS LINE
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy='dynamic'
    )

    salaries = db.relationship(
        'Salary',
        back_populates='worker',
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
    
    status = db.Column(db.String(20), nullable=False)
    
    time_in = db.Column(db.Time, nullable=True)
    time_out = db.Column(db.Time, nullable=True)
    notes = db.Column(db.String(100), nullable=True)
    
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now()
    )

    worker = db.relationship(
        'Worker', 
        back_populates='attendance_records',  # <-- USE back_populates INSTEAD OF backref
        lazy='joined'
    )

    __table_args__ = (
        db.UniqueConstraint('worker_id', 'date', name='_worker_date_uc'),
    )

    def __repr__(self):
        return f'<Attendance {self.worker_id} - {self.date} - {self.status}>'

    @property
    def duration(self):
        if self.time_in and self.time_out:
            dt_in = datetime.combine(date.today(), self.time_in)
            dt_out = datetime.combine(date.today(), self.time_out)
            
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
    
    worker = db.relationship('Worker', back_populates='salaries')
    
    month = db.Column(db.String(7), nullable=False, index=True)
    
    total_days_present = db.Column(db.Integer, nullable=False, default=0)
    daily_rate = db.Column(db.Float, nullable=False, default=0.0)
    deductions = db.Column(db.Float, nullable=False, default=0.0)
    gross_salary = db.Column(db.Float, nullable=False, default=0.0)
    net_salary = db.Column(db.Float, nullable=False, default=0.0)
    amount = db.Column(db.Float, nullable=False, default=0.0)
    is_processed = db.Column(db.Boolean, nullable=False, default=False)
    
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

    __table_args__ = (
        db.UniqueConstraint('worker_id', 'month', name='uq_worker_month_salary'),
    )

    def calculate(self):
        days = float(self.total_days_present or 0)
        rate = float(self.daily_rate or 0)
        ded = float(self.deductions or 0)
        
        self.gross_salary = days * rate
        self.net_salary = self.gross_salary - ded
        self.amount = self.net_salary
        return self

    def auto_fill_from_worker(self):
        if not self.worker:
            return self
            
        if self.worker.daily_rate and float(self.worker.daily_rate) > 0:
            self.daily_rate = float(self.worker.daily_rate)
        elif self.worker.amount_of_salary and float(self.worker.amount_of_salary) > 0:
            self.daily_rate = float(self.worker.amount_of_salary) / 30.0
        else:
            self.daily_rate = 0.0
            
        self.bank_name = self.worker.bank_name
        self.bank_account = self.worker.bank_account
        self.bank_account_name = self.worker.bank_account_name
        return self

    def __repr__(self):
        return f'<Salary {self.worker_id} - {self.month} - ₦{self.net_salary}>'

class PayrollLock(db.Model):
    __tablename__ = 'payroll_lock'

    id = db.Column(db.Integer, primary_key=True)
    month = db.Column(db.String(7), unique=True, nullable=False)
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
    action = db.Column(db.String(50), nullable=False)
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

class Material(db.Model):
    __tablename__ = 'materials'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    unit = db.Column(db.String(20), nullable=False)
    category = db.Column(db.String(50), default='General')
    low_stock_threshold = db.Column(db.Integer, default=10)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    transactions = db.relationship('MaterialTransaction', backref='material', lazy='dynamic', cascade="all, delete-orphan")

    @property
    def total_in(self):
        return db.session.query(func.coalesce(func.sum(MaterialTransaction.quantity), 0)).filter(
            MaterialTransaction.material_id == self.id,
            MaterialTransaction.type == 'stock_in',
            MaterialTransaction.is_verified == True
        ).scalar()

    @property
    def total_out(self):
        return db.session.query(func.coalesce(func.sum(MaterialTransaction.quantity), 0)).filter(
            MaterialTransaction.material_id == self.id,
            MaterialTransaction.type.in_(['usage', 'sale']),
            MaterialTransaction.is_verified == True
        ).scalar()

    @property
    def remaining(self):
        return self.total_in - self.total_out

    @property
    def is_low_stock(self):
        return self.remaining <= self.low_stock_threshold

    def __repr__(self):
        return f'<Material {self.name}: {self.remaining}{self.unit}>'

# DELETE THE FIRST MaterialTransaction CLASS ABOVE. KEEP ONLY THIS ONE.
class MaterialTransaction(db.Model):
    __tablename__ = 'material_transactions'
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey('materials.id', ondelete="CASCADE"), nullable=False, index=True)
    type = db.Column(db.String(20), nullable=False) # stock_in, usage, sale
    quantity = db.Column(db.Float, nullable=False)
    unit_price = db.Column(db.Float, nullable=True)
    total_value = db.Column(db.Float, nullable=True)
    purpose = db.Column(db.String(200))
    client_supplier = db.Column(db.String(100))
    transaction_date = db.Column(db.Date, default=date.today, index=True)
    recorded_by_name = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Verification fields - REQUIRED BY YOUR ROUTES
    is_verified = db.Column(db.Boolean, default=False)
    verified_by_id = db.Column(db.Integer)
    verified_at = db.Column(db.DateTime)
    is_edited = db.Column(db.Boolean, default=False)
    edited_at = db.Column(db.DateTime)

    def __repr__(self):
        return f'<MaterialTxn {self.type} {self.quantity}>'