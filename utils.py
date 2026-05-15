import time
from flask import url_for, session, flash, redirect
from functools import wraps
from datetime import datetime

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return (
        '.' in filename and
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    )

def get_passport_url(worker):
    if worker.passport:
        return url_for('static', filename=f'uploads/{worker.passport}') + f"?v={int(time.time())}"
    return url_for('static', filename='default.png')

def safe_date(value):
    """Convert YYYY-MM-DD string to date object. Returns None if invalid."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None

def login_required(role=None):
    """
    Protect routes with login and optional role-based access.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 1. Check login
            if 'role' not in session:
                flash("Please login first.", "warning")
                return redirect(url_for('auth.login'))

            # 2. Check role only if required
            if role is not None and session.get('role')!= role:
                flash("You are not authorized to access this page.", "danger")

                # redirect based on user role
                if session.get('role') == 'secretary':
                    return redirect(url_for('secretary.secretary_dashboard'))
                elif session.get('role') == 'admin':
                    return redirect(url_for('admin.admin_dashboard'))
                else:
                    return redirect(url_for('auth.login'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator