from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from app import db
from app.models import Product, Category, Supplier
from app.auth.auth import admin_required
from sqlalchemy import func

inventory_bp = Blueprint('inventory', __name__)


@inventory_bp.route('/', methods=['GET'])
@login_required
@admin_required
def index():
    search_query = (request.args.get('search') or request.args.get('q') or '').strip()
    selected_category = (request.args.get('category') or request.args.get('cat') or '').strip()

    query = Product.query

    if search_query:
        query = query.filter(Product.product_name.ilike(f'%{search_query}%'))

    active_cat_name = ''
    if selected_category:
        if selected_category.isdigit():
            query = query.filter(Product.category_id == int(selected_category))
            cat_obj = db.session.get(Category, int(selected_category))
            if cat_obj:
                active_cat_name = cat_obj.category_name
        else:
            cat_obj = Category.query.filter_by(category_name=selected_category).first()
            if cat_obj:
                query = query.filter(Product.category_id == cat_obj.category_id)
                active_cat_name = cat_obj.category_name

    products = query.order_by(Product.product_name.asc()).all()
    categories = Category.query.order_by(Category.category_name.asc()).all()
    suppliers = Supplier.query.order_by(Supplier.supplier_name.asc()).all()

    total_skus = Product.query.count()
    low_stock_count = Product.query.filter(
        Product.stock_quantity > 0,
        Product.stock_quantity <= Product.reorder_level
    ).count()
    out_of_stock_count = Product.query.filter(Product.stock_quantity == 0).count()

    total_valuation = float(db.session.query(
        func.coalesce(func.sum(Product.stock_quantity * Product.selling_price), 0)
    ).scalar() or 0.0)

    return render_template(
        'inventory/inventory.html',
        products=products,
        categories=categories,
        suppliers=suppliers,
        total_skus=total_skus,
        low_stock_count=low_stock_count,
        low_stock=low_stock_count,
        out_of_stock_count=out_of_stock_count,
        out_of_stock=out_of_stock_count,
        total_valuation=total_valuation,
        total_val=total_valuation,
        search_query=search_query,
        selected_category=selected_category,
        active_cat=active_cat_name or selected_category
    )


@inventory_bp.route('/product/add', methods=['POST'])
@inventory_bp.route('/add', methods=['POST'])
@login_required
@admin_required
def add_product():
    product_name = request.form.get('product_name', '').strip()
    category_id = request.form.get('category_id')
    category_name = request.form.get('category_name', '').strip()
    supplier_id = request.form.get('supplier_id')
    cost_price = request.form.get('cost_price')
    selling_price = request.form.get('selling_price')
    stock_quantity = request.form.get('stock_quantity', '0')
    reorder_level = request.form.get('reorder_level', '5')

    if not category_id and category_name:
        cat_obj = Category.query.filter_by(category_name=category_name).first()
        if not cat_obj:
            cat_obj = Category(category_name=category_name, description=f'{category_name} items')
            db.session.add(cat_obj)
            db.session.flush()
        category_id = cat_obj.category_id

    if not supplier_id:
        first_sup = Supplier.query.first()
        if not first_sup:
            first_sup = Supplier(supplier_name='General Supplier', lead_time_days=3)
            db.session.add(first_sup)
            db.session.flush()
        supplier_id = first_sup.supplier_id

    if not product_name or not category_id or not supplier_id or cost_price is None or selling_price is None:
        flash('Please fill out all required fields to add a product.', 'danger')
        return redirect(url_for('inventory.index'))

    try:
        stock_val = int(stock_quantity) if stock_quantity else 0
        reorder_val = int(reorder_level) if reorder_level else 5
        new_product = Product(
            product_name=product_name,
            category_id=int(category_id),
            supplier_id=int(supplier_id),
            cost_price=float(cost_price),
            selling_price=float(selling_price),
            stock_quantity=stock_val,
            reorder_level=reorder_val,
            risk_level='HIGH' if stock_val <= reorder_val else 'LOW'
        )
        db.session.add(new_product)
        db.session.commit()
        flash(f'Product "{product_name}" created successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding product: {str(e)}', 'danger')

    return redirect(url_for('inventory.index'))


@inventory_bp.route('/product/edit/<int:product_id>', methods=['POST'])
@inventory_bp.route('/edit/<int:product_id>', methods=['POST'])
@login_required
@admin_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)

    product_name = request.form.get('product_name', '').strip()
    category_id = request.form.get('category_id')
    supplier_id = request.form.get('supplier_id')
    cost_price = request.form.get('cost_price')
    selling_price = request.form.get('selling_price')
    stock_quantity = request.form.get('stock_quantity')
    reorder_level = request.form.get('reorder_level')

    if not product_name or cost_price is None or selling_price is None:
        flash('Please complete all required product fields.', 'danger')
        return redirect(url_for('inventory.index'))

    try:
        product.product_name = product_name
        if category_id:
            product.category_id = int(category_id)
        if supplier_id:
            product.supplier_id = int(supplier_id)
        product.cost_price = float(cost_price)
        product.selling_price = float(selling_price)
        if stock_quantity is not None and stock_quantity != '':
            product.stock_quantity = int(stock_quantity)
        if reorder_level is not None and reorder_level != '':
            product.reorder_level = int(reorder_level)
        product.risk_level = 'HIGH' if product.stock_quantity <= product.reorder_level else 'LOW'

        db.session.commit()
        flash(f'Product "{product.product_name}" updated successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating product: {str(e)}', 'danger')

    return redirect(url_for('inventory.index'))


@inventory_bp.route('/product/restock/<int:product_id>', methods=['POST'])
@login_required
@admin_required
def restock_product(product_id):
    product = Product.query.get_or_404(product_id)
    data = request.get_json(silent=True) or request.form
    add_units = int(data.get('add_units', 10))
    try:
        product.stock_quantity = max(0, product.stock_quantity + add_units)
        product.risk_level = 'HIGH' if product.stock_quantity <= product.reorder_level else 'LOW'
        db.session.commit()
        return jsonify({
            'success': True,
            'product_id': product.product_id,
            'stock_quantity': product.stock_quantity,
            'reorder_level': product.reorder_level
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@inventory_bp.route('/product/delete/<int:product_id>', methods=['POST'])
@inventory_bp.route('/delete/<int:product_id>', methods=['POST'])
@login_required
@admin_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    try:
        name = product.product_name
        from app.models import MLForecast, PurchaseOrderItem, SalesItem
        MLForecast.query.filter_by(product_id=product.product_id).delete()
        PurchaseOrderItem.query.filter_by(product_id=product.product_id).delete()
        SalesItem.query.filter_by(product_id=product.product_id).delete()
        db.session.delete(product)
        db.session.commit()
        flash(f'Product "{name}" deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting product: {str(e)}', 'danger')

    return redirect(url_for('inventory.index'))


@inventory_bp.route('/category/add', methods=['POST'])
@login_required
@admin_required
def add_category():
    category_name = request.form.get('category_name', '').strip()
    description = request.form.get('description', '').strip()

    if not category_name:
        flash('Category name cannot be empty.', 'danger')
        return redirect(url_for('inventory.index'))

    existing = Category.query.filter_by(category_name=category_name).first()
    if existing:
        flash('Category already exists.', 'warning')
        return redirect(url_for('inventory.index'))

    try:
        new_cat = Category(category_name=category_name, description=description)
        db.session.add(new_cat)
        db.session.commit()
        flash(f'Category "{category_name}" created successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding category: {str(e)}', 'danger')

    return redirect(url_for('inventory.index'))
