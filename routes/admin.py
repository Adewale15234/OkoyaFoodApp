from flask import Blueprint, render_template, send_file, flash, redirect, url_for
from utils import login_required
from extensions import db
from services.backup_manager import create_backup
from flask import current_app

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin_dashboard')
@login_required(role='admin')
def admin_dashboard():
    return render_template('admin_dashboard.html')

@admin_bp.route("/backup-now")
@login_required(role='admin')
def backup_now():
    db_url = current_app.config['SQLALCHEMY_DATABASE_URI']
    file_path = create_backup(db_url)

    if file_path:
        flash("Backup created successfully!", "success")
        return send_file(file_path, as_attachment=True)

    flash("Backup failed!", "danger")
    return redirect(url_for("admin.admin_dashboard"))