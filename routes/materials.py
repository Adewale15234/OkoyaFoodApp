from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import db, Material, MaterialTransaction
from datetime import date
from sqlalchemy import or_

materials_bp = Blueprint('materials', __name__, url_prefix='/materials')

@materials_bp.route('/')
def materials_dashboard():
    search = request.args.get('search', '')
    category = request.args.get('category', '')

    query = Material.query
    if search:
        query = query.filter(Material.name.ilike(f'%{search}%'))
    if category:
        query = query.filter_by(category=category)

    materials = query.order_by(Material.name).all()
    categories = db.session.query(Material.category).distinct().all()

    # Low stock items
    low_stock = [m for m in Material.query.all() if m.is_low_stock]

    return render_template('materials_dashboard.html',
                         materials=materials,
                         categories=[c[0] for c in categories],
                         low_stock=low_stock,
                         search=search,
                         selected_category=category)

@materials_bp.route('/add-material', methods=['POST'])
def add_material():
    name = request.form.get('name').strip()
    unit = request.form.get('unit').strip()
    category = request.form.get('category', 'General')
    threshold = request.form.get('low_stock_threshold', type=int, default=10)

    if Material.query.filter_by(name=name).first():
        flash('Material already exists', 'error')
        return redirect(url_for('materials.materials_dashboard'))

    material = Material(name=name, unit=unit, category=category, low_stock_threshold=threshold)
    db.session.add(material)
    db.session.commit()
    flash(f'{name} added to inventory', 'success')
    return redirect(url_for('materials.materials_dashboard'))

@materials_bp.route('/transaction', methods=['POST'])
def add_transaction():
    material_id = request.form.get('material_id', type=int)
    trans_type = request.form.get('type') # stock_in, usage, sale
    quantity = request.form.get('quantity', type=float)
    unit_price = request.form.get('unit_price', type=float)
    purpose = request.form.get('purpose', '')
    client_supplier = request.form.get('client_supplier', '')
    notes = request.form.get('notes', '')

    material = Material.query.get_or_404(material_id)

    if trans_type in ['usage', 'sale'] and quantity > material.remaining:
        flash(f'Not enough stock! Only {material.remaining} {material.unit} left', 'error')
        return redirect(url_for('materials.materials_dashboard'))

    total_value = quantity * unit_price if unit_price else None

    txn = MaterialTransaction(
        material_id=material_id,
        type=trans_type,
        quantity=quantity,
        unit_price=unit_price,
        total_value=total_value,
        purpose=purpose,
        client_supplier=client_supplier,
        notes=notes,
        recorded_by='Admin' # replace with current_user.name
    )
    db.session.add(txn)
    db.session.commit()
    flash(f'Transaction recorded: {trans_type} {quantity} {material.unit}', 'success')
    return redirect(url_for('materials.materials_dashboard'))

@materials_bp.route('/history/<int:material_id>')
def material_history(material_id):
    material = Material.query.get_or_404(material_id)
    transactions = material.transactions.order_by(MaterialTransaction.transaction_date.desc()).all()
    return render_template('material_history.html', material=material, transactions=transactions)

@materials_bp.route('/export')
def export_csv():
    import csv
    from io import StringIO
    from flask import make_response

    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Material', 'Category', 'Unit', 'Total In', 'Total Out', 'Remaining', 'Low Stock'])

    for m in Material.query.all():
        cw.writerow([m.name, m.category, m.unit, m.total_in, m.total_out, m.remaining, 'YES' if m.is_low_stock else 'NO'])

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename=inventory_{date.today()}.csv"
    output.headers["Content-type"] = "text/csv"
    return output