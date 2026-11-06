from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required
from app import db
from app.models import Product, Category, SalesTransaction, SalesItem
from app.auth.auth import admin_required
from sqlalchemy import func, extract

analytics_bp = Blueprint('analytics',__name__)


@analytics_bp.route('/', methods=['GET'])
@login_required
@admin_required
def index():
    """Owner & Admin Analytics View.
    Aggregates financial KPIs, recent sales audit logs, and datasets for Chart.js.
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

    # KPI 2: Total Completed Transactions (All Time)
    total_transactions = SalesTransaction.query.filter_by(status='Completed').count()

    # Total Sales All-Time (for Average Order Value)
    all_time_sales = db.session.query(
        func.coalesce(func.sum(SalesTransaction.total_amount), 0.0)
    ).filter_by(status='Completed').scalar()

    # KPI 3: Average Order Value (AOV)
    aov = (float(all_time_sales) / total_transactions) if total_transactions > 0 else 0.0

    # KPI 4: Low Stock Alerts Count
    low_stock_count = Product.query.filter(
        Product.stock_quantity <= Product.reorder_level
    ).count()

    # Recent Audit Log of Sales (Latest 15)
    recent_sales = SalesTransaction.query.order_by(
        SalesTransaction.sale_date.desc()
    ).limit(15).all()

    # Chart 1: Weekly Revenue by Category
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

    return render_template(
        'analytics/analytics.html',
        today_sales=float(today_sales),
        total_transactions=total_transactions,
        aov=float(aov),
        low_stock_count=low_stock_count,
        recent_sales=recent_sales,
        category_labels=category_labels,
        category_data=category_data,
        hourly_labels=hourly_labels,
        hourly_data=hourly_data
    )


@analytics_bp.route('/api/sales-summary', methods=['GET'])
@login_required
@admin_required
def sales_summary_api():
    """JSON API endpoint returning aggregated sales metrics for dynamic client charts."""
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
        'labels': labels,
        'revenue': totals,
        'transactions': counts
    }), 200
