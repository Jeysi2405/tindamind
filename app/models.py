from datetime import datetime
from flask_login import UserMixin
from app import db, bcrypt


class Role(db.Model):
    __tablename__ = 'roles'

    role_id = db.Column(db.Integer, primary_key=True)
    role_name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)

    users = db.relationship('User', backref='role', lazy=True)

    def __repr__(self):
        return f"<Role {self.role_name}>"


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    user_id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.role_id'), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    pin_code = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sales_transactions = db.relationship('SalesTransaction', backref='user', lazy=True)
    purchase_orders = db.relationship('PurchaseOrder', backref='creator', lazy=True)

    def get_id(self):
        return str(self.user_id)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"


class Category(db.Model):
    __tablename__ = 'categories'

    category_id = db.Column(db.Integer, primary_key=True)
    category_name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)

    products = db.relationship('Product', backref='category', lazy=True)

    def __repr__(self):
        return f"<Category {self.category_name}>"


class Supplier(db.Model):
    __tablename__ = 'suppliers'

    supplier_id = db.Column(db.Integer, primary_key=True)
    supplier_name = db.Column(db.String(150), nullable=False)
    contact_person = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    email = db.Column(db.String(150), nullable=True)
    address = db.Column(db.Text, nullable=True)
    lead_time_days = db.Column(db.Integer, default=3)
    receipt_number = db.Column(db.String(30), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    products = db.relationship('Product', backref='supplier', lazy=True)
    purchase_orders = db.relationship('PurchaseOrder', backref='supplier', lazy=True)

    def __repr__(self):
        return f"<Supplier {self.supplier_name}>"


class Product(db.Model):
    __tablename__ = 'products'

    product_id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.supplier_id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.category_id'), nullable=False)
    product_name = db.Column(db.String(150), nullable=False)
    cost_price = db.Column(db.Numeric(10, 2), nullable=False)
    selling_price = db.Column(db.Numeric(10, 2), nullable=False)
    stock_quantity = db.Column(db.Integer, default=0)
    reorder_level = db.Column(db.Integer, default=5)
    risk_level = db.Column(db.String(20), default='LOW')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sales_items = db.relationship('SalesItem', backref='product', lazy=True)
    po_items = db.relationship('PurchaseOrderItem', backref='product', lazy=True)
    forecasts = db.relationship('MLForecast', backref='product', lazy=True)

    def __repr__(self):
        return f"<Product {self.product_name}>"


class SalesTransaction(db.Model):
    __tablename__ = 'sales_transactions'

    sale_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    sale_date = db.Column(db.DateTime, default=datetime.utcnow)
    payment_method = db.Column(db.String(30), nullable=False, default='Cash')
    status = db.Column(db.String(20), default='Completed')
    total_amount = db.Column(db.Numeric(12, 2), nullable=False)
    amount_tendered = db.Column(db.Numeric(12, 2), nullable=False)
    change_amount = db.Column(db.Numeric(12, 2), nullable=False)

    items = db.relationship('SalesItem', backref='transaction', lazy=True)

    def __repr__(self):
        return f"<SalesTransaction #{self.sale_id}>"


class SalesItem(db.Model):
    __tablename__ = 'sales_items'

    sale_item_id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales_transactions.sale_id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    sub_total = db.Column(db.Numeric(12, 2), nullable=False)

    def __repr__(self):
        return f"<SalesItem Item #{self.sale_item_id} (Sale #{self.sale_id})>"


class PurchaseOrder(db.Model):
    __tablename__ = 'purchase_orders'

    purchase_order_id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.supplier_id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    expected_delivery = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(30), default='Pending')
    po_number = db.Column(db.String(30), unique=True, nullable=False)
    total_cost = db.Column(db.Numeric(12, 2), nullable=False)

    items = db.relationship('PurchaseOrderItem', backref='purchase_order', lazy=True)

    def __repr__(self):
        return f"<PurchaseOrder {self.po_number}>"


class PurchaseOrderItem(db.Model):
    __tablename__ = 'purchase_order_items'

    po_item_id = db.Column(db.Integer, primary_key=True)
    purchase_order_id = db.Column(db.Integer, db.ForeignKey('purchase_orders.purchase_order_id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_cost = db.Column(db.Numeric(10, 2), nullable=False)
    sub_total = db.Column(db.Numeric(12, 2), nullable=False)

    def __repr__(self):
        return f"<PurchaseOrderItem #{self.po_item_id}>"


class MLForecast(db.Model):
    __tablename__ = 'ml_forecasts'

    forecast_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=False)
    forecast_date = db.Column(db.Date, nullable=False)
    predicted_units = db.Column(db.Numeric(10, 2), nullable=False)
    risk_category = db.Column(db.String(20), nullable=False)
    confidence_score = db.Column(db.Numeric(5, 2), nullable=True)
    model_mae = db.Column(db.Numeric(10, 4), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<MLForecast Product #{self.product_id} - {self.risk_category}>"