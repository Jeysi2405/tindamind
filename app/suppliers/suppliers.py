from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Supplier, Product, PurchaseOrder, PurchaseOrderItem, MLForecast
from app.auth.auth import admin_required

suppliers_bp = Blueprint('suppliers',__name__)


@suppliers_bp.route('/', methods=['GET'])
@login_required
@admin_required
def index():
    suppliers = Supplier.query.order_by(Supplier.supplier_name.asc()).all()
    recent_pos = PurchaseOrder.query.order_by(PurchaseOrder.order_date.desc()).limit(10).all()

    restock_candidates = Product.query.filter(
        Product.stock_quantity <= Product.reorder_level
    ).order_by(Product.stock_quantity.asc()).all()

    high_risk_forecasts = MLForecast.query.filter_by(risk_category='HIGH').all()

    return render_template(
        'suppliers/suppliers.html',
        suppliers=suppliers,
        recent_pos=recent_pos,
        restock_candidates=restock_candidates,
        high_risk_forecasts=high_risk_forecasts
    )


@suppliers_bp.route('/supplier/add', methods=['POST'])
@login_required
@admin_required
def add_supplier():
    supplier_name = request.form.get('supplier_name', '').strip()
    contact_person = request.form.get('contact_person', '').strip()
    phone = request.form.get('phone', '').strip()
    email = request.form.get('email', '').strip()
    address = request.form.get('address', '').strip()
    lead_time_days = request.form.get('lead_time_days', '3')

    if not supplier_name:
        flash('Supplier name is required.', 'danger')
        return redirect(url_for('suppliers.index'))

    try:
        new_supplier = Supplier(
            supplier_name=supplier_name,
            contact_person=contact_person if contact_person else None,
            phone=phone if phone else None,
            email=email if email else None,
            address=address if address else None,
            lead_time_days=int(lead_time_days) if lead_time_days else 3
        )
        db.session.add(new_supplier)
        db.session.commit()
        flash(f'Supplier "{supplier_name}" added successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding supplier: {str(e)}', 'danger')

    return redirect(url_for('suppliers.index'))


@suppliers_bp.route('/supplier/edit/<int:supplier_id>', methods=['POST'])
@login_required
@admin_required
def edit_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)

    supplier_name = request.form.get('supplier_name', '').strip()
    contact_person = request.form.get('contact_person', '').strip()
    phone = request.form.get('phone', '').strip()
    email = request.form.get('email', '').strip()
    address = request.form.get('address', '').strip()
    lead_time_days = request.form.get('lead_time_days')

    if not supplier_name:
        flash('Supplier name cannot be empty.', 'danger')
        return redirect(url_for('suppliers.index'))

    try:
        supplier.supplier_name = supplier_name
        supplier.contact_person = contact_person if contact_person else None
        supplier.phone = phone if phone else None
        supplier.email = email if email else None
        supplier.address = address if address else None
        if lead_time_days is not None and lead_time_days != '':
            supplier.lead_time_days = int(lead_time_days)

        db.session.commit()
        flash(f'Supplier "{supplier.supplier_name}" updated successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating supplier: {str(e)}', 'danger')

    return redirect(url_for('suppliers.index'))


@suppliers_bp.route('/supplier/delete/<int:supplier_id>', methods=['POST'])
@login_required
@admin_required
def delete_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    try:
        name = supplier.supplier_name
        db.session.delete(supplier)
        db.session.commit()
        flash(f'Supplier "{name}" deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting supplier: {str(e)}', 'danger')

    return redirect(url_for('suppliers.index'))


@suppliers_bp.route('/po/create', methods=['POST'])
@login_required
@admin_required
def create_po():
    supplier_id = request.form.get('supplier_id')
    product_id = request.form.get('product_id')
    quantity = request.form.get('quantity')

    if not supplier_id or not product_id or not quantity:
        flash('Missing required purchase order fields.', 'danger')
        return redirect(url_for('suppliers.index'))

    supplier = Supplier.query.get_or_404(int(supplier_id))
    product = Product.query.get_or_404(int(product_id))

    try:
        qty = int(quantity)
        unit_cost = float(product.cost_price)
        total_cost = unit_cost * qty

        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        po_number = f"PO-{timestamp}"

        lead_days = supplier.lead_time_days if supplier.lead_time_days is not None else 3
        expected_delivery = date.today() + timedelta(days=lead_days)

        po = PurchaseOrder(
            supplier_id=supplier.supplier_id,
            created_by=current_user.user_id,
            order_date=datetime.utcnow(),
            expected_delivery=expected_delivery,
            status='Pending',
            po_number=po_number,
            total_cost=total_cost
        )
        db.session.add(po)
        db.session.flush()

        po_item = PurchaseOrderItem(
            purchase_order_id=po.purchase_order_id,
            product_id=product.product_id,
            quantity=qty,
            unit_cost=unit_cost,
            sub_total=total_cost
        )
        db.session.add(po_item)

        db.session.commit()
        flash(f'Purchase Order {po_number} created for {supplier.supplier_name}.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating purchase order: {str(e)}', 'danger')

    return redirect(url_for('suppliers.index'))


@suppliers_bp.route('/po/update_status/<int:po_id>', methods=['POST'])
@login_required
@admin_required
def update_po_status(po_id):
    po = PurchaseOrder.query.get_or_404(po_id)
    new_status = request.form.get('status', '').strip()

    valid_statuses = ['Pending', 'Ordered', 'Received', 'Cancelled']
    if new_status not in valid_statuses:
        flash('Invalid status updated.', 'danger')
        return redirect(url_for('suppliers.index'))

    try:
        if new_status == 'Received' and po.status != 'Received':
            po_items = getattr(po, 'items', None) or getattr(po, 'purchase_order_items', None) or PurchaseOrderItem.query.filter_by(purchase_order_id=po.purchase_order_id).all()
            for item in po_items:
                prod = Product.query.get(item.product_id)
                if prod:
                    prod.stock_quantity += item.quantity

        po.status = new_status
        db.session.commit()
        flash(f'Purchase Order {po.po_number} updated to "{new_status}".', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating purchase order: {str(e)}', 'danger')

    return redirect(url_for('suppliers.index'))