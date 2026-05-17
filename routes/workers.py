from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from extensions import db
from models import Worker, EmailLog, Attendance, Salary
from utils import login_required, allowed_file, get_passport_url, safe_date
from services.hr_letter import generate_hr_letter
import os
import uuid
from werkzeug.utils import secure_filename
from datetime import datetime
import json
import qrcode
import base64
from io import BytesIO

workers_bp = Blueprint('workers', __name__, url_prefix='/workers')

@workers_bp.route('/register_worker', methods=['GET', 'POST'])
@login_required(role='admin')
def register_worker():
    if request.method == 'POST':
        try:
            # ===============================
            # 1. COLLECT & CLEAN INPUTS
            # ===============================
            name = (request.form.get('name') or "").strip()
            phone_number = (request.form.get('phone_number') or "").strip()
            gender = (request.form.get('gender') or "").strip().title()
            email = (request.form.get('email') or "").strip().lower()
            qualifications = (request.form.get('qualifications') or "").strip()
            position = (request.form.get('position') or "").strip()
            guarantor = (request.form.get('guarantor') or "").strip()
            national_id = (request.form.get('national_id') or "").strip()
            nationality = (request.form.get('nationality') or "").strip()
            ethnic_group = (request.form.get('ethnic_group') or "").strip()
            disability = (request.form.get('disability') or "").strip()
            home_address = (request.form.get('home_address') or "").strip()
            place_of_residence = (request.form.get('place_of_residence') or "").strip()
            bank_account_name = (request.form.get('bank_account_name') or "").strip()
            bank_name = (request.form.get('bank_name') or "").strip()
            bank_account = (request.form.get('bank_account') or "").strip()

            # salary safe parse
            try:
                amount_of_salary = float(request.form.get('amount_of_salary') or 0)
            except ValueError:
                amount_of_salary = 0.0

            # ===============================
            # 2. DATE VALIDATION
            # ===============================
            date_of_birth = safe_date(request.form.get('date_of_birth'))
            date_of_employment = safe_date(request.form.get('date_of_employment'))

            # ===============================
            # 3. FULL VALIDATION
            # ===============================
            required_fields = {
                "Name": name,
                "Phone Number": phone_number,
                "Gender": gender,
                "Email": email,
                "Qualifications": qualifications,
                "Position": position,
                "Guarantor": guarantor,
                "National ID": national_id,
                "Nationality": nationality,
                "Home Address": home_address,
                "Ethnic Group": ethnic_group,
                "Place of Residence": place_of_residence,
                "Bank Account Name": bank_account_name
            }

            for label, value in required_fields.items():
                if not value:
                    flash(f"{label} is required.", "danger")
                    return redirect(url_for('workers.register_worker'))

            if not date_of_birth:
                flash("Valid Date of Birth required.", "danger")
                return redirect(url_for('workers.register_worker'))

            if not date_of_employment:
                flash("Valid Employment Date required.", "danger")
                return redirect(url_for('workers.register_worker'))

            if amount_of_salary < 0:
                flash("Salary cannot be negative.", "danger")
                return redirect(url_for('workers.register_worker'))

            # ===============================
            # 4. DUPLICATE CHECK
            # ===============================
            existing_worker = Worker.query.filter(
                (Worker.phone_number == phone_number) |
                (Worker.email == email)
            ).first()

            if existing_worker:
                flash("Worker with this phone or email already exists.", "warning")
                return redirect(url_for('workers.register_worker'))

            # ===============================
            # 5. NIN CHECK
            # ===============================
            if national_id:
                existing_nin = Worker.query.filter_by(national_id=national_id).first()
                if existing_nin:
                    flash("This National ID is already registered.", "warning")
                    return redirect(url_for('workers.register_worker'))

            # ===============================
            # 6. PASSPORT UPLOAD - CLOUDINARY
            # ===============================
            passport_url = None
            passport_file = request.files.get('passport')

            if passport_file and passport_file.filename.strip():
                if not allowed_file(passport_file.filename):
                    flash("Only image files (jpg, jpeg, png, gif, webp) allowed.", "danger")
                    return redirect(url_for('workers.register_worker'))

                import cloudinary.uploader
                result = cloudinary.uploader.upload(
                    passport_file,
                    folder="okoya_passports",
                    transformation=[{"width": 500, "height": 500, "crop": "fill"}],
                    resource_type="image"
                )
                passport_url = result['secure_url']
                print(f"[PASSPORT UPLOADED] {passport_url}")

            # ===============================
            # 7. AUTO WORKER CODE
            # ===============================
            last_worker = Worker.query.order_by(Worker.id.desc()).first()
            if last_worker and last_worker.worker_code:
                try:
                    last_number = int(last_worker.worker_code.replace("OFCL", ""))
                    new_number = last_number + 1
                except:
                    new_number = (last_worker.id or 0) + 1
            else:
                new_number = 1

            worker_code = f"OFCL{new_number:04d}"

            # ===============================
            # 8. CREATE WORKER
            # ===============================
            new_worker = Worker(
                worker_code=worker_code,
                name=name,
                phone_number=phone_number,
                date_of_birth=date_of_birth,
                gender=gender,
                email=email,
                qualifications=qualifications,
                position=position,
                amount_of_salary=amount_of_salary,
                date_of_employment=date_of_employment,
                guarantor=guarantor,
                national_id=national_id,
                nationality=nationality,
                ethnic_group=ethnic_group,
                disability=disability,
                home_address=home_address,
                place_of_residence=place_of_residence,
                bank_account_name=bank_account_name,
                bank_name=bank_name,
                bank_account=bank_account,
                passport=passport_url, # Save Cloudinary URL now
                is_active=True
            )

            # ===============================
            # 9. SAVE
            # ===============================
            db.session.add(new_worker)
            db.session.commit()

            print(f"[WORKER CREATED] {worker_code} - {name}")
            flash(f"Worker registered successfully! Code: {worker_code}", "success")
            return render_template('register_worker.html', worker=new_worker)

        except Exception as e:
            db.session.rollback()
            import traceback
            traceback.print_exc()
            return f"<pre>{traceback.format_exc()}</pre>", 500

    return render_template('register_worker.html')

@workers_bp.route('/')
@login_required()
def workers_name():
    if session.get('role') not in ['admin', 'hr', 'manager']:
        flash("You are not authorized to access this page.", "error")
        return redirect(url_for('secretary.secretary_dashboard'))

    workers = Worker.query.order_by(Worker.id.desc()).all()
    new_worker_id = request.args.get('new_id', type=int)
    return render_template('workers_name.html', workers=workers, new_worker_id=new_worker_id)

@workers_bp.route('/toggle_worker_status/<int:worker_id>', methods=['POST'])
@login_required(role='admin')
def toggle_worker_status(worker_id):
    worker = Worker.query.get_or_404(worker_id)
    reason = request.form.get('reason', '').strip()

    if not reason:
        flash("Reason is required before changing worker status.", "danger")
        return redirect(url_for('workers.workers_name'))

    now = datetime.utcnow()
    worker.is_active = not worker.is_active

    if worker.is_active:
        worker.status_type = "reactivated"
    else:
        worker.status_type = "deactivated"

    worker.status_reason = reason
    worker.status_date = now
    worker.last_action_by = session.get('role')
    worker.last_action_date = now

    if not worker.is_active:
        worker.warning_count = (worker.warning_count or 0) + 1

    # Generate letter with AI offence review included
    worker.status_letter = generate_hr_letter(worker, reason, worker.status_type)
    db.session.commit()
    flash(f"{worker.name} status updated successfully.", "success")
    return redirect(url_for('workers.workers_name'))

@workers_bp.route('/worker_history/<int:worker_id>')
@login_required()
def worker_history(worker_id):
    worker = Worker.query.get_or_404(worker_id)
    return render_template('worker_history.html', worker=worker)

@workers_bp.route('/active-workers')
@login_required()
def active_workers():
    workers = Worker.query.filter_by(is_active=True).all()
    return render_template('workers_name.html', workers=workers)

@workers_bp.route('/inactive-workers')
@login_required()
def inactive_workers():
    workers = Worker.query.filter_by(is_active=False).all()
    return render_template('workers_name.html', workers=workers)

@workers_bp.route('/worker_letter/<int:worker_id>')
@login_required()
def worker_letter(worker_id):
    worker = Worker.query.get_or_404(worker_id)
    if not worker.status_letter:
        flash("No letter available for this worker.", "warning")
        return redirect(url_for('workers.workers_name'))
    return render_template('worker_letter.html', worker=worker)

@workers_bp.route('/send_worker_letter/<int:worker_id>', methods=['POST'])
@login_required(role='admin')
def send_worker_letter(worker_id):
    from flask_mail import Message
    from extensions import mail

    worker = Worker.query.get_or_404(worker_id)

    if not worker.email:
        flash("Worker has no email address.", "danger")
        return redirect(url_for('workers.worker_letter', worker_id=worker.id))

    if not worker.status_letter:
        flash("No HR letter available.", "danger")
        return redirect(url_for('workers.worker_letter', worker_id=worker.id))

    try:
        print("SENDING EMAIL TO:", worker.email)
        print("SMTP USER:", current_app.config['MAIL_USERNAME'])
        print("SMTP SERVER:", current_app.config['MAIL_SERVER'])

        msg = Message(
            subject="Official HR Letter - Okoya Food Ltd",
            sender=current_app.config['MAIL_DEFAULT_SENDER'],
            recipients=[worker.email],
            body=worker.status_letter
        )
        mail.send(msg)
        flash("Letter sent successfully!", "success")

    except Exception as e:
        print("EMAIL ERROR:", str(e))
        import traceback
        traceback.print_exc()
        flash("Email failed. Check SMTP or network.", "danger")

    return redirect(url_for('workers.worker_letter', worker_id=worker.id))

@workers_bp.route('/edit_worker/<int:worker_id>', methods=['GET', 'POST'])
@login_required(role='admin')
def edit_worker(worker_id):
    worker = Worker.query.get_or_404(worker_id)

    if request.method == 'POST':
        try:
            worker.name = (request.form.get('name') or "").strip()
            worker.phone_number = (request.form.get('phone_number') or "").strip()
            worker.gender = (request.form.get('gender') or "").strip()
            worker.email = (request.form.get('email') or "").strip().lower()
            worker.qualifications = (request.form.get('qualifications') or "").strip()
            worker.position = (request.form.get('position') or "").strip()
            worker.national_id = (request.form.get('national_id') or "").strip()
            worker.nationality = (request.form.get('nationality') or "").strip()
            worker.home_address = (request.form.get('home_address') or "").strip()
            worker.ethnic_group = (request.form.get('ethnic_group') or "").strip()
            worker.place_of_residence = (request.form.get('place_of_residence') or "").strip()
            worker.disability = (request.form.get('disability') or "").strip()
            worker.bank_name = (request.form.get('bank_name') or "").strip()
            worker.bank_account = (request.form.get('bank_account') or "").strip()
            worker.bank_account_name = (request.form.get('bank_account_name') or "").strip()
            worker.guarantor = (request.form.get('guarantor') or "").strip()

            try:
                worker.amount_of_salary = float(request.form.get('amount_of_salary') or 0)
            except ValueError:
                worker.amount_of_salary = 0

            def safe_date(value):
                try:
                    return datetime.strptime(value, "%Y-%m-%d").date()
                except:
                    return None

            worker.date_of_birth = safe_date(request.form.get('date_of_birth'))
            worker.date_of_employment = safe_date(request.form.get('date_of_employment'))

            # ===============================
            # PASSPORT UPLOAD - CLOUDINARY
            # ===============================
            passport_file = request.files.get('passport')
            if passport_file and passport_file.filename:
                if allowed_file(passport_file.filename):
                    import cloudinary.uploader

                    # Delete old image from Cloudinary if exists
                    if worker.passport and 'cloudinary.com' in worker.passport:
                        try:
                            public_id = worker.passport.split('/upload/')[1].rsplit('.', 1)[0]
                            cloudinary.uploader.destroy(public_id)
                        except:
                            pass

                    # Upload new image
                    result = cloudinary.uploader.upload(
                        passport_file,
                        folder="okoya_passports",
                        transformation=[{"width": 500, "height": 500, "crop": "fill"}],
                        resource_type="image"
                    )
                    worker.passport = result['secure_url']
                    worker.updated_at = datetime.utcnow()
                else:
                    flash("Only jpg, jpeg, png, gif, webp files allowed.", "danger")
                    return redirect(url_for('workers.edit_worker', worker_id=worker.id))

            db.session.commit()
            flash('Worker details updated successfully.', 'success')
            return redirect(url_for('workers.workers_name'))

        except Exception as e:
            db.session.rollback()
            flash(f"Error updating worker: {e}", "danger")

    return render_template('edit_worker.html', worker=worker)

@workers_bp.route('/worker_id_card/<int:worker_id>')
@login_required(role='admin')
def worker_id_card(worker_id):
    worker = Worker.query.get_or_404(worker_id)
    passport_url = get_passport_url(worker)

    verify_url = url_for('workers.verify_worker', worker_code=worker.worker_code, _external=True)

    qr_data = {
        "company": "OKOYA FOOD COMPANY LIMITED",
        "worker_code": worker.worker_code,
        "name": worker.name,
        "position": worker.position,
        "phone": worker.phone_number or "N/A",
        "status": "Active" if worker.is_active else "Inactive",
        "verify_url": verify_url
    }

    qr_string = json.dumps(qr_data, ensure_ascii=False)

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=4,
        border=2
    )
    qr.add_data(qr_string)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    qr_base64 = base64.b64encode(buffer.read()).decode('utf-8')

    return render_template('worker_id_card.html', worker=worker, qr_code=qr_base64, passport_url=passport_url)

@workers_bp.route('/verify/<worker_code>')
def verify_worker(worker_code):
    worker = Worker.query.filter_by(worker_code=worker_code).first_or_404()
    return render_template('verify_worker.html', worker=worker)

@workers_bp.route('/delete_worker/<int:worker_id>', methods=['POST'])
@login_required(role='admin')
def delete_worker(worker_id):
    worker = Worker.query.get_or_404(worker_id)

    try:
        # Delete passport from Cloudinary if exists
        if worker.passport and 'cloudinary.com' in worker.passport:
            import cloudinary.uploader
            try:
                public_id = worker.passport.split('/upload/')[1].rsplit('.', 1)[0]
                cloudinary.uploader.destroy(public_id)
            except:
                pass

        db.session.query(EmailLog).filter_by(worker_id=worker.id).delete()
        db.session.query(Attendance).filter_by(worker_id=worker.id).delete()
        db.session.query(Salary).filter_by(worker_id=worker.id).delete()
        db.session.delete(worker)
        db.session.commit()
        flash('Worker deleted successfully.', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting worker: {str(e)}', 'danger')

    return redirect(url_for('workers.workers_name'))