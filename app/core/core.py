from datetime import date
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from app.models import Product, SalesTransaction, MLForecast, db
from app.auth.auth import get_user_role
from sqlalchemy import func

core_bp = Blueprint('core', __name__)


@core_bp.route('/')
def index():
    if current_user.is_authenticated:
        role_name = get_user_role(current_user)
        if role_name.lower() == 'cashier':
            return redirect(url_for('pos.index'))
        return redirect(url_for('core.dashboard'))
    return redirect(url_for('auth.login'))


@core_bp.route('/login')
def login():
    return redirect(url_for('auth.login'))


@core_bp.route('/logout')
def logout():
    return redirect(url_for('auth.logout'))


@core_bp.route('/dashboard')
@login_required
def dashboard():
    role_name = get_user_role(current_user)
    if role_name.lower() == 'cashier':
        return redirect(url_for('pos.index'))

    total_skus = Product.query.count()
    low_stock_count = Product.query.filter(
        Product.stock_quantity > 0,
        Product.stock_quantity <= Product.reorder_level
    ).count()
    out_of_stock_count = Product.query.filter(Product.stock_quantity == 0).count()

    today = date.today()
    today_sales = db.session.query(
        func.coalesce(func.sum(SalesTransaction.total_amount), 0)
    ).filter(func.date(SalesTransaction.sale_date) == today).scalar()

    today_transactions_count = SalesTransaction.query.filter(
        func.date(SalesTransaction.sale_date) == today
    ).count()

    recent_transactions = SalesTransaction.query.order_by(
        SalesTransaction.sale_date.desc()
    ).limit(5).all()

    high_risk_forecasts = MLForecast.query.filter_by(risk_category='HIGH').limit(5).all()

    return render_template(
        'core/dashboard.html',
        total_skus=total_skus,
        low_stock_count=low_stock_count,
        out_of_stock_count=out_of_stock_count,
        today_sales=today_sales,
        today_transactions_count=today_transactions_count,
        recent_transactions=recent_transactions,
        high_risk_forecasts=high_risk_forecasts
    )
