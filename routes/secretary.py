from flask import Blueprint, render_template, session, redirect, url_for, flash
from utils import login_required
from models import Worker

secretary_bp = Blueprint('secretary', __name__)

@secretary_bp.route('/secretary_dashboard')
@login_required(role='secretary')
def secretary_dashboard():
    return render_template(
        'secretary_dashboard.html',
        workers=Worker.query.filter_by(is_active=True).all(),
        total_workers=Worker.query.count(),
        active_count=Worker.query.filter_by(is_active=True).count(),
        inactive_count=Worker.query.filter_by(is_active=False).count()
    )