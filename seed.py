from datetime import date
from app import create_app, db
from app.models import Role, User, Category, Supplier, Product, MLForecast

app = create_app()


def seed_database():
    with app.app_context():
        print("Resetting database schema...")
        db.drop_all()
        db.create_all()

        # 1. Create System Roles
        admin_role = Role(role_name='Admin', description='Store Owner / System Administrator')
        cashier_role = Role(role_name='Cashier', description='Front-Desk Store Cashier')
        db.session.add_all([admin_role, cashier_role])
        db.session.commit()

        # 2. Create Initial Accounts
        admin_user = User(
            role_id=admin_role.role_id,
            full_name='James Huelar',
            username='admin',
            email='admin@tindamind.com'
        )
        admin_user.set_password('admin123')

        cashier_user = User(
            role_id=cashier_role.role_id,
            full_name='Store Cashier',
            username='cashier',
            email='cashier@tindamind.com'
        )
        cashier_user.set_password('cashier123')

        db.session.add_all([admin_user, cashier_user])
        db.session.commit()

        # 3. Create Master Product Categories
        cat_canned = Category(category_name='Canned Goods', description='Canned meat, sardines, and soups')
        cat_noodles = Category(category_name='Noodles', description='Instant noodles and ramen packs')
        cat_beverages = Category(category_name='Beverages', description='Juices, sodas, and bottled drinks')
        cat_snacks = Category(category_name='Snacks', description='Chips, biscuits, and crackers')
        cat_personal = Category(category_name='Personal Care', description='Soaps, shampoos, and hygiene items')
        cat_condiments = Category(category_name='Condiments', description='Sauces, seasonings, and cooking oils')

        db.session.add_all([cat_canned, cat_noodles, cat_beverages, cat_snacks, cat_personal, cat_condiments])
        db.session.commit()

        # 4. Create Partner Suppliers
        sup_monde = Supplier(
            supplier_name='Monde Nissin',
            contact_person='Maria Santos',
            phone='0917-888-1234',
            email='Monde_Nissin@gmail.com',
            address='Quezon City, Metro Manila',
            lead_time_days=3
        )
        sup_urc = Supplier(
            supplier_name='Universal Robina Corp',
            contact_person='Juan Dela Cruz',
            phone='0917-888-1234',
            email='Uni.RobinaCorp@gmail.com',
            address='Pasig City, Metro Manila',
            lead_time_days=2
        )
        sup_mega = Supplier(
            supplier_name='Mega Global Corp',
            contact_person='Elena Gomez',
            phone='0917-888-1234',
            email='MegaCorp@gmail.com',
            address='Valenzuela City Hub',
            lead_time_days=4
        )
        sup_coke = Supplier(
            supplier_name='Coca-Cola Beverages PH',
            contact_person='Mark Reyes',
            phone='0917-888-1234',
            email='CocaBeveragesPH@gmail.com',
            address='Taguig City, Metro Manila',
            lead_time_days=2
        )

        db.session.add_all([sup_monde, sup_urc, sup_mega, sup_coke])
        db.session.commit()

        # 5. Create Initial Catalog Products
        p1 = Product(
            product_name='Instant Noodles',
            category_id=cat_noodles.category_id,
            supplier_id=sup_monde.supplier_id,
            cost_price=11.00,
            selling_price=13.00,
            stock_quantity=9,
            reorder_level=10,
            risk_level='HIGH'
        )
        p2 = Product(
            product_name='Chips Classic',
            category_id=cat_snacks.category_id,
            supplier_id=sup_urc.supplier_id,
            cost_price=18.00,
            selling_price=21.00,
            stock_quantity=13,
            reorder_level=15,
            risk_level='MODERATE'
        )
        p3 = Product(
            product_name='Apple Juice',
            category_id=cat_beverages.category_id,
            supplier_id=sup_coke.supplier_id,
            cost_price=14.75,
            selling_price=16.00,
            stock_quantity=7,
            reorder_level=10,
            risk_level='HIGH'
        )
        p4 = Product(
            product_name='Cheapy Cheese Flavor',
            category_id=cat_snacks.category_id,
            supplier_id=sup_urc.supplier_id,
            cost_price=8.50,
            selling_price=13.00,
            stock_quantity=31,
            reorder_level=10,
            risk_level='LOW'
        )
        p5 = Product(
            product_name='Fish Cracker',
            category_id=cat_snacks.category_id,
            supplier_id=sup_urc.supplier_id,
            cost_price=7.00,
            selling_price=10.00,
            stock_quantity=19,
            reorder_level=10,
            risk_level='LOW'
        )
        p6 = Product(
            product_name='MEGA Sardines in Can',
            category_id=cat_canned.category_id,
            supplier_id=sup_mega.supplier_id,
            cost_price=23.50,
            selling_price=26.00,
            stock_quantity=28,
            reorder_level=10,
            risk_level='LOW'
        )
        p7 = Product(
            product_name='Ham',
            category_id=cat_canned.category_id,
            supplier_id=sup_mega.supplier_id,
            cost_price=80.00,
            selling_price=90.00,
            stock_quantity=34,
            reorder_level=10,
            risk_level='LOW'
        )
        p8 = Product(
            product_name='Coca Cola',
            category_id=cat_beverages.category_id,
            supplier_id=sup_coke.supplier_id,
            cost_price=20.00,
            selling_price=25.00,
            stock_quantity=23,
            reorder_level=10,
            risk_level='LOW'
        )
        p9 = Product(
            product_name='Vegetable Soup',
            category_id=cat_canned.category_id,
            supplier_id=sup_mega.supplier_id,
            cost_price=29.50,
            selling_price=32.00,
            stock_quantity=27,
            reorder_level=10,
            risk_level='LOW'
        )

        db.session.add_all([p1, p2, p3, p4, p5, p6, p7, p8, p9])
        db.session.commit()

        # 6. Create Machine Learning Stockout Predictions
        f1 = MLForecast(
            product_id=p1.product_id,
            forecast_date=date.today(),
            predicted_units=25.00,
            risk_category='HIGH',
            confidence_score=92.50,
            model_mae=1.20
        )
        f2 = MLForecast(
            product_id=p3.product_id,
            forecast_date=date.today(),
            predicted_units=18.00,
            risk_category='HIGH',
            confidence_score=88.00,
            model_mae=1.45
        )

        db.session.add_all([f1, f2])
        db.session.commit()

        print("--------------------------------------------------")
        print("TindaMind Database successfully initialized & seeded!")
        print("Admin Account   -> Username: admin   | Password: admin123")
        print("Cashier Account -> Username: cashier | Password: cashier123")
        print("--------------------------------------------------")


if __name__ == '__main__':
    seed_database()