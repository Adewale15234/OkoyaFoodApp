from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, jsonify
from extensions import db
from models import Worker, Attendance, Salary, PayrollLock, AuditLog
from utils import login_required
from datetime import datetime
from calendar import monthrange
from sqlalchemy import extract, func
import logging

salary_bp = Blueprint('salary', __name__, url_prefix='/salary')

@salary_bp.route('/', methods=['GET', 'POST'])
@login_required(role='admin')
def salary():
    """Main salary management page with monthly period support"""
    period = request.args.get('period', datetime.now().strftime('%Y-%m'))
    year, month = map(int, period.split('-'))

    days_in_month = monthrange(year, month)[1]
    if days_in_month < 1:
        days_in_month = 1

    is_locked = PayrollLock.query.filter_by(month=period).first()

    # Get or auto-create salary records for this period
    salary_data = Salary.query.filter_by(month=period).all()

    if not salary_data:
        workers = Worker.query.filter_by(is_active=True).all()
        for w in workers:
            total_days_present = w.get_month_attendance(period)

            monthly_salary = float(w.amount_of_salary or 0)
            auto_daily_rate = round(monthly_salary / days_in_month, 2) if days_in_month > 0 else 0

            s = Salary(
                worker_id=w.id,
                month=period,
                total_days_present=total_days_present,
                daily_rate=auto_daily_rate,
                deductions=0
            )
            s.auto_fill_from_worker()
            s.calculate()
            db.session.add(s)
        db.session.commit()
        salary_data = Salary.query.filter_by(month=period).all()

    # Attach extra display values for template
    for s in salary_data:
        s.days_in_month = days_in_month
        s.present_days = s.total_days_present
        s.attendance_percent = round((s.total_days_present / days_in_month) * 100, 2) if days_in_month > 0 else 0
        s.daily_rate_display = s.daily_rate
        s.calculated_salary = s.net_salary
        s.worker_name = s.worker.name if s.worker else 'Unknown'
        s.worker_department = s.worker.department if s.worker else 'N/A'

    total_payroll = sum(s.net_salary for s in salary_data)

    # Get filter options
    banks = db.session.query(Worker.bank_name).distinct().filter(Worker.bank_name.isnot(None), Worker.bank_name!= '').all()
    banks = [b[0] for b in banks]

    departments = db.session.query(Worker.department).distinct().filter(Worker.department.isnot(None), Worker.department!= '').all()
    departments = [d[0] for d in departments]

    # Audit logs for this period
    audit_logs = AuditLog.query.filter(AuditLog.details.like(f'%{period}%')).order_by(AuditLog.created_at.desc()).limit(50).all()

    if request.method == 'POST':
        try:
            worker_id = int(request.form.get('worker_id'))
            worker = Worker.query.get(worker_id)

            if not worker:
                flash("Worker not found.", "error")
                return redirect(url_for('salary.salary', period=period))

            if is_locked:
                flash("This period is locked. Unlock it first to make changes.", "error")
                return redirect(url_for('salary.salary', period=period))

            # Get or create salary record
            salary_record = Salary.query.filter_by(worker_id=worker_id, month=period).first()

            if not salary_record:
                monthly_salary = float(worker.amount_of_salary or 0)
                auto_daily_rate = round(monthly_salary / days_in_month, 2) if days_in_month > 0 else 0
                salary_record = Salary(
                    worker_id=worker_id,
                    month=period,
                    total_days_present=0,
                    daily_rate=auto_daily_rate,
                    deductions=0
                )
                salary_record.auto_fill_from_worker()

            # Update fields from form/edit
            total_days_present = int(request.form.get('total_days_present', worker.get_month_attendance(period)))
            daily_rate = float(request.form.get('daily_rate', salary_record.daily_rate))
            deductions = float(request.form.get('deductions', salary_record.deductions))

            salary_record.total_days_present = total_days_present
            salary_record.daily_rate = daily_rate
            salary_record.deductions = deductions

            # Mark as processed when saved
            salary_record.is_processed = True
            salary_record.calculate()
            db.session.add(salary_record)

            # Audit log
            audit = AuditLog(
                user_name=session.get('username', 'Admin'),
                action='processed',
                table_name='salary',
                record_id=salary_record.id,
                worker_id=worker.id,
                worker_name=worker.name,
                details=f'Processed salary for {period}'
            )
            db.session.add(audit)
            db.session.commit()

            flash(f"Salary processed successfully for {worker.name}.", "success")
            return redirect(url_for('salary.salary', period=period))

        except Exception as e:
            db.session.rollback()
            logging.error(f"Salary error: {e}")
            flash("Error recording salary. Try again.", "error")
            return redirect(url_for('salary.salary', period=period))

    return render_template(
        'salary.html',
        salary_data=salary_data,
        total_payroll=round(total_payroll, 2),
        current_month=month,
        current_year=year,
        days_in_month=days_in_month,
        period=period,
        banks=banks,
        departments=departments,
        is_locked=bool(is_locked),
        audit_logs=audit_logs,
        now=datetime.now()
    )

@salary_bp.route('/save', methods=['POST'])
@login_required(role='admin')
def save_salary():
    """AJAX endpoint to save individual salary row"""
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form

    worker_id = data.get('worker_id')
    month = data.get('month') or request.args.get('period', datetime.now().strftime('%Y-%m'))

    # Check if period is locked
    if PayrollLock.query.filter_by(month=month).first():
        return jsonify({'error': 'Period is locked'}), 403

    salary = Salary.query.filter_by(worker_id=worker_id, month=month).first()
    if not salary:
        worker = Worker.query.get(worker_id)
        if not worker:
            return jsonify({'error': 'Worker not found'}), 404
        salary = Salary(
            worker_id=worker_id,
            month=month,
            total_days_present=0,
            daily_rate=float(worker.amount_of_salary or 0) / monthrange(int(month[:4]), int(month[5:7]))[1],
            deductions=0
        )
        salary.auto_fill_from_worker()

    # Update fields if present
    if 'total_days_present' in data:
        salary.total_days_present = int(data['total_days_present'])
    if 'daily_rate' in data:
        salary.daily_rate = float(data['daily_rate'])
    if 'deductions' in data:
        salary.deductions = float(data['deductions'])

    # Mark as processed on save
    salary.is_processed = True
    salary.calculate()
    db.session.add(salary)

    # Audit log
    audit = AuditLog(
        user_name=session.get('username', 'Admin'),
        action='processed',
        table_name='salary',
        record_id=salary.id,
        worker_id=salary.worker_id,
        worker_name=salary.worker.name,
        details=f'Processed salary for {month}: days={salary.total_days_present}, rate={salary.daily_rate}, ded={salary.deductions}'
    )
    db.session.add(audit)
    db.session.commit()

    return jsonify({
        'success': True,
        'net_salary': salary.net_salary,
        'gross_salary': salary.gross_salary,
        'is_processed': salary.is_processed,
        'message': 'Salary processed successfully'
    })

@salary_bp.route('/save-all', methods=['POST'])
@login_required(role='admin')
def save_all_salaries():
    """Save all pending salaries for a period"""
    period = request.args.get('period', datetime.now().strftime('%Y-%m'))

    if PayrollLock.query.filter_by(month=period).first():
        return jsonify({'error': 'Period is locked'}), 403

    salaries = Salary.query.filter_by(month=period, is_processed=False).all()
    count = 0

    for salary in salaries:
        salary.is_processed = True
        db.session.add(salary)
        count += 1

    db.session.commit()
    return jsonify({'success': True, 'processed': count})

@salary_bp.route('/bulk-update', methods=['POST'])
@login_required(role='admin')
def bulk_update_salaries():
    """Bulk update selected salaries"""
    data = request.get_json()
    worker_ids = data.get('worker_ids', [])
    month = data.get('month', datetime.now().strftime('%Y-%m'))
    updates = data.get('updates', {})

    if PayrollLock.query.filter_by(month=month).first():
        return jsonify({'error': 'Period is locked'}), 403

    updated = 0
    for wid in worker_ids:
        salary = Salary.query.filter_by(worker_id=wid, month=month).first()
        if not salary:
            continue

        if 'daily_rate' in updates:
            salary.daily_rate = float(updates['daily_rate'])
        if 'deduction_percent' in updates:
            gross = float(salary.total_days_present) * float(salary.daily_rate)
            salary.deductions = (gross * float(updates['deduction_percent'])) / 100
        if 'status' in updates:
            salary.is_processed = (updates['status'] == 'processed')

        salary.calculate()
        db.session.add(salary)
        updated += 1

    db.session.commit()
    return jsonify({'success': True, 'updated': updated})

@salary_bp.route('/toggle-lock', methods=['POST'])
@login_required(role='admin')
def toggle_lock():
    """Lock or unlock a payroll period"""
    period = request.args.get('period', datetime.now().strftime('%Y-%m'))
    lock = PayrollLock.query.filter_by(month=period).first()

    if lock:
        db.session.delete(lock)
        locked = False
        action = 'unlocked'
    else:
        lock = PayrollLock(
            month=period,
            locked_by=session.get('username', 'Admin'),
            note=request.form.get('note', '')
        )
        db.session.add(lock)
        locked = True
        action = 'locked'

    audit = AuditLog(
        user_name=session.get('username', 'Admin'),
        action=action,
        table_name='payroll_lock',
        details=f'Period {period} {action}'
    )
    db.session.add(audit)
    db.session.commit()

    return jsonify({'locked': locked, 'message': f'Period {period} {action}'})

@salary_bp.route('/history')
@login_required(role='admin')
def salary_history():
    period = request.args.get('period', datetime.now().strftime('%Y-%m'))
    status_filter = request.args.get('status', 'all')
    department_filter = request.args.get('department', 'all')

    year, month = map(int, period.split('-'))
    days_in_month = monthrange(year, month)[1]
    if days_in_month < 1:
        days_in_month = 1

    query = Salary.query.filter_by(month=period)

    if status_filter == 'processed':
        query = query.filter_by(is_processed=True)
    elif status_filter == 'pending':
        query = query.filter_by(is_processed=False)

    if department_filter!= 'all':
        query = query.join(Worker).filter(Worker.department == department_filter)

    salaries = query.order_by(Salary.payment_date.desc()).all()

    # Attach extra display values
    for s in salaries:
        s.days_in_month = days_in_month
        s.present_days = s.total_days_present
        s.attendance_percent = round((s.total_days_present / days_in_month) * 100, 1) if days_in_month > 0 else 0
        s.daily_rate_display = s.daily_rate

    total_gross = sum(s.gross_salary for s in salaries)
    total_deductions = sum(s.deductions for s in salaries)
    total_paid = sum(s.net_salary for s in salaries)

    # Build period list
    available_months = []
    for y in range(datetime.now().year - 2, datetime.now().year + 2):
        for m in range(1, 13):
            available_months.append(f"{y}-{m:02d}")
    available_months.reverse()

    departments = db.session.query(Worker.department).distinct().filter(Worker.department.isnot(None)).all()
    departments = [d[0] for d in departments]

    is_locked = PayrollLock.query.filter_by(month=period).first()

    return render_template(
        'salary_history.html',
        salary_records=salaries,
        total_gross=total_gross,
        total_deductions=total_deductions,
        total_paid=total_paid,
        period=period,
        available_months=available_months,
        departments=departments,
        status_filter=status_filter,
        department_filter=department_filter,
        is_locked=bool(is_locked),
        now=datetime.now()
    )

@salary_bp.route('/payslip/<int:worker_id>')
@login_required(role='admin')
def payslip(worker_id):
    period = request.args.get('period', datetime.now().strftime('%Y-%m'))

    salary = Salary.query.filter_by(worker_id=worker_id, month=period)\
                        .options(db.joinedload(Salary.worker))\
                        .first()

    if not salary:
        return "Payslip not found for this period", 404

    # Calculate month values
    year, month = map(int, period.split('-'))
    days_in_month = monthrange(year, month)[1]
    if days_in_month < 1:
        days_in_month = 1

    # Attach display fields
    salary.days_in_month = days_in_month
    salary.present_days = salary.total_days_present or 0
    salary.attendance_percent = round((salary.present_days / days_in_month) * 100, 1) if days_in_month > 0 else 0

    # Fallback to worker fields if salary fields are empty
    if salary.worker:
        salary.worker_code = salary.worker_code or salary.worker_code
        salary.bank_name = salary.bank_name or salary.worker.bank_name
        salary.bank_account = salary.bank_account or salary.worker.bank_account
        salary.worker_department = salary.worker.department
        salary.worker_position = getattr(salary.worker, 'position', None)

    # Ensure numbers are not None for template
    salary.daily_rate = salary.daily_rate or 0
    salary.gross_salary = salary.gross_salary or 0
    salary.deductions = salary.deductions or 0
    salary.net_salary = salary.net_salary or 0

    return render_template(
        'payslip.html',
        salary=salary,
        period=period,
        now=datetime.now()
    )

@salary_bp.route('/export-csv')
@login_required(role='admin')
def export_csv():
    period = request.args.get('period', datetime.now().strftime('%Y-%m'))
    year, month = map(int, period.split('-'))
    days_in_month = monthrange(year, month)[1]

    salaries = Salary.query.filter_by(month=period).all()

    csv_data = "Worker Code,Name,Department,Days Present,Days in Month,Attendance %,Daily Rate,Gross,Deductions,Net,Bank,Account No,Status\n"
    for s in salaries:
        present = s.total_days_present
        percent = round((present / days_in_month) * 100, 1) if days_in_month > 0 else 0
        csv_data += f"{s.worker_code},{s.worker.name},{s.worker.department},{present},{days_in_month},{percent},"
        csv_data += f"{s.daily_rate},{s.gross_salary},{s.deductions},{s.net_salary},"
        csv_data += f"{s.bank_name},{s.bank_account},{'Processed' if s.is_processed else 'Pending'}\n"

    return current_app.response_class(
        csv_data,
        mimetype='text/csv',
        headers={"Content-disposition": f"attachment; filename=salary_{period}.csv"}
    )