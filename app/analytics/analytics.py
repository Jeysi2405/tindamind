from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required
from sqlalchemy import func, extract
from app import db
from app.models import Product, Category, SalesTransaction, SalesItem
from app.auth.auth import admin_required

analytics_bp = Blueprint('analytics', __name__)


@analytics_bp.route('/', methods=['GET'])
@login_required
@admin_required
def index():
    """Owner & Admin Analytics View with KPIs, Top Products, and Chart.js datasets."""
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

    # KPI 2: Total Completed Transactions
    total_transactions = SalesTransaction.query.filter_by(status='Completed').count()

    # KPI 3: Average Order Value (AOV)
    all_time_sales = db.session.query(
        func.coalesce(func.sum(SalesTransaction.total_amount), 0.0)
    ).filter_by(status='Completed').scalar()
    aov = (float(all_time_sales) / total_transactions) if total_transactions > 0 else 0.0

    # KPI 4: Low Stock Alerts Count
    low_stock_count = Product.query.filter(
        Product.stock_quantity <= Product.reorder_level
    ).count()

    # Top Selling Products
    top_selling_query = (
        db.session.query(
            Product.product_name,
            func.sum(SalesItem.quantity).label('units_sold'),
            func.sum(SalesItem.sub_total).label('total_revenue')
        )
        .join(SalesItem, Product.product_id == SalesItem.product_id)
        .join(SalesTransaction, SalesItem.sale_id == SalesTransaction.sale_id)
        .filter(SalesTransaction.status == 'Completed')
        .group_by(Product.product_id, Product.product_name)
        .order_by(func.sum(SalesItem.quantity).desc())
        .limit(5)
        .all()
    )

    top_selling_products = [
        {
            'product_name': row.product_name,
            'units_sold': int(row.units_sold or 0),
            'total_revenue': float(row.total_revenue or 0.0)
        }
        for row in top_selling_query
    ]

    recent_sales = SalesTransaction.query.order_by(
        SalesTransaction.sale_date.desc()
    ).limit(15).all()

    # Chart 1: Revenue by Category
    categories = Category.query.order_by(Category.category_name.asc()).all()
    category_labels = []
    category_data = []
    for cat in categories:
        cat_revenue = (
            db.session.query(func.coalesce(func.sum(SalesItem.sub_total), 0.0))
            .join(Product, SalesItem.product_id == Product.product_id)
            .filter(Product.category_id == cat.category_id)
            .scalar()
        )
        category_labels.append(cat.category_name)
        category_data.append(float(cat_revenue))

    # Chart 2: Hourly Peak Sales Density (6 AM to 10 PM)
    hourly_hours = list(range(6, 23))
    hourly_labels = [f"{h:02d}:00" for h in hourly_hours]
    hourly_data = [
        SalesTransaction.query.filter(
            extract('hour', SalesTransaction.sale_date) == hour,
            SalesTransaction.status == 'Completed'
        ).count()
        for hour in hourly_hours
    ]

    return render_template(
        'analytics/analytics.html',
        today_sales=float(today_sales),
        total_transactions=total_transactions,
        today_transactions=total_transactions,
        aov=float(aov),
        avg_order_value=float(aov),
        low_stock_count=low_stock_count,
        top_selling_products=top_selling_products,
        recent_sales=recent_sales,
        category_labels=category_labels,
        category_data=category_data,
        hourly_labels=hourly_labels,
        hourly_data=hourly_data
    )


@analytics_bp.route('/api/sales-data', methods=['GET'])
@analytics_bp.route('/api/sales-summary', methods=['GET'])
@analytics_bp.route('/api/daily-revenue', methods=['GET'])
@login_required
@admin_required
def sales_summary_api():
    """
    Daily revenue JSON endpoint querying sales_transactions and sales_items.
    Returns daily revenue totals, transaction counts, and category breakdown.
    """
    days = request.args.get('days', default=7, type=int)
    start_cutoff = datetime.utcnow() - timedelta(days=days)

    daily_records = (
        db.session.query(
            func.date(SalesTransaction.sale_date).label('day'),
            func.coalesce(func.sum(SalesTransaction.total_amount), 0.0).label('daily_total'),
            func.count(SalesTransaction.sale_id).label('tx_count')
        )
        .filter(
            SalesTransaction.sale_date >= start_cutoff,
            SalesTransaction.status == 'Completed'
        )
        .group_by(func.date(SalesTransaction.sale_date))
        .order_by('day')
        .all()
    )

    daily_labels = [str(r.day) for r in daily_records]
    daily_revenue = [round(float(r.daily_total), 2) for r in daily_records]
    daily_counts = [int(r.tx_count) for r in daily_records]

    daily_breakdown = [
        {
            'date': str(r.day),
            'revenue': round(float(r.daily_total), 2),
            'transactions': int(r.tx_count)
        }
        for r in daily_records
    ]

    categories = Category.query.order_by(Category.category_name.asc()).all()
    cat_labels = []
    cat_values = []
    for cat in categories:
        val = (
            db.session.query(func.coalesce(func.sum(SalesItem.sub_total), 0.0))
            .join(Product, SalesItem.product_id == Product.product_id)
            .filter(Product.category_id == cat.category_id)
            .scalar()
        )
        cat_labels.append(cat.category_name)
        cat_values.append(round(float(val), 2))

    return jsonify({
        'success': True,
        'days': days,
        'daily_labels': daily_labels,
        'revenue': daily_revenue,
        'transactions': daily_counts,
        'daily_breakdown': daily_breakdown,
        'labels': cat_labels if cat_labels else daily_labels,
        'values': cat_values if cat_values else daily_revenue
    }), 200