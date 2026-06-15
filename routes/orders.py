from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_file
from extensions import db
from models import Order
from utils import login_required
from datetime import datetime
from openpyxl import Workbook
from io import BytesIO

orders_bp = Blueprint('orders', __name__, url_prefix='/orders')

@orders_bp.route('/client_form', methods=['GET', 'POST'])
@login_required()
def client_form():
    products = ["Soya Beans", "Cashew Nut", "Maize", "Rice"]

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        items = request.form.get('items')

        try:
            kilograms = float(request.form.get('kilograms') or 0)
            unit_price = float(request.form.get('unit_price') or 0)
        except ValueError:
            kilograms = 0
            unit_price = 0

        total_amount = kilograms * unit_price

        date_str = request.form.get('date')
        try:
            date_needed = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None
        except:
            date_needed = None

        order = Order(
            name=name,
            email=email,
            items=items,
            kilograms=kilograms,
            unit_price=unit_price,
            total_amount=total_amount,
            date_needed=date_needed,
            driver_name=request.form.get('driver_name'),
            vehicle_plate_number=request.form.get('vehicle_plate_number'),
            bank_name=request.form.get('bank_name'),
            account_number=request.form.get('account_number'),
            account_bank_name=request.form.get('account_bank_name'),
            description=request.form.get('description'),
            phone_number=request.form.get('phone_number'),
            status="Pending"
        )

        db.session.add(order)
        db.session.commit()

        return redirect(
            url_for('orders.orders_overview') if session['role'] == 'admin'
            else url_for('secretary.secretary_dashboard')
        )

    return render_template('client_form.html', products=products)

@orders_bp.route('/orders_overview')
@login_required(role='admin')
def orders_overview():
    all_orders = Order.query.order_by(Order.created_at.desc()).all()

    soya_orders = [o for o in all_orders if o.items and "soya" in o.items.lower()]
    cashew_orders = [o for o in all_orders if o.items and "cashew" in o.items.lower()]
    maize_orders = [o for o in all_orders if o.items and "maize" in o.items.lower()]
    rice_orders = [o for o in all_orders if o.items and "rice" in o.items.lower()]

    total_orders = len(all_orders)
    total_revenue = sum(o.total_amount or 0 for o in all_orders)

    today = datetime.utcnow().date()
    today_sales = sum(
        o.total_amount or 0
        for o in all_orders
        if o.created_at and o.created_at.date() == today
    )

    pending_orders = len([o for o in all_orders if o.status == "Pending"])
    confirmed_orders = len([o for o in all_orders if o.status == "Confirmed"])
    delivered_orders = len([o for o in all_orders if o.status == "Delivered"])

    product_stats = {}
    for o in all_orders:
        if o.items:
            key = o.items.lower()
            product_stats[key] = product_stats.get(key, 0) + 1

    return render_template(
        'orders_overview.html',
        soya_orders=soya_orders,
        cashew_orders=cashew_orders,
        maize_orders=maize_orders,
        rice_orders=rice_orders,
        all_orders=all_orders,
        total_orders=total_orders,
        total_revenue=total_revenue,
        today_sales=today_sales,
        pending_orders=pending_orders,
        confirmed_orders=confirmed_orders,
        delivered_orders=delivered_orders,
        product_stats=product_stats,
        now=datetime.utcnow()
    )

@orders_bp.route('/confirm_order/<int:order_id>', methods=['POST'])
@login_required(role='admin')
def confirm_order(order_id):
    order = Order.query.get_or_404(order_id)
    order.status = "Confirmed"
    order.confirmed_at = datetime.utcnow()
    db.session.commit()
    return redirect(url_for('orders.orders_overview'))

@orders_bp.route('/delete_order/<int:order_id>', methods=['POST'])
@login_required(role='admin')
def delete_order(order_id):
    order = Order.query.get_or_404(order_id)
    db.session.delete(order)
    db.session.commit()
    return redirect(url_for('orders.orders_overview'))

@orders_bp.route('/print_order/<int:order_id>')
@login_required()
def print_order(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('print_order.html', order=order)

@orders_bp.route('/export_order/<int:order_id>')
@login_required()
def export_order(order_id):
    order = Order.query.get_or_404(order_id)

    wb = Workbook()
    ws = wb.active
    ws.title = "Order"

    ws.append([
        "Client Name", "Email", "Phone", "Item",
        "Description", "Kilograms", "Unit Price",
        "Total", "Driver", "Vehicle",
        "Account Number", "Bank", "Date"
    ])

    ws.append([
        order.name,
        order.email,
        order.phone_number,
        order.items,
        order.description,
        order.kilograms,
        order.unit_price,
        order.total_amount,
        order.driver_name,
        order.vehicle_plate_number,
        order.account_number,
        order.account_bank_name,
        order.date_needed
    ])

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        download_name=f"order_{order.id}.xlsx",
        as_attachment=True
    )

@orders_bp.route('/export_all_orders')
@login_required(role='admin')
def export_all_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "All Orders"

    ws.append([
        "Client Name", "Email", "Phone", "Item",
        "Description", "Kilograms", "Unit Price",
        "Total", "Driver", "Vehicle",
        "Account Number", "Bank", "Date",
        "Status", "Created At"
    ])

    for order in orders:
        ws.append([
            order.name,
            order.email,
            order.phone_number,
            order.items,
            order.description,
            order.kilograms,
            order.unit_price,
            order.total_amount,
            order.driver_name,
            order.vehicle_plate_number,
            order.account_number,
            order.account_bank_name,
            str(order.date_needed) if order.date_needed else "",
            order.status,
            order.created_at.strftime('%Y-%m-%d %H:%M') if order.created_at else ""
        ])

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        download_name="all_orders.xlsx",
        as_attachment=True
    )