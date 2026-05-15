from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from extensions import db
from models import Worker, Attendance, Salary
from utils import login_required
from datetime import datetime
from calendar import monthrange
from sqlalchemy import extract
import logging

salary_bp = Blueprint('salary', __name__, url_prefix='/salary')

@salary_bp.route('/', methods=['GET', 'POST'])
@login_required(role='admin')
def salary():
    workers = Worker.query.filter_by(is_active=True).all()

    today = datetime.today()
    current_year = today.year
    current_month = today.month

    total_days_in_month = monthrange(current_year, current_month)[1]
    if total_days_in_month < 1:
        total_days_in_month = 1

    salary_data = []
    total_payroll = 0

    for worker in workers:
        total_days_present = Attendance.query.filter(
            Attendance.worker_id == worker.id,
            Attendance.status == "Present",
            extract('year', Attendance.date) == current_year,
            extract('month', Attendance.date) == current_month
        ).count()

        daily_rate = (worker.amount_of_salary or 0) / total_days_in_month
        calculated_salary = total_days_present * daily_rate
        total_payroll += calculated_salary

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

            if not worker:
                flash("Worker not found.", "error")
                return redirect(url_for('salary.salary'))

            # 🚫 Prevent duplicate salary for same month
            existing_salary = Salary.query.filter_by(
                worker_id=worker_id
            ).filter(
                extract('year', Salary.payment_date) == current_year,
                extract('month', Salary.payment_date) == current_month
            ).first()

            if existing_salary:
                flash(f"Salary already recorded for {worker.name} this month.", "warning")
                return redirect(url_for('salary.salary_history'))

            total_days_present = Attendance.query.filter(
                Attendance.worker_id == worker.id,
                Attendance.status == "Present",
                extract('year', Attendance.date) == current_year,
                extract('month', Attendance.date) == current_month
            ).count()

            daily_rate = (worker.amount_of_salary or 0) / total_days_in_month
            calculated_salary = total_days_present * daily_rate

            new_salary = Salary(
                worker_id=worker.id,
                total_days_present=total_days_present,
                daily_rate=daily_rate,
                amount=round(calculated_salary, 2),
                bank_name=worker.bank_name,
                bank_account=worker.bank_account,
                bank_account_name=worker.bank_account_name,
                payment_date=datetime.now()
            )

            db.session.add(new_salary)
            db.session.commit()

            flash(f"Salary recorded successfully for {worker.name}.", "success")
            return redirect(url_for('salary.salary_history'))

        except Exception as e:
            db.session.rollback()
            logging.error(f"Salary error: {e}")
            flash("Error recording salary. Try again.", "error")

    return render_template(
        'salary.html',
        salary_data=salary_data,
        total_payroll=round(total_payroll, 2),
        current_month=current_month,
        current_year=current_year
    )

@salary_bp.route('/history')
@login_required(role='admin')
def salary_history():
    today = datetime.today()
    current_year = today.year
    current_month = today.month

    # Show current month by default, but allow filtering
    year = request.args.get('year', current_year, type=int)
    month = request.args.get('month', current_month, type=int)

    salaries = Salary.query.filter(
        extract('year', Salary.payment_date) == year,
        extract('month', Salary.payment_date) == month
    ).order_by(Salary.payment_date.desc()).all()

    total_paid = sum(s.amount for s in salaries)

    # Build available months for filter dropdown
    available_months = []
    for y in range(today.year - 2, today.year + 1):
        for m in range(1, 13):
            available_months.append(f"{y}-{m:02d}")
    available_months.reverse()

    selected_month_str = f"{year}-{month:02d}"

    return render_template(
        'salary_history.html',
        salary_records=salaries,
        total_paid=round(total_paid, 2),
        selected_year=year,
        selected_month=selected_month_str,
        available_months=available_months,
        now=datetime.now()
    )