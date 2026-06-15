# materials/routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response, abort, session
from models import Material, MaterialTransaction
from extensions import db
from datetime import date
from sqlalchemy import func
import io, csv
from. import materials_bp

def is_admin():
    # Replace with your actual role check from session or flask-login
    return request.cookies.get('role') == 'admin' or session.get('role') == 'admin'

def get_current_user_name():
    return session.get('username', 'Unknown')

@materials_bp.route('/')
def dashboard():
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()

    query = Material.query
    if search:
        query = query.filter(Material.name.ilike(f'%{search}%'))
    if category:
        query = query.filter(Material.category == category)

    materials = query.order_by(Material.category, Material.name).all()
    categories = [c[0] for c in db.session.query(Material.category).distinct().all()]
    low_stock = [m for m in Material.query.all() if m.is_low_stock]

    grouped = {}
    for m in materials:
        grouped.setdefault(m.category, []).append(m)

    return render_template('materials/dashboard.html',
                           materials=materials,
                           grouped=grouped,
                           categories=categories,
                           low_stock=low_stock,
                           search=search,
                           selected_category=category,
                           is_admin=is_admin())

@materials_bp.route('/add-material', methods=['POST'])
def add_material():
    if not is_admin():
        flash('Only admin can add new materials', 'error')
        return redirect(url_for('materials.dashboard'))

    name = request.form.get('name', '').strip()
    unit = request.form.get('unit', '').strip()
    category = request.form.get('category', 'General').strip()
    threshold = request.form.get('low_stock_threshold', type=int, default=10)

    if not name or not unit:
        flash('Name and unit required', 'error')
        return redirect(url_for('materials.dashboard'))

    if Material.query.filter(func.lower(Material.name) == func.lower(name)).first():
        flash('Material already exists', 'error')
        return redirect(url_for('materials.dashboard'))

    material = Material(
        name=name,
        unit=unit,
        category=category,
        low_stock_threshold=threshold
    )
    db.session.add(material)
    db.session.commit()
    flash(f'Material {name} added. Use Stock In to add quantity.', 'success')
    return redirect(url_for('materials.dashboard'))

@materials_bp.route('/add-transaction', methods=['POST'])
def add_transaction():
    material_id = request.form.get('material_id', type=int)
    txn_type = request.form.get('type') # stock_in, usage, sale
    quantity = request.form.get('quantity', type=float)
    unit_price = request.form.get('unit_price', type=float)
    purpose = request.form.get('purpose', '').strip()
    client_supplier = request.form.get('client_supplier', '').strip()
    notes = request.form.get('notes', '').strip()

    material = Material.query.get_or_404(material_id)

    # Permission check: Secretary cannot do stock_in
    if txn_type == 'stock_in' and not is_admin():
        flash('Only admin can add stock', 'error')
        return redirect(url_for('materials.dashboard'))

    if quantity <= 0:
        flash('Quantity must be > 0', 'error')
        return redirect(url_for('materials.dashboard'))

    # For usage/sale, check stock
    if txn_type in ['usage', 'sale'] and quantity > material.remaining:
        flash(f'Not enough stock! Only {material.remaining} {material.unit} left', 'error')
        return redirect(url_for('materials.dashboard'))

    total_value = quantity * unit_price if unit_price else None

    recorded_by = request.form.get('recorded_by_name', '').strip()
    if not recorded_by:
        recorded_by = get_current_user_name()

    txn = MaterialTransaction(
        material_id=material_id,
        type=txn_type,
        quantity=quantity,
        unit_price=unit_price,
        total_value=total_value,
        purpose=purpose,
        client_supplier=client_supplier,
        notes=notes,
        recorded_by_name=recorded_by,
        is_verified=is_admin(), # Auto-verify if admin, else pending
        transaction_date=date.today()
    )
    db.session.add(txn)
    db.session.commit()

    if is_admin():
        flash(f'Transaction saved: {txn_type} {quantity} {material.unit}', 'success')
    else:
        flash('Entry submitted. Pending admin verification', 'info')
    return redirect(url_for('materials.dashboard'))

@materials_bp.route('/verify/<int:txn_id>', methods=['POST'])
def verify_transaction(txn_id):
    if not is_admin():
        abort(403)

    txn = MaterialTransaction.query.get_or_404(txn_id)
    txn.is_verified = True
    txn.verified_by_id = 1 # replace with current_user.id
    txn.verified_at = db.func.now()
    db.session.commit()
    flash('Transaction verified', 'success')
    return redirect(request.referrer or url_for('materials.dashboard'))

@materials_bp.route('/delete/<int:txn_id>', methods=['POST'])
def delete_transaction(txn_id):
    if not is_admin():
        abort(403)

    txn = MaterialTransaction.query.get_or_404(txn_id)
    db.session.delete(txn)
    db.session.commit()
    flash('Transaction deleted', 'success')
    return redirect(request.referrer or url_for('materials.dashboard'))

@materials_bp.route('/edit/<int:txn_id>', methods=['POST'])
def edit_transaction(txn_id):
    if not is_admin():
        abort(403)

    txn = MaterialTransaction.query.get_or_404(txn_id)
    txn.quantity = request.form.get('quantity', type=float)
    txn.unit_price = request.form.get('unit_price', type=float)
    txn.purpose = request.form.get('purpose')
    txn.client_supplier = request.form.get('client_supplier')
    txn.notes = request.form.get('notes')
    txn.recorded_by_name = request.form.get('recorded_by_name', txn.recorded_by_name).strip()
    txn.is_edited = True
    txn.edited_at = db.func.now()
    txn.total_value = txn.quantity * txn.unit_price if txn.unit_price else None
    db.session.commit()
    flash('Transaction updated', 'success')
    return redirect(url_for('materials.material_history', material_id=txn.material_id))

@materials_bp.route('/history/<int:material_id>')
def material_history(material_id):
    material = Material.query.get_or_404(material_id)
    transactions = material.transactions.order_by(MaterialTransaction.transaction_date.desc()).all()
    return render_template('materials/history.html', material=material, transactions=transactions, is_admin=is_admin())

@materials_bp.route('/print-analysis/<int:material_id>')
def print_analysis(material_id):
    material = Material.query.get_or_404(material_id)
    transactions = material.transactions.filter_by(is_verified=True).order_by(MaterialTransaction.transaction_date).all()
    return render_template('materials/print_analysis.html', material=material, transactions=transactions, date=date)

@materials_bp.route('/delete-material/<int:material_id>', methods=['POST'])
def delete_material(material_id):
    if not is_admin():
        abort(403)
    
    material = Material.query.get_or_404(material_id)
    material_name = material.name
    
    # Delete all transactions first to avoid foreign key constraint errors
    MaterialTransaction.query.filter_by(material_id=material_id).delete()
    
    # Then delete the material
    db.session.delete(material)
    db.session.commit()
    
    flash(f'Material "{material_name}" and all its transactions deleted', 'success')
    return redirect(url_for('materials.dashboard'))
@materials_bp.route('/export-csv')
def export_csv():
    materials = Material.query.order_by(Material.category, Material.name).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Material', 'Category', 'Unit', 'Total Bought', 'Total Used/Sold', 'Remaining', 'Status'])

    for m in materials:
        writer.writerow([
            m.name, m.category, m.unit,
            m.total_in, m.total_out, m.remaining,
            'Low Stock' if m.is_low_stock else 'OK'
        ])

    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = f'attachment; filename=materials_report_{date.today()}.csv'
    response.headers['Content-type'] = 'text/csv'
    return response