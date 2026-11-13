from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from app import db
from app.models import Product, Category, SalesTransaction, SalesItem, MLForecast
from app.auth.auth import admin_required
from sqlalchemy import func, extract

analytics_bp = Blueprint('analytics', __name__)


@analytics_bp.route('/', methods=['GET'])
@login_required
@admin_required
def index():
    """Owner & Admin Analytics View.
    Aggregates financial KPIs, recent sales audit logs, ML forecasts, and datasets for Chart.js.
    """
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = datetime.combine(date.today(), datetime.max.time())

    # KPI 1: Today's Revenue
    today_sales = db.session.query(
        func.coalesce(func.sum(SalesTransaction.total_amount), 0.0)
    ).filter(
        SalesTransaction.sale_date >= today_start,
        SalesTransaction.sale_date <= today_end,
        SalesTransaction.status == 'Completed'
    ).scalar()

    # KPI 2: Today's & Total Completed Transactions
    today_tx_count = SalesTransaction.query.filter(
        SalesTransaction.sale_date >= today_start,
        SalesTransaction.sale_date <= today_end,
        SalesTransaction.status == 'Completed'
    ).count()
    total_transactions = SalesTransaction.query.filter_by(status='Completed').count()

    # Total Sales All-Time (for Average Order Value fallback)
    all_time_sales = db.session.query(
        func.coalesce(func.sum(SalesTransaction.total_amount), 0.0)
    ).filter_by(status='Completed').scalar()

    # KPI 3: Average Order Value (AOV)
    if today_tx_count > 0:
        aov = float(today_sales) / today_tx_count
    else:
        aov = (float(all_time_sales) / total_transactions) if total_transactions > 0 else 0.0

    # KPI 4: Low Stock / High Stockout Risk Count
    low_stock_count = Product.query.filter(
        Product.stock_quantity <= Product.reorder_level
    ).count()

    # Top Selling Products (Today, with fallback to all-time if today is empty)
    top_selling_query = db.session.query(
        Product.product_name,
        func.sum(SalesItem.quantity).label('units_sold'),
        func.sum(SalesItem.sub_total).label('total_revenue')
    ).join(SalesItem, Product.product_id == SalesItem.product_id)\
     .join(SalesTransaction, SalesItem.sale_id == SalesTransaction.sale_id)\
     .filter(SalesTransaction.status == 'Completed',
             SalesTransaction.sale_date >= today_start,
             SalesTransaction.sale_date <= today_end)\
     .group_by(Product.product_id, Product.product_name)\
     .order_by(func.sum(SalesItem.quantity).desc())\
     .limit(5).all()

    if not top_selling_query:
        top_selling_query = db.session.query(
            Product.product_name,
            func.sum(SalesItem.quantity).label('units_sold'),
            func.sum(SalesItem.sub_total).label('total_revenue')
        ).join(SalesItem, Product.product_id == SalesItem.product_id)\
         .join(SalesTransaction, SalesItem.sale_id == SalesTransaction.sale_id)\
         .filter(SalesTransaction.status == 'Completed')\
         .group_by(Product.product_id, Product.product_name)\
         .order_by(func.sum(SalesItem.quantity).desc())\
         .limit(5).all()

    top_selling_products = [
        {
            'product_name': row.product_name,
            'units_sold': int(row.units_sold or 0),
            'total_revenue': float(row.total_revenue or 0.0)
        }
        for row in top_selling_query
    ]

    # Recent Audit Log of Sales (Latest 15)
    recent_sales = SalesTransaction.query.order_by(
        SalesTransaction.sale_date.desc()
    ).limit(15).all()

    db_sales_logs = []
    for tx in recent_sales:
        items_str = ', '.join([
            f"{item.product.product_name if item.product else 'Item'} (x{item.quantity})"
            for item in tx.items
        ])
        db_sales_logs.append({
            'txnId': f"#TM-{tx.sale_id:06d}",
            'dateKey': tx.sale_date.strftime('%Y-%m-%d') if tx.sale_date else date.today().strftime('%Y-%m-%d'),
            'timestamp': tx.sale_date.strftime('%b %d, %Y, %I:%M %p') if tx.sale_date else 'Today',
            'cashier': tx.user.full_name if tx.user else 'Store Cashier',
            'itemsSummary': items_str or 'POS Order',
            'paymentMethod': 'QR Code' if tx.payment_method.upper() in ('QR', 'GCASH', 'QR CODE') else 'Cash',
            'total': float(tx.total_amount)
        })

    # Chart 1: Revenue by Category
    categories = Category.query.order_by(Category.category_name.asc()).all()
    category_labels = []
    category_data = []

    for cat in categories:
        cat_revenue = db.session.query(
            func.coalesce(func.sum(SalesItem.sub_total), 0.0)
        ).join(Product, SalesItem.product_id == Product.product_id)\
         .filter(Product.category_id == cat.category_id).scalar()

        category_labels.append(cat.category_name)
        category_data.append(float(cat_revenue))

    if not category_labels:
        category_labels = ['Canned Goods', 'Noodles', 'Beverages', 'Snacks', 'Condiments']
        category_data = [0.0, 0.0, 0.0, 0.0, 0.0]

    # Chart 2: Hourly Peak Sales Density (6 AM to 10 PM Operating Window)
    hourly_hours = list(range(6, 23))
    hourly_labels = [f"{h:02d}:00" for h in hourly_hours]
    hourly_data = []

    for hour in hourly_hours:
        count_in_hour = SalesTransaction.query.filter(
            extract('hour', SalesTransaction.sale_date) == hour,
            SalesTransaction.status == 'Completed'
        ).count()
        hourly_data.append(count_in_hour)

    # ML Forecast & Stockout Risk rows
    products_all = Product.query.order_by(Product.stock_quantity.asc()).limit(8).all()
    forecast_rows = []
    for p in products_all:
        fc = MLForecast.query.filter_by(product_id=p.product_id).order_by(MLForecast.forecast_date.desc()).first()
        predicted_7d = int(round(float(fc.predicted_units))) if fc else max(10, p.reorder_level * 2)
        velocity = round(predicted_7d / 7.0, 1)
        days_left = round(p.stock_quantity / velocity, 1) if velocity > 0 else 99.0
        if p.stock_quantity <= p.reorder_level or days_left <= 2.5:
            risk = 'High Risk'
        elif p.stock_quantity <= (p.reorder_level * 1.5) or days_left <= 6.0:
            risk = 'Moderate Risk'
        else:
            risk = 'Low Risk'
        forecast_rows.append({
            'product_id': p.product_id,
            'product_name': p.product_name,
            'stock_quantity': p.stock_quantity,
            'reorder_level': p.reorder_level,
            'velocity': velocity,
            'predicted_7d': predicted_7d,
            'days_left': days_left,
            'risk': risk
        })

    return render_template(
        'analytics/analytics.html',
        today_sales=float(today_sales),
        total_transactions=total_transactions,
        today_transactions=today_tx_count,
        aov=float(aov),
        avg_order_value=float(aov),
        low_stock_count=low_stock_count,
        top_selling_products=top_selling_products,
        recent_sales=recent_sales,
        db_sales_logs=db_sales_logs,
        forecast_rows=forecast_rows,
        category_labels=category_labels,
        category_data=category_data,
        hourly_labels=hourly_labels,
        hourly_data=hourly_data
    )


@analytics_bp.route('/api/sales-data', methods=['GET'])
@analytics_bp.route('/api/sales-summary', methods=['GET'])
@login_required
@admin_required
def sales_summary_api():
    """JSON API endpoint returning aggregated sales metrics for dynamic client charts."""
    categories = Category.query.order_by(Category.category_name.asc()).all()
    cat_labels = []
    cat_values = []
    for cat in categories:
        val = db.session.query(
            func.coalesce(func.sum(SalesItem.sub_total), 0.0)
        ).join(Product, SalesItem.product_id == Product.product_id)\
         .filter(Product.category_id == cat.category_id).scalar()
        cat_labels.append(cat.category_name)
        cat_values.append(float(val))

    seven_days_ago = datetime.utcnow() - timedelta(days=7)

    daily_records = db.session.query(
        func.date(SalesTransaction.sale_date).label('day'),
        func.sum(SalesTransaction.total_amount).label('daily_total'),
        func.count(SalesTransaction.sale_id).label('tx_count')
    ).filter(
        SalesTransaction.sale_date >= seven_days_ago,
        SalesTransaction.status == 'Completed'
    ).group_by(func.date(SalesTransaction.sale_date))\
     .order_by('day').all()

    labels = [str(r.day) for r in daily_records]
    totals = [float(r.daily_total) for r in daily_records]
    counts = [int(r.tx_count) for r in daily_records]

    return jsonify({
        'labels': cat_labels if cat_labels else labels,
        'values': cat_values if cat_values else totals,
        'revenue': totals,
        'transactions': counts
    }), 200
