import os
import csv
import io
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, Response, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models import StoreSetting, User, Role, Product, SalesTransaction, Supplier, Category
from app.auth.auth import admin_required

settings_bp = Blueprint('settings', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'svg'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@settings_bp.route('/', methods=['GET'])
@login_required
@admin_required
def index():
    """Main Settings Dashboard with tabs for Store Profile, Payments, Staff, and Backup."""
    settings = StoreSetting.get_settings()
    staff_members = User.query.order_by(User.role_id.asc(), User.created_at.asc()).all()
    active_tab = request.args.get('tab', 'profile')

    # Data Backup Stats
    db_path = os.path.join(current_app.instance_path, 'tindamind.db')
    db_size_kb = 0.0
    if os.path.exists(db_path):
        db_size_kb = round(os.path.getsize(db_path) / 1024, 2)

    total_sales_count = SalesTransaction.query.count()
    total_products_count = Product.query.count()

    return render_template(
        'settings/settings.html',
        settings=settings,
        staff_members=staff_members,
        active_tab=active_tab,
        db_size_kb=db_size_kb,
        total_sales_count=total_sales_count,
        total_products_count=total_products_count
    )


@settings_bp.route('/profile', methods=['POST'])
@login_required
@admin_required
def update_profile():
    """Update Store Profile and Receipt Details."""
    settings = StoreSetting.get_settings()
    try:
        settings.store_name = request.form.get('store_name', '').strip() or 'TindaMind Sari-Sari Store'
        settings.tagline = request.form.get('tagline', '').strip()
        settings.store_address = request.form.get('store_address', '').strip()
        settings.contact_number = request.form.get('contact_number', '').strip()
        settings.receipt_footer = request.form.get('receipt_footer', '').strip() or 'Salamat sa pagbili! Balik po kayo.'

        db.session.commit()
        flash('Store Profile & Receipt settings saved successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error saving profile settings: {str(e)}', 'danger')

    return redirect(url_for('settings.index', tab='profile'))


@settings_bp.route('/payments', methods=['POST'])
@login_required
@admin_required
def update_payments():
    """Update Digital Payments & QR Configuration."""
    settings = StoreSetting.get_settings()
    try:
        settings.gcash_name = request.form.get('gcash_name', '').strip()
        settings.gcash_number = request.form.get('gcash_number', '').strip()
        settings.accept_gcash = bool(request.form.get('accept_gcash'))
        settings.accept_cash = bool(request.form.get('accept_cash'))

        # QR Image Upload
        if 'qr_image' in request.files:
            file = request.files['qr_image']
            if file and file.filename and allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = f"qr_payment_{int(datetime.utcnow().timestamp())}.{ext}"
                upload_dir = os.path.join(current_app.root_path, 'static', 'uploads')
                os.makedirs(upload_dir, exist_ok=True)
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)
                settings.qr_image = filename

        db.session.commit()
        flash('Digital payment settings updated successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating digital payment settings: {str(e)}', 'danger')

    return redirect(url_for('settings.index', tab='payments'))


@settings_bp.route('/staff/add', methods=['POST'])
@login_required
@admin_required
def add_staff():
    """Add a new Cashier / Staff member."""
    full_name = request.form.get('full_name', '').strip()
    username = request.form.get('username', '').strip().lower()
    password = request.form.get('password', '').strip()
    pin_code = request.form.get('pin_code', '').strip()

    if not full_name or not username or not password:
        flash('Full Name, Username, and Password are required.', 'danger')
        return redirect(url_for('settings.index', tab='staff'))

    existing = User.query.filter_by(username=username).first()
    if existing:
        flash(f'Username "{username}" is already taken.', 'warning')
        return redirect(url_for('settings.index', tab='staff'))

    cashier_role = Role.query.filter_by(role_name='Cashier').first()
    if not cashier_role:
        cashier_role = Role(role_name='Cashier', description='Front-Desk Store Cashier')
        db.session.add(cashier_role)
        db.session.commit()

    try:
        new_user = User(
            role_id=cashier_role.role_id,
            full_name=full_name,
            username=username,
            pin_code=pin_code if pin_code else None
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash(f'Cashier account "{full_name}" created successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating staff account: {str(e)}', 'danger')

    return redirect(url_for('settings.index', tab='staff'))


@settings_bp.route('/staff/edit/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def edit_staff(user_id):
    """Edit Cashier information or reset password/PIN."""
    user = User.query.get_or_404(user_id)
    full_name = request.form.get('full_name', '').strip()
    pin_code = request.form.get('pin_code', '').strip()
    new_password = request.form.get('password', '').strip()

    if not full_name:
        flash('Full name cannot be empty.', 'danger')
        return redirect(url_for('settings.index', tab='staff'))

    try:
        user.full_name = full_name
        if pin_code:
            user.pin_code = pin_code
        if new_password:
            user.set_password(new_password)

        db.session.commit()
        flash(f'Staff account "{user.username}" updated successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating staff member: {str(e)}', 'danger')

    return redirect(url_for('settings.index', tab='staff'))


@settings_bp.route('/staff/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_staff(user_id):
    """Delete a Cashier account."""
    if current_user.user_id == user_id:
        flash('You cannot delete your own logged-in account.', 'danger')
        return redirect(url_for('settings.index', tab='staff'))

    user = User.query.get_or_404(user_id)
    if user.role and user.role.role_name.lower() == 'admin':
        flash('Admin accounts cannot be deleted from the cashier management panel.', 'danger')
        return redirect(url_for('settings.index', tab='staff'))

    if user.sales_transactions and len(user.sales_transactions) > 0:
        flash(f'Cannot delete cashier "{user.full_name}" because they have {len(user.sales_transactions)} logged sales transaction(s). Reset their password or PIN instead to secure access.', 'warning')
        return redirect(url_for('settings.index', tab='staff'))

    try:
        name = user.full_name
        db.session.delete(user)
        db.session.commit()
        flash(f'Cashier "{name}" removed successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting cashier: {str(e)}', 'danger')

    return redirect(url_for('settings.index', tab='staff'))


@settings_bp.route('/backup/database', methods=['GET'])
@login_required
@admin_required
def backup_database():
    """One-click download of the complete SQLite database file."""
    db_path = os.path.join(current_app.instance_path, 'tindamind.db')
    if not os.path.exists(db_path):
        flash('Database file not found on server.', 'danger')
        return redirect(url_for('settings.index', tab='backup'))

    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    download_name = f"tindamind_backup_{timestamp}.db"
    return send_file(
        db_path,
        as_attachment=True,
        download_name=download_name,
        mimetype='application/x-sqlite3'
    )


@settings_bp.route('/backup/sales-csv', methods=['GET'])
@login_required
@admin_required
def backup_sales_csv():
    """Export all sales transactions and line items to CSV."""
    transactions = SalesTransaction.query.order_by(SalesTransaction.sale_date.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        'Sale ID', 'Date & Time', 'Cashier', 'Payment Method', 'Status',
        'Total Amount (PHP)', 'Amount Tendered (PHP)', 'Change Amount (PHP)', 'Items Summary'
    ])

    for tx in transactions:
        cashier_name = tx.user.full_name if tx.user else 'System'
        items_summary = "; ".join([f"{item.product.product_name if item.product else 'Item'} (x{item.quantity} @ P{item.unit_price})" for item in tx.items])
        writer.writerow([
            tx.sale_id,
            tx.sale_date.strftime('%Y-%m-%d %H:%M:%S') if tx.sale_date else '',
            cashier_name,
            tx.payment_method,
            tx.status,
            f"{tx.total_amount:.2f}",
            f"{tx.amount_tendered:.2f}",
            f"{tx.change_amount:.2f}",
            items_summary
        ])

    timestamp = datetime.utcnow().strftime('%Y%m%d')
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = f'attachment; filename=sales_backup_{timestamp}.csv'
    return response


@settings_bp.route('/backup/inventory-csv', methods=['GET'])
@login_required
@admin_required
def backup_inventory_csv():
    """Export complete product inventory catalog to CSV."""
    products = Product.query.order_by(Product.product_name.asc()).all()
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        'Product ID', 'SKU', 'Product Name', 'Category', 'Supplier',
        'Cost Price (PHP)', 'Selling Price (PHP)', 'Stock Quantity', 'Reorder Level', 'Risk Level'
    ])

    for p in products:
        cat_name = p.category.category_name if p.category else 'Uncategorized'
        sup_name = p.supplier.supplier_name if p.supplier else 'None'
        writer.writerow([
            p.product_id,
            f"TM-{p.product_id:03d}",
            p.product_name,
            cat_name,
            sup_name,
            f"{p.cost_price:.2f}",
            f"{p.selling_price:.2f}",
            p.stock_quantity,
            p.reorder_level,
            p.risk_level
        ])

    timestamp = datetime.utcnow().strftime('%Y%m%d')
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = f'attachment; filename=inventory_catalog_{timestamp}.csv'
    return response
