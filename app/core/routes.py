from flask import current_app, flash, jsonify, redirect, render_template, request, url_for
from app.core import core_bp

MOCK_CATEGORIES = [
    {'category_id': 1, 'category_name': 'Canned Goods'},
    {'category_id': 2, 'category_name': 'Noodles'},
    {'category_id': 3, 'category_name': 'Beverages'},
    {'category_id': 4, 'category_name': 'Snacks'},
    {'category_id': 5, 'category_name': 'Condiments'}
]

MOCK_SUPPLIERS = [
    {
        'supplier_id': 1,
        'supplier_name': 'Monde Nissin',
        'lead_time_days': 3,
        'phone': '0917-888-1234',
        'email': 'monde.nissin@gmail.com',
        'address': '2 Martin St. Quezon City'
    },
    {
        'supplier_id': 2,
        'supplier_name': 'Universal Robina Corp',
        'lead_time_days': 2,
        'phone': '0917-888-1234',
        'email': 'uni.robinacorp@gmail.com',
        'address': '2 Martin St. Quezon City'
    },
    {
        'supplier_id': 3,
        'supplier_name': 'Mega Global Corp',
        'lead_time_days': 4,
        'phone': '0917-888-1234',
        'email': 'megacorp@gmail.com',
        'address': '2 Martin St. Quezon City'
    },
    {
        'supplier_id': 4,
        'supplier_name': 'Coca-Cola Beverages PH',
        'lead_time_days': 2,
        'phone': '0917-888-1234',
        'email': 'cocabeveragesph@gmail.com',
        'address': '2 Martin St. Quezon City'
    }
]

MOCK_PRODUCTS = [
    {
        'product_id': 1,
        'product_name': 'Vegetable Soup',
        'category_id': 1,
        'category': {'category_name': 'Canned Goods'},
        'supplier_id': 3,
        'supplier': {'supplier_name': 'Mega Global Corp'},
        'cost_price': 29.50,
        'selling_price': 32.00,
        'stock_quantity': 27,
        'reorder_level': 10
    },
    {
        'product_id': 2,
        'product_name': 'Chips Classic',
        'category_id': 4,
        'category': {'category_name': 'Snacks'},
        'supplier_id': 2,
        'supplier': {'supplier_name': 'Universal Robina Corp'},
        'cost_price': 18.00,
        'selling_price': 21.00,
        'stock_quantity': 13,
        'reorder_level': 15
    },
    {
        'product_id': 3,
        'product_name': 'MEGA Sardines In Can',
        'category_id': 1,
        'category': {'category_name': 'Canned Goods'},
        'supplier_id': 3,
        'supplier': {'supplier_name': 'Mega Global Corp'},
        'cost_price': 23.50,
        'selling_price': 26.00,
        'stock_quantity': 28,
        'reorder_level': 10
    },
    {
        'product_id': 4,
        'product_name': 'Instant Noodles',
        'category_id': 2,
        'category': {'category_name': 'Noodles'},
        'supplier_id': 1,
        'supplier': {'supplier_name': 'Monde Nissin'},
        'cost_price': 11.00,
        'selling_price': 13.00,
        'stock_quantity': 9,
        'reorder_level': 10
    },
    {
        'product_id': 5,
        'product_name': 'Apple Juice',
        'category_id': 3,
        'category': {'category_name': 'Beverages'},
        'supplier_id': 4,
        'supplier': {'supplier_name': 'Coca-Cola Beverages PH'},
        'cost_price': 14.00,
        'selling_price': 16.00,
        'stock_quantity': 7,
        'reorder_level': 10
    },
    {
        'product_id': 6,
        'product_name': 'Cheapy Cheese Flavor',
        'category_id': 4,
        'category': {'category_name': 'Snacks'},
        'supplier_id': 2,
        'supplier': {'supplier_name': 'Universal Robina Corp'},
        'cost_price': 11.00,
        'selling_price': 13.00,
        'stock_quantity': 31,
        'reorder_level': 10
    },
    {
        'product_id': 7,
        'product_name': 'Fish Cracker',
        'category_id': 4,
        'category': {'category_name': 'Snacks'},
        'supplier_id': 2,
        'supplier': {'supplier_name': 'Universal Robina Corp'},
        'cost_price': 8.50,
        'selling_price': 10.00,
        'stock_quantity': 19,
        'reorder_level': 10
    },
    {
        'product_id': 8,
        'product_name': 'Ham',
        'category_id': 1,
        'category': {'category_name': 'Canned Goods'},
        'supplier_id': 3,
        'supplier': {'supplier_name': 'Mega Global Corp'},
        'cost_price': 82.00,
        'selling_price': 90.00,
        'stock_quantity': 34,
        'reorder_level': 5
    }
]


@core_bp.route('/')
def index():
    return render_template('core/dashboard.html')


@core_bp.route('/health')
def health_check():
    db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
    return jsonify({
        "system": "TindaMind",
        "status": "healthy",
        "database_dialect": db_uri.split(':')[0] if db_uri else 'unknown'
    }), 200


@core_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        return redirect(url_for('core.index'))
    return render_template('login.html')


@core_bp.route('/pos')
def pos_view():
    return render_template('pos/pos.html', products=MOCK_PRODUCTS)


@core_bp.route('/inventory')
def inventory_view():
    search_query = request.args.get('q', '').strip().lower()
    category_filter = request.args.get('cat', '').strip()

    filtered = MOCK_PRODUCTS
    if search_query:
        filtered = [p for p in filtered if search_query in p['product_name'].lower()]
    if category_filter:
        filtered = [p for p in filtered if p['category']['category_name'] == category_filter]

    total_skus = len(MOCK_PRODUCTS)
    low_stock = sum(1 for p in MOCK_PRODUCTS if 0 < p['stock_quantity'] <= p['reorder_level'])
    out_of_stock = sum(1 for p in MOCK_PRODUCTS if p['stock_quantity'] == 0)
    total_val = sum(p['selling_price'] * p['stock_quantity'] for p in MOCK_PRODUCTS)

    return render_template(
        'inventory/inventory.html',
        products=filtered,
        categories=MOCK_CATEGORIES,
        suppliers=MOCK_SUPPLIERS,
        total_skus=total_skus,
        low_stock=low_stock,
        out_of_stock=out_of_stock,
        total_val=total_val,
        active_cat=category_filter,
        search_query=search_query
    )


@core_bp.route('/inventory/add', methods=['POST'])
def add_product():
    new_id = len(MOCK_PRODUCTS) + 1
    name = request.form.get('product_name', 'New Product')
    cat_id = int(request.form.get('category_id', 1))
    sup_id = int(request.form.get('supplier_id', 1))

    cat_name = next((c['category_name'] for c in MOCK_CATEGORIES if c['category_id'] == cat_id), 'General')
    sup_name = next((s['supplier_name'] for s in MOCK_SUPPLIERS if s['supplier_id'] == sup_id), 'General Supplier')

    MOCK_PRODUCTS.append({
        'product_id': new_id,
        'product_name': name,
        'category_id': cat_id,
        'category': {'category_name': cat_name},
        'supplier_id': sup_id,
        'supplier': {'supplier_name': sup_name},
        'cost_price': float(request.form.get('cost_price', 0)),
        'selling_price': float(request.form.get('selling_price', 0)),
        'stock_quantity': int(request.form.get('stock_quantity', 10)),
        'reorder_level': int(request.form.get('reorder_level', 5))
    })
    flash(f'Product "{name}" added successfully!', 'success')
    return redirect(url_for('core.inventory_view'))


@core_bp.route('/inventory/edit/<int:product_id>', methods=['POST'])
def edit_product(product_id):
    for p in MOCK_PRODUCTS:
        if p['product_id'] == product_id:
            p['product_name'] = request.form.get('product_name', p['product_name'])
            p['cost_price'] = float(request.form.get('cost_price', p['cost_price']))
            p['selling_price'] = float(request.form.get('selling_price', p['selling_price']))
            p['stock_quantity'] = int(request.form.get('stock_quantity', p['stock_quantity']))
            p['reorder_level'] = int(request.form.get('reorder_level', p['reorder_level']))
            break
    flash('Product updated successfully!', 'success')
    return redirect(url_for('core.inventory_view'))


@core_bp.route('/inventory/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    global MOCK_PRODUCTS
    MOCK_PRODUCTS = [p for p in MOCK_PRODUCTS if p['product_id'] != product_id]
    flash('Product removed from catalog.', 'info')
    return redirect(url_for('core.inventory_view'))


@core_bp.route('/suppliers')
def suppliers_view():
    restock_items = [p for p in MOCK_PRODUCTS if p['stock_quantity'] <= p['reorder_level']]
    return render_template('suppliers/suppliers.html', suppliers=MOCK_SUPPLIERS, restock_items=restock_items)


@core_bp.route('/analytics')
def analytics_view():
    return render_template('analytics/analytics.html')
