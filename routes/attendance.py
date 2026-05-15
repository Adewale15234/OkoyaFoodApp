from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from extensions import db
from models import Worker, Attendance
from utils import login_required
from datetime import date
import logging

attendance_bp = Blueprint('attendance', __name__)

@attendance_bp.route('/secretary_attendance', methods=['GET', 'POST'])
def secretary_attendance():
    return redirect(url_for('attendance.attendance'))

@attendance_bp.route('/attendance', methods=['GET', 'POST'])
@login_required()
def attendance():
    workers = Worker.query.filter_by(is_active=True).all()
    secretary = session.get('role') == 'secretary'
    today = date.today()

    total_workers = len(workers)
    today_present_count = Attendance.query.filter_by(date=today, status="Present").count()
    today_absent_count = Attendance.query.filter_by(date=today, status="Absent").count()

    if request.method == 'POST':
        worker_id = request.form.get('worker_id')
        status = request.form.get('attendance_status')

        if not worker_id or not status:
            flash("Missing attendance data.", "error")
            return redirect(url_for('attendance.attendance'))

        try:
            worker_id = int(worker_id)
        except ValueError:
            flash("Invalid worker ID.", "error")
            return redirect(url_for('attendance.attendance'))

        worker = Worker.query.get(worker_id)
        if not worker:
            flash("Worker not found.", "error")
            return redirect(url_for('attendance.attendance'))

        existing = Attendance.query.filter_by(worker_id=worker_id, date=today).first()
        if existing:
            flash(f"{worker.name} already marked for today.", "warning")
            return redirect(url_for('attendance.attendance'))

        try:
            new_attendance = Attendance(worker_id=worker_id, status=status, date=today)
            db.session.add(new_attendance)
            db.session.commit()
            flash(f"Attendance marked for {worker.name}.", "success")
        except Exception as e:
            db.session.rollback()
            logging.error(f"Attendance error: {e}")
            flash("System error while saving attendance.", "error")

        return redirect(url_for('attendance.attendance'))

    return render_template(
        'attendance.html',
        workers=workers,
        secretary=secretary,
        total_workers=total_workers,
        today_present_count=today_present_count,
        today_absent_count=today_absent_count,
        today=today
    )

@attendance_bp.route('/attendance_history')
@login_required()
def attendance_history():
    if session.get('role') not in ['admin', 'secretary']:
        flash("Please login first.", "warning")
        return redirect(url_for('auth.login'))

    selected_month = request.args.get('month')
    attendance_query = Attendance.query.join(Worker).order_by(Attendance.date.desc())

    all_records = attendance_query.all()
    available_months = sorted(list({record.date.strftime("%B %Y") for record in all_records}), reverse=True)

    if selected_month:
        try:
            from datetime import datetime
            from sqlalchemy import extract
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
        now=date.today()
    )