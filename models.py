from datetime import date, datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    image = db.Column(db.String(255), nullable=True)  # New field for profile image filename



class Sale(db.Model):
    __tablename__ = 'sales'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    payment_method = db.Column(db.Enum('cash', 'card', 'mobile', name='payment_method_enum'), nullable=False)
    customer = db.Column(db.String(100))
    sale_date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Sale {self.product} x{self.quantity} ({self.payment_method})>"


class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_data = db.Column(db.LargeBinary)  # Store binary data for images

    def __repr__(self):
        return f"<Product {self.name} - ${self.price}>"


class Inventory(db.Model):
    __tablename__ = 'inventory'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    category = db.Column(db.String(100))
    quantity = db.Column(db.Integer)
    price = db.Column(db.Numeric(10, 2))
    location = db.Column(db.String(100))
    notes = db.Column(db.Text)
    updated_at = db.Column(db.Date, default=date.today)

    def __repr__(self):
        return f"<Inventory {self.name} - Qty: {self.quantity}>"


class ProductBatch(db.Model):
    __tablename__ = 'product_batches'

    id = db.Column(db.Integer, primary_key=True)
    batch_code = db.Column(db.String(100), unique=True, nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    production_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.Date, default=date.today)


class Supplier(db.Model):
    __tablename__ = 'supplier'  # all lowercase here

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    address = db.Column(db.Text, nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, name, address, phone, email):
        self.name = name
        self.address = address
        self.phone = phone
        self.email = email


class PurchaseOrder(db.Model):
    __tablename__ = 'purchase_orders'
    
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=False)  # lowercase supplier
    total_amount = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    supplier = db.relationship('Supplier', backref=db.backref('purchase_orders', lazy='dynamic'))
    items = db.relationship('PurchaseOrderItem', backref='purchase_order', cascade="all, delete-orphan", lazy=True)


class PurchaseOrderItem(db.Model):
    __tablename__ = 'purchase_order_items'

    id = db.Column(db.Integer, primary_key=True)
    purchase_order_id = db.Column(db.Integer, db.ForeignKey('purchase_orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)

    product = db.relationship('Product')

    def line_total(self):
        return self.quantity * self.unit_price


class SupplierPayment(db.Model):
    __tablename__ = 'supplier_payments'
    
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=False)  # lowercase supplier
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.Enum('cash', 'card', 'bank_transfer', name='payment_method_enum'), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    supplier = db.relationship('Supplier', backref=db.backref('supplier_payments', lazy='dynamic'))

class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    for_admin = db.Column(db.Boolean, default=True)
    for_employee = db.Column(db.Boolean, default=False)
    url = db.Column(db.String(255), nullable=True)
