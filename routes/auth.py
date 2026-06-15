from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import os

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # --- Admin credentials ---
        ADMIN_USER = os.environ.get('ADMIN_USERNAME', 'admin')
        ADMIN_PASS = os.environ.get('ADMIN_PASSWORD', 'Alayinde001')

        # --- Secretary credentials ---
        SECRETARY_USER = os.environ.get('SECRETARY_USERNAME', 'secretary')
        SECRETARY_PASS = os.environ.get('SECRETARY_PASS', 'Sec001')

        # --- Check credentials ---
        if username == ADMIN_USER and password == ADMIN_PASS:
            session['role'] = 'admin'
            flash("Welcome Admin!", "success")
            return redirect(url_for('admin.admin_dashboard'))

        elif username == SECRETARY_USER and password == SECRETARY_PASS:
            session['role'] = 'secretary'
            flash("Welcome Secretary!", "success")
            return redirect(url_for('secretary.secretary_dashboard'))

        else:
            error = 'Invalid username or password.'

    return render_template('login.html', error=error)

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for('auth.login'))

@auth_bp.route('/logout_admin')
def logout_admin():
    session.clear()
    return redirect(url_for('auth.login'))