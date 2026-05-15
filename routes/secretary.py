from flask import Blueprint, render_template
from utils import login_required

secretary_bp = Blueprint('secretary', __name__)

@secretary_bp.route('/secretary_dashboard')
@login_required(role='secretary')
def secretary_dashboard():
    return render_template('secretary_dashboard.html')