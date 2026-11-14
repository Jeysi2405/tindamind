from datetime import datetime
import json
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Product, Category, SalesTransaction, SalesItem

pos_bp = Blueprint('pos', __name__)


@pos_bp.route('/', methods=['GET'])
@login_required
def index():
    """Renders the Point-of-Sale (POS) terminal for Cashier and Admin roles."""
    products = Product.query.order_by(Product.product_name.asc()).all()
    categories = Category.query.order_by(Category.category_name.asc()).all()
    return render_template('pos/pos.html', products=products, categories=categories)


@pos_bp.route('/checkout', methods=['POST'])
@login_required
def checkout():
    """
    Processes an atomic POS checkout transaction (/pos/checkout & /api/pos/checkout).
    Saves sales_transactions and sales_items rows and deducts product stock_quantity.
    """
    if request.is_json:
        data = request.get_json() or {}
    else:
        data = request.form.to_dict()

    cart_raw = data.get('items') or data.get('cart') or []
    if isinstance(cart_raw, str):
        try:
            cart_items = json.loads(cart_raw)
        except Exception:
            cart_items = []
    elif isinstance(cart_raw, dict):
        cart_items = list(cart_raw.values())
    else:
        cart_items = cart_raw

    payment_method = str(data.get('payment_method', 'Cash')).strip()
    amount_tendered_raw = data.get('amount_tendered', 0.0)

    try:
        amount_tendered = float(amount_tendered_raw) if amount_tendered_raw else 0.0
    except (ValueError, TypeError):
        amount_tendered = 0.0

    if not cart_items:
        return jsonify({'success': False, 'message': 'Cannot checkout with an empty cart.'}), 400

    total_amount = 0.0
    products_to_update = []

    # Step 1: Validate stock quantity for all line items prior to any write
    for item in cart_items:
        product_id = item.get('id') or item.get('product_id')
        qty = int(item.get('qty') or item.get('quantity', 0))

        if qty <= 0:
            continue

        product = db.session.get(Product, int(product_id)) if product_id else None
        if not product:
            return jsonify({'success': False, 'message': f'Product ID {product_id} not found.'}), 404

        if product.stock_quantity < qty:
            return jsonify({
                'success': False,
                'message': (
                    f'Insufficient stock for "{product.product_name}". '
                    f'Available: {product.stock_quantity}, Requested: {qty}.'
                )
            }), 400

        item_unit_price = float(product.selling_price)
        item_subtotal = item_unit_price * qty
        total_amount += item_subtotal
        products_to_update.append((product, qty, item_unit_price, item_subtotal))

    if not products_to_update:
        return jsonify({'success': False, 'message': 'No valid product quantities provided.'}), 400

    # Step 2: Validate cash payment bounds
    if payment_method.upper() == 'CASH' and amount_tendered < total_amount:
        return jsonify({
            'success': False,
            'message': f'Tendered amount (PHP {amount_tendered:,.2f}) is less than total (PHP {total_amount:,.2f}).'
        }), 400

    change_amount = max(0.0, amount_tendered - total_amount) if payment_method.upper() == 'CASH' else 0.0
    if payment_method.upper() != 'CASH':
        amount_tendered = total_amount

    # Step 3: Atomic database transaction write + stock deduction
    try:
        sale = SalesTransaction(
            user_id=current_user.user_id,
            sale_date=datetime.utcnow(),
            payment_method=payment_method,
            status='Completed',
            total_amount=total_amount,
            amount_tendered=amount_tendered,
            change_amount=change_amount
        )
        db.session.add(sale)
        db.session.flush()

        updated_stock_map = {}
        for product, qty, unit_price, sub_total in products_to_update:
            sale_item = SalesItem(
                sale_id=sale.sale_id,
                product_id=product.product_id,
                quantity=qty,
                unit_price=unit_price,
                sub_total=sub_total
            )
            db.session.add(sale_item)

            # Deduct inventory stock
            product.stock_quantity -= qty
            product.risk_level = 'HIGH' if product.stock_quantity <= product.reorder_level else 'LOW'
            updated_stock_map[product.product_id] = product.stock_quantity

        db.session.commit()

        return jsonify({
            'success': True,
            'sale_id': sale.sale_id,
            'total_amount': round(total_amount, 2),
            'amount_tendered': round(amount_tendered, 2),
            'change_amount': round(change_amount, 2),
            'updated_stocks': updated_stock_map,
            'message': f'Sale #{sale.sale_id} processed successfully!'
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Transaction error: {str(e)}'}), 500


@pos_bp.route('/receipt/', methods=['GET'])
@login_required
def receipt(sale_id):
    """Returns JSON details for a completed transaction to render receipts."""
    sale = SalesTransaction.query.get_or_404(sale_id)
    items = SalesItem.query.filter_by(sale_id=sale.sale_id).all()
    receipt_items = []

    for item in items:
        product = db.session.get(Product, item.product_id)
        receipt_items.append({
            'product_name': product.product_name if product else 'Item Removed',
            'quantity': item.quantity,
            'unit_price': float(item.unit_price),
            'sub_total': float(item.sub_total)
        })

    return jsonify({
        'sale_id': sale.sale_id,
        'cashier_id': sale.user_id,
        'date': sale.sale_date.strftime('%Y-%m-%d %H:%M:%S'),
        'payment_method': sale.payment_method,
        'total_amount': float(sale.total_amount),
        'amount_tendered': float(sale.amount_tendered),
        'change_amount': float(sale.change_amount),
        'items': receipt_items
    }), 200