from datetime import datetime
from extensions import db
from sqlalchemy.sql import func
from sqlalchemy.orm import validates
from constants import (
    TRANSACTION_TYPES,
    INCOME_CATEGORIES,
    EXPENSE_CATEGORIES,
    PAYMENT_MODES,
    PAYMENT_STATUSES,
    ORDER_STATUSES
)
from werkzeug.security import generate_password_hash, check_password_hash

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_code = db.Column(db.String(50), unique=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200))
    phone = db.Column(db.String(20))
    preference = db.Column(db.String(200))
    gstin = db.Column(db.String(20))
    area_location = db.Column(db.String(100))
    registration_source = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    orders = db.relationship('Sales', backref='customer', lazy=True)

class Sales(db.Model):
    order_no = db.Column(db.String(50), primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    order_date = db.Column(db.DateTime, nullable=False)
    due_date = db.Column(db.DateTime)
    last_activity = db.Column(db.DateTime)
    pieces = db.Column(db.Integer)
    weight = db.Column(db.Float)
    gross_amount = db.Column(db.Float)
    discount = db.Column(db.Float)
    tax = db.Column(db.Float)
    net_amount = db.Column(db.Float)
    advance = db.Column(db.Float)
    paid = db.Column(db.Float)
    adjustment = db.Column(db.Float)
    balance = db.Column(db.Float)
    advance_received = db.Column(db.Float)
    advance_used = db.Column(db.Float)
    booked_by = db.Column(db.String(100))
    workshop_note = db.Column(db.Text)
    order_note = db.Column(db.Text)
    home_delivery = db.Column(db.Boolean, default=False)
    garments_inspected_by = db.Column(db.String(100))
    order_from_pos = db.Column(db.Boolean, default=True)
    package = db.Column(db.Boolean, default=False)
    package_type = db.Column(db.String(50))
    package_name = db.Column(db.String(100))
    feedback = db.Column(db.Text)
    tags = db.Column(db.String(200))
    comment = db.Column(db.Text)
    primary_services = db.Column(db.String(200))
    topup_service = db.Column(db.String(200))
    order_status = db.Column(db.String(50))
    last_payment_activity = db.Column(db.DateTime)
    coupon_code = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow) 

class Accounts(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaction_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    transaction_type = db.Column(db.String(50), nullable=False)  # Income/Expense/Transfer
    category = db.Column(db.String(100), nullable=False)  # Salary, Rent, Utilities, Sales, etc.
    sub_category = db.Column(db.String(100))  # More specific categorization
    
    # Amount details
    amount = db.Column(db.Float, nullable=False)
    tax_amount = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, nullable=False)
    
    # Payment details
    payment_mode = db.Column(db.String(50))  # Cash, UPI, Bank Transfer, Card, etc.
    payment_status = db.Column(db.String(50), default='Completed')  # Pending, Completed, Failed
    reference_no = db.Column(db.String(100))  # Check number, UPI ID, Transaction ID
    
    # Related entities
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    order_no = db.Column(db.String(50), db.ForeignKey('sales.order_no'))
    vendor_name = db.Column(db.String(100))
    
    # Additional details
    description = db.Column(db.Text)
    notes = db.Column(db.Text)
    attachments = db.Column(db.String(500))  # URLs or paths to receipts/invoices
    
    # Accounting fields
    fiscal_year = db.Column(db.String(10))
    accounting_period = db.Column(db.String(7))  # YYYY-MM
    
    # Reconciliation
    is_reconciled = db.Column(db.Boolean, default=False)
    reconciled_date = db.Column(db.DateTime)
    reconciled_by = db.Column(db.String(100))
    
    # Audit fields
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(100))
    modified_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    modified_by = db.Column(db.String(100))
    
    # Relationships
    customer = db.relationship('Customer', backref='transactions')
    order = db.relationship('Sales', backref='transactions')
    
    # Source field
    source = db.Column(db.String(50), default='manual')  # 'manual' or 'csv'

    def __repr__(self):
        return f'<Transaction {self.id}: {self.transaction_type} - {self.amount}>'

    @property
    def formatted_amount(self):
        return f"₹{self.amount:,.2f}"

    @classmethod
    def get_balance(cls, start_date=None, end_date=None):
        query = cls.query
        
        if start_date:
            query = query.filter(cls.transaction_date >= start_date)
        if end_date:
            query = query.filter(cls.transaction_date <= end_date)
            
        income = query.filter_by(transaction_type='Income').with_entities(
            func.sum(cls.total_amount)).scalar() or 0
        expense = query.filter_by(transaction_type='Expense').with_entities(
            func.sum(cls.total_amount)).scalar() or 0
            
        return income - expense 

    @validates('transaction_type')
    def validate_transaction_type(self, key, value):
        if value not in TRANSACTION_TYPES:
            raise ValueError(f"Invalid transaction type. Must be one of: {', '.join(TRANSACTION_TYPES)}")
        return value

    @validates('category')
    def validate_category(self, key, value):
        valid_categories = INCOME_CATEGORIES + EXPENSE_CATEGORIES
        if value not in valid_categories:
            raise ValueError(f"Invalid category. Must be one of: {', '.join(valid_categories)}")
        return value

    @validates('payment_mode')
    def validate_payment_mode(self, key, value):
        if value and value not in PAYMENT_MODES:
            raise ValueError(f"Invalid payment mode. Must be one of: {', '.join(PAYMENT_MODES)}")
        return value

    @validates('payment_status')
    def validate_payment_status(self, key, value):
        if value not in PAYMENT_STATUSES:
            raise ValueError(f"Invalid payment status. Must be one of: {', '.join(PAYMENT_STATUSES)}")
        return value

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')  # 'admin' or 'user'
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'