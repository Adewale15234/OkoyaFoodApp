# materials/__init__.py
from flask import Blueprint

materials_bp = Blueprint(
    'materials', 
    __name__, 
    template_folder='templates',
    url_prefix='/materials'
)

from . import routes  # import routes after creating blueprint