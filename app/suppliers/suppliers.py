from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_
from app import db
from app.models import Supplier, Product, PurchaseOrder, PurchaseOrderItem, MLForecast
from app.auth.auth import admin_required

suppliers_bp = Blueprint('suppliers', __name__)


def compute_recommended_qty(product: Product) -> int:
    """Calculates pre-filled restock quantity using ML 7-day forecast or reorder threshold."""
    latest_fc = (
        MLForecast.query.filter_by(product_id=product.product_id)
        .order_by(MLForecast.forecast_date.desc())
        .first()
    )
    if latest_fc and float(latest_fc.predicted_units) > 0:
        target_stock = int(round(float(latest_fc.predicted_units) * 1.2))
    else:
        target_stock = max(product.reorder_level * 3, 25)

    return max(10, target_stock - product.stock_quantity)


@suppliers_bp.route('/', methods=['GET'])
@login_required
@admin_required
def index():
    """Renders Supplier Directory, High-Risk Restock Recommendations, and Recent POs."""
    suppliers = Supplier.query.order_by(Supplier.supplier_name.asc()).all()
    recent_pos = PurchaseOrder.query.order_by(PurchaseOrder.order_date.desc()).limit(15).all()

    restock_candidates = (
        Product.query.filter(
            or_(
                Product.stock_quantity <= Product.reorder_level,
                Product.risk_level == 'HIGH'
            )
        )
        .order_by(Product.stock_quantity.asc())
        .all()
    )

    for item in restock_candidates:
        item.suggested_qty = compute_recommended_qty(item)

    high_risk_forecasts = MLForecast.query.filter_by(risk_category='HIGH').all()

    return render_template(
        'suppliers/suppliers.html',
        suppliers=suppliers,
        recent_pos=recent_pos,
        restock_candidates=restock_candidates,
        restock_items=restock_candidates,
        high_risk_forecasts=high_risk_forecasts
    )


@suppliers_bp.route('/po/create', methods=['POST'])
@suppliers_bp.route('/api/orders/generate-po', methods=['POST'])
@login_required
@admin_required
def create_po():
    """
    Creates pre-filled Purchase Orders (/suppliers/po/create & /api/orders/generate-po).
    Supports single-item 1-Click Restock and bulk auto-creation (`auto_high_risk=true`).
    """
    data = request.get_json(silent=True) or request.form

    # Mode A: Bulk 1-Click Auto-Restock for all HIGH-risk / low-stock products
    auto_high_risk = str(data.get('auto_high_risk', '')).lower() in ('true', '1', 'yes')
    if auto_high_risk:
        high_risk_products = Product.query.filter(
            or_(
                Product.risk_level == 'HIGH',
                Product.stock_quantity <= Product.reorder_level
            )
        ).all()

        if not high_risk_products:
            msg = 'No high-risk products currently require restocking.'
            if request.is_json:
                return jsonify({'success': True, 'created_pos': [], 'message': msg}), 200
            flash(msg, 'info')
            return redirect(url_for('suppliers.index'))

        created_pos = []
        try:
            for idx, prod in enumerate(high_risk_products, start=1):
                sup = prod.supplier or Supplier.query.first()
                qty = compute_recommended_qty(prod)
                unit_cost = float(prod.cost_price)
                total_cost = round(unit_cost * qty, 2)
                lead_days = sup.lead_time_days if (sup and sup.lead_time_days) else 3
                po_number = f"PO-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{idx}"

                po = PurchaseOrder(
                    supplier_id=sup.supplier_id,
                    created_by=current_user.user_id,
                    order_date=datetime.utcnow(),
                    expected_delivery=date.today() + timedelta(days=lead_days),
                    status='Pending',
                    po_number=po_number,
                    total_cost=total_cost
                )
                db.session.add(po)
                db.session.flush()

                db.session.add(PurchaseOrderItem(
                    purchase_order_id=po.purchase_order_id,
                    product_id=prod.product_id,
                    quantity=qty,
                    unit_cost=unit_cost,
                    sub_total=total_cost
                ))
                created_pos.append({
                    'po_id': po.purchase_order_id,
                    'po_number': po.po_number,
                    'product_name': prod.product_name,
                    'supplier_name': sup.supplier_name,
                    'quantity': qty,
                    'total_cost': total_cost
                })

            db.session.commit()
            if request.is_json:
                return jsonify({
                    'success': True,
                    'count': len(created_pos),
                    'created_pos': created_pos,
                    'message': f'Auto-generated {len(created_pos)} PO(s) for high-risk items.'
                }), 200
            flash(f'1-Click Restock: Created {len(created_pos)} PO(s) for high-risk items!', 'success')
            return redirect(url_for('suppliers.index'))
        except Exception as e:
            db.session.rollback()
            if request.is_json:
                return jsonify({'success': False, 'message': str(e)}), 500
            flash(f'Error auto-generating POs: {str(e)}', 'danger')
            return redirect(url_for('suppliers.index'))

    # Mode B: Single Product 1-Click Restock or Custom PO
    product_id = data.get('product_id')
    if not product_id:
        if request.is_json:
            return jsonify({'success': False, 'message': 'product_id is required.'}), 400
        flash('Missing required purchase order fields.', 'danger')
        return redirect(url_for('suppliers.index'))

    product = Product.query.get_or_404(int(product_id))
    supplier_id = data.get('supplier_id') or product.supplier_id
    supplier = Supplier.query.get_or_404(int(supplier_id)) if supplier_id else (product.supplier or Supplier.query.first())

    raw_qty = data.get('quantity')
    qty = int(raw_qty) if (raw_qty and int(raw_qty) > 0) else compute_recommended_qty(product)

    try:
        unit_cost = float(product.cost_price)
        total_cost = round(unit_cost * qty, 2)
        po_count = PurchaseOrder.query.count() + 1
        po_number = data.get('po_number') or f"PO-{date.today().year}-{po_count:04d}"
        if PurchaseOrder.query.filter_by(po_number=po_number).first():
            po_number = f"PO-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        lead_days = supplier.lead_time_days if (supplier and supplier.lead_time_days is not None) else 3
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

        if request.is_json:
            return jsonify({
                'success': True,
                'po_id': po.purchase_order_id,
                'po_number': po.po_number,
                'supplier_name': supplier.supplier_name,
                'product_name': product.product_name,
                'quantity': qty,
                'total_cost': float(po.total_cost),
                'order_date': po.order_date.strftime('%Y-%m-%d')
            }), 200
        flash(f'Purchase Order {po_number} created for {supplier.supplier_name}.', 'success')
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'success': False, 'message': str(e)}), 500
        flash(f'Error creating purchase order: {str(e)}', 'danger')

    return redirect(url_for('suppliers.index'))


@suppliers_bp.route('/supplier/add', methods=['POST'])
@login_required
@admin_required
def add_supplier():
    data = request.get_json(silent=True) or request.form
    supplier_name = (data.get('supplier_name') or '').strip()
    contact_person = (data.get('contact_person') or '').strip()
    phone = (data.get('phone') or '').strip()
    email = (data.get('email') or '').strip()
    address = (data.get('address') or '').strip()
    lead_time_days = data.get('lead_time_days', '3')

    if not supplier_name:
        if request.is_json:
            return jsonify({'success': False, 'message': 'Supplier name is required.'}), 400
        flash('Supplier name is required.', 'danger')
        return redirect(url_for('suppliers.index'))

    try:
        new_supplier = Supplier(
            supplier_name=supplier_name,
            contact_person=contact_person or None,
            phone=phone or None,
            email=email or None,
            address=address or None,
            lead_time_days=int(lead_time_days) if lead_time_days else 3
        )
        db.session.add(new_supplier)
        db.session.commit()
        if request.is_json:
            return jsonify({'success': True, 'supplier_id': new_supplier.supplier_id, 'supplier_name': new_supplier.supplier_name})
        flash(f'Supplier "{supplier_name}" added successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'success': False, 'message': str(e)}), 500
        flash(f'Error adding supplier: {str(e)}', 'danger')

    return redirect(url_for('suppliers.index'))


@suppliers_bp.route('/supplier/edit/', methods=['POST'])
@login_required
@admin_required
def edit_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    supplier_name = request.form.get('supplier_name', '').strip()
    if not supplier_name:
        flash('Supplier name cannot be empty.', 'danger')
        return redirect(url_for('suppliers.index'))

    try:
        supplier.supplier_name = supplier_name
        supplier.contact_person = request.form.get('contact_person', '').strip() or None
        supplier.phone = request.form.get('phone', '').strip() or None
        supplier.email = request.form.get('email', '').strip() or None
        supplier.address = request.form.get('address', '').strip() or None
        lead_time_days = request.form.get('lead_time_days')
        if lead_time_days is not None and lead_time_days != '':
            supplier.lead_time_days = int(lead_time_days)
        db.session.commit()
        flash(f'Supplier "{supplier.supplier_name}" updated successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating supplier: {str(e)}', 'danger')

    return redirect(url_for('suppliers.index'))


@suppliers_bp.route('/supplier/delete/', methods=['POST'])
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


@suppliers_bp.route('/po/update_status/', methods=['POST'])
@login_required
@admin_required
def update_po_status(po_id):
    po = PurchaseOrder.query.get_or_404(po_id)
    data = request.get_json(silent=True) or request.form
    new_status = (data.get('status') or 'Received').strip()

    if new_status not in ('Pending', 'Ordered', 'Received', 'Cancelled'):
        if request.is_json:
            return jsonify({'success': False, 'message': 'Invalid status.'}), 400
        flash('Invalid status updated.', 'danger')
        return redirect(url_for('suppliers.index'))

    updated_stocks = {}
    try:
        if new_status == 'Received' and po.status != 'Received':
            po_items = getattr(po, 'items', None) or PurchaseOrderItem.query.filter_by(purchase_order_id=po.purchase_order_id).all()
            for item in po_items:
                prod = db.session.get(Product, item.product_id)
                if prod:
                    prod.stock_quantity += item.quantity
                    prod.risk_level = 'HIGH' if prod.stock_quantity <= prod.reorder_level else 'LOW'
                    updated_stocks[str(prod.product_id)] = prod.stock_quantity

        po.status = new_status
        db.session.commit()
        if request.is_json:
            return jsonify({'success': True, 'po_id': po.purchase_order_id, 'status': po.status, 'updated_stocks': updated_stocks})
        flash(f'Purchase Order {po.po_number} updated to "{new_status}".', 'success')
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'success': False, 'message': str(e)}), 500
        flash(f'Error updating purchase order: {str(e)}', 'danger')

    return redirect(url_for('suppliers.index'))