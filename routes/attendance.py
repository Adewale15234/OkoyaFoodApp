from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from extensions import db
from models import Worker, Attendance
from utils import login_required
from datetime import date, datetime
from sqlalchemy import extract
import logging

attendance_bp = Blueprint('attendance', __name__)

@attendance_bp.route('/secretary_attendance', methods=['GET', 'POST'])
def secretary_attendance():
    return redirect(url_for('attendance.attendance'))

@attendance_bp.route('/attendance', methods=['GET', 'POST'])
@login_required()
def attendance():
    today = date.today()
    secretary = session.get('role') == 'secretary'

    # Get all active workers
    workers = Worker.query.filter_by(is_active=True).order_by(Worker.name.asc()).all()

    # Get unique departments for filter dropdown
    departments = db.session.query(Worker.department).distinct().filter(Worker.department.isnot(None)).all()
    departments = [d[0] for d in departments if d[0]]

    # Load today's attendance data into worker objects for template
    today_attendance = Attendance.query.filter_by(date=today).all()
    att_map = {a.worker_id: a for a in today_attendance}

    for w in workers:
        att = att_map.get(w.id)
        if att:
            w.today_status = att.status
            w.today_time_in = att.time_in
            w.today_time_out = att.time_out
            w.today_notes = att.notes
        else:
            w.today_status = None
            w.today_time_in = None
            w.today_time_out = None
            w.today_notes = None

    # Handle POST request
    if request.method == 'POST':
        # Check if it's a bulk save
        bulk_data = request.form.get('bulk_data')

        if bulk_data:
            # Bulk save from "Save All" button
            try:
                import json
                records = json.loads(bulk_data)
                saved = 0
                updated = 0
                errors = 0

                for item in records:
                    try:
                        worker_id = int(item.get('worker_id'))
                        status = item.get('status')

                        if not worker_id or not status:
                            continue

                        # Parse time fields
                        time_in = None
                        time_out = None
                        if item.get('time_in'):
                            time_in = datetime.strptime(item['time_in'], '%H:%M').time()
                        if item.get('time_out'):
                            time_out = datetime.strptime(item['time_out'], '%H:%M').time()

                        notes = item.get('notes', '').strip()[:100]

                        existing = Attendance.query.filter_by(worker_id=worker_id, date=today).first()

                        if existing:
                            existing.status = status
                            existing.time_in = time_in
                            existing.time_out = time_out
                            existing.notes = notes
                            updated += 1
                        else:
                            new_att = Attendance(
                                worker_id=worker_id,
                                status=status,
                                date=today,
                                time_in=time_in,
                                time_out=time_out,
                                notes=notes
                            )
                            db.session.add(new_att)
                            saved += 1

                    except Exception as e:
                        logging.error(f"Bulk save error for worker {item.get('worker_id')}: {e}")
                        errors += 1
                        continue

                db.session.commit()

                msg_parts = []
                if saved > 0:
                    msg_parts.append(f"{saved} new records saved")
                if updated > 0:
                    msg_parts.append(f"{updated} records updated")
                if errors > 0:
                    msg_parts.append(f"{errors} failed")

                flash(", ".join(msg_parts), "success" if errors == 0 else "warning")

            except Exception as e:
                db.session.rollback()
                logging.error(f"Bulk attendance save error: {e}")
                flash("System error while saving bulk attendance.", "error")

            return redirect(url_for('attendance.attendance'))

        else:
            # Single worker save from individual form
            worker_id = request.form.get('worker_id')
            status = request.form.get('attendance_status')
            time_in_str = request.form.get('time_in')
            time_out_str = request.form.get('time_out')
            notes = request.form.get('notes', '').strip()[:100]

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

            # Parse time fields
            time_in = None
            time_out = None
            try:
                if time_in_str:
                    time_in = datetime.strptime(time_in_str, '%H:%M').time()
                if time_out_str:
                    time_out = datetime.strptime(time_out_str, '%H:%M').time()
            except ValueError:
                flash("Invalid time format.", "error")
                return redirect(url_for('attendance.attendance'))

            try:
                existing = Attendance.query.filter_by(worker_id=worker_id, date=today).first()

                if existing:
                    existing.status = status
                    existing.time_in = time_in
                    existing.time_out = time_out
                    existing.notes = notes
                    flash(f"Attendance updated for {worker.name}.", "success")
                else:
                    new_attendance = Attendance(
                        worker_id=worker_id,
                        status=status,
                        date=today,
                        time_in=time_in,
                        time_out=time_out,
                        notes=notes
                    )
                    db.session.add(new_attendance)
                    flash(f"Attendance marked for {worker.name}.", "success")

                db.session.commit()

            except Exception as e:
                db.session.rollback()
                logging.error(f"Attendance error: {e}")
                flash("System error while saving attendance.", "error")

            return redirect(url_for('attendance.attendance'))

    # Calculate stats for template
    total_workers = len(workers)
    today_present_count = sum(1 for w in workers if getattr(w, 'today_status', None) == 'Present')
    today_absent_count = sum(1 for w in workers if getattr(w, 'today_status', None) == 'Absent')
    today_late_count = sum(1 for w in workers if getattr(w, 'today_status', None) == 'Late')
    today_leave_count = sum(1 for w in workers if getattr(w, 'today_status', None) == 'Leave')

    return render_template(
        'attendance.html',
        workers=workers,
        departments=departments,
        secretary=secretary,
        total_workers=total_workers,
        today_present_count=today_present_count,
        today_absent_count=today_absent_count,
        today_late_count=today_late_count,
        today_leave_count=today_leave_count,
        today=today
    )

@attendance_bp.route('/attendance_history')
@login_required()
def attendance_history():
    if session.get('role') not in ['admin', 'secretary']:
        flash("Please login first.", "warning")
        return redirect(url_for('auth.login'))

    # Get filter parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    selected_month = request.args.get('month')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    status = request.args.get('status')
    worker_search = request.args.get('worker')

    # Base query
    attendance_query = Attendance.query.join(Worker).order_by(Attendance.date.desc(), Attendance.id.desc())

    # Apply month filter
    if selected_month:
        try:
            month_dt = datetime.strptime(selected_month, "%B %Y")
            attendance_query = attendance_query.filter(
                extract('month', Attendance.date) == month_dt.month,
                extract('year', Attendance.date) == month_dt.year
            )
        except ValueError:
            flash("Invalid month format for filtering.", "error")

    # Apply date range filters
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            attendance_query = attendance_query.filter(Attendance.date >= date_from_obj)
        except ValueError:
            flash("Invalid date from format.", "error")

    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            attendance_query = attendance_query.filter(Attendance.date <= date_to_obj)
        except ValueError:
            flash("Invalid date to format.", "error")

    # Apply status filter
    if status:
        attendance_query = attendance_query.filter(Attendance.status == status)

    # Apply worker search filter
    if worker_search:
        attendance_query = attendance_query.filter(Worker.name.ilike(f'%{worker_search}%'))

    # Get all records for month filter dropdown - use unfiltered query for this
    all_records_query = Attendance.query.join(Worker).order_by(Attendance.date.desc())
    all_records = all_records_query.all()
    available_months = sorted(
        list({record.date.strftime("%B %Y") for record in all_records}),
        reverse=True
    )

    # Paginate filtered results
    pagination = attendance_query.paginate(page=page, per_page=per_page, error_out=False)
    attendance_records = pagination.items

    return render_template(
        "attendance_history.html",
        attendance_records=attendance_records,
        pagination=pagination,
        available_months=available_months,
        selected_month=selected_month,
        now=date.today()
    )

@attendance_bp.route('/attendance/api/bulk_check', methods=['POST'])
@login_required()
def attendance_bulk_check():
    """
    API endpoint to check if workers already have attendance for today
    Used by frontend to prevent duplicate submissions
    """
    try:
        data = request.get_json()
        worker_ids = data.get('worker_ids', [])
        today = date.today()

        existing = Attendance.query.filter(
            Attendance.worker_id.in_(worker_ids),
            Attendance.date == today
        ).all()

        existing_ids = [a.worker_id for a in existing]

        return jsonify({
            'success': True,
            'existing_ids': existing_ids,
            'count': len(existing_ids)
        })
    except Exception as e:
        logging.error(f"Bulk check error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@attendance_bp.route('/attendance/delete/<int:attendance_id>', methods=['POST'])
@login_required()
def delete_attendance(attendance_id):
    """
    Delete a single attendance record
    """
    if session.get('role')!= 'admin':
        flash("Only admin can delete attendance records.", "error")
        return redirect(url_for('attendance.attendance_history'))

    att = Attendance.query.get_or_404(attendance_id)

    try:
        worker_name = att.worker.name
        db.session.delete(att)
        db.session.commit()
        flash(f"Attendance record for {worker_name} deleted.", "success")
    except Exception as e:
        db.session.rollback()
        logging.error(f"Delete attendance error: {e}")
        flash("Error deleting record.", "error")

    return redirect(request.referrer or url_for('attendance.attendance_history'))