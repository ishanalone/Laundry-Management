from flask import jsonify, request, send_from_directory, render_template, session, redirect, url_for, send_file
from datetime import datetime, timedelta
from sqlalchemy import or_, func
from models import Customer, Sales, Accounts, User, Employee, DailyBalance
from extensions import db
from constants import (
    TRANSACTION_TYPES,
    INCOME_CATEGORIES,
    EXPENSE_CATEGORIES,
    PAYMENT_MODES,
    PAYMENT_STATUSES
)
from functools import wraps
from services.whatsapp_service import WhatsAppService
from services.accounting_ai_service import AccountingAIAgent
import csv
from io import BytesIO, StringIO
import pandas as pd

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session or session['role'] != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def init_routes(app):
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            
            user = User.query.filter_by(username=username).first()
            
            if user and user.check_password(password) and user.is_active:
                session['user_id'] = user.id
                session['username'] = user.username
                session['role'] = user.role
                
                # Update last login
                user.last_login = datetime.utcnow()
                db.session.commit()
                
                return redirect(url_for('index'))
            
            return render_template('login.html', error='Invalid credentials')
            
        return render_template('login.html')

    @app.route('/logout')
    def logout():
        session.clear()
        return redirect(url_for('login'))

    @app.route('/')
    @login_required
    def index():
        return render_template('display.html')

    @app.route('/upload')
    def upload_page():
        return render_template('excel-file-upload.html')

    @app.route('/transaction')
    def transaction_page():
        return render_template('transaction_form.html')

    @app.route('/api/customers')
    def get_customers():
        customers = Customer.query.all()
        return jsonify([{
            'customer_code': c.customer_code,
            'name': c.name,
            'phone': c.phone,
            'address': c.address,
            'area_location': c.area_location
        } for c in customers])

    @app.route('/api/orders')
    def get_orders():
        try:
            # Get filter parameters from request
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 100, type=int)
            search = request.args.get('search', '').lower()
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            due_start = request.args.get('due_start')
            due_end = request.args.get('due_end')
            status = request.args.get('status')

            # Build query
            query = Sales.query.order_by(Sales.order_date.desc())

            # Apply filters
            if search:
                query = query.join(Customer).filter(
                    or_(
                        Sales.order_no.ilike(f'%{search}%'),
                        Customer.name.ilike(f'%{search}%')
                    )
                )
            
            if start_date:
                query = query.filter(Sales.order_date >= datetime.strptime(start_date, '%Y-%m-%d'))
            if end_date:
                query = query.filter(Sales.order_date <= datetime.strptime(end_date, '%Y-%m-%d'))
            
            if due_start:
                query = query.filter(Sales.due_date >= datetime.strptime(due_start, '%Y-%m-%d'))
            if due_end:
                query = query.filter(Sales.due_date <= datetime.strptime(due_end, '%Y-%m-%d'))
            
            if status and status != 'all':
                query = query.filter(Sales.order_status == status)

            # Get total count before pagination
            total_count = query.count()

            # Apply pagination
            orders = query.paginate(page=page, per_page=per_page, error_out=False)

            return jsonify({
                'orders': [{
                    'order_no': o.order_no,
                    'customer_name': o.customer.name if o.customer else '-',
                    'order_date': o.order_date.isoformat() if o.order_date else None,
                    'due_date': o.due_date.isoformat() if o.due_date else None,
                    'amount': float(o.net_amount or o.gross_amount or 0),
                    'status': o.order_status or 'Unprocessed'
                } for o in orders.items],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total_count,
                    'pages': orders.pages
                }
            })

        except Exception as e:
            app.logger.error(f"Error getting orders: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/transactions')
    def get_transactions():
        try:
            # Get pagination parameters
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 100, type=int)
            
            # Get filter parameters
            search = request.args.get('search', '').lower()
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            source = request.args.get('source')

            # Build query
            query = Accounts.query

            # Apply filters
            if search:
                query = query.filter(
                    or_(
                        Accounts.order_no.ilike(f'%{search}%'),
                        Accounts.description.ilike(f'%{search}%'),
                        Accounts.notes.ilike(f'%{search}%')
                    )
                )
            
            if start_date:
                query = query.filter(Accounts.transaction_date >= datetime.strptime(start_date, '%Y-%m-%d'))
            if end_date:
                query = query.filter(Accounts.transaction_date <= datetime.strptime(end_date, '%Y-%m-%d'))
            
            if source and source != 'all':
                query = query.filter(Accounts.source == source)

            # Order by date
            query = query.order_by(Accounts.transaction_date.desc())
            
            # Get total count before pagination
            total_count = query.count()
            
            # Apply pagination
            transactions = query.paginate(page=page, per_page=per_page, error_out=False)
            
            def format_date(date):
                if not date:
                    return None
                try:
                    if isinstance(date, str):
                        date = pd.to_datetime(date, dayfirst=True)
                    return date.strftime('%d-%m-%Y')
                except Exception as e:
                    app.logger.error(f"Error formatting date {date}: {str(e)}")
                    return None

            return jsonify({
                'transactions': [{
                    'id': t.id,
                    'transaction_date': format_date(t.transaction_date),
                    'order_no': t.order_no,
                    'transaction_type': t.transaction_type,
                    'amount': float(t.amount) if t.amount else 0,
                    'payment_mode': t.payment_mode,
                    'reference_no': t.reference_no,
                    'description': t.description,
                    'notes': t.notes,
                    'source': t.source
                } for t in transactions.items],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total_count,
                    'pages': transactions.pages
                }
            })
        except Exception as e:
            app.logger.error(f"Error getting transactions: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/customers/<customer_code>', methods=['GET'])
    def get_customer(customer_code):
        try:
            customer = Customer.query.filter_by(customer_code=customer_code).first()
            if not customer:
                return jsonify({'error': 'Customer not found'}), 404
                
            return jsonify({
                'id': customer.id,
                'customer_code': customer.customer_code,
                'name': customer.name,
                'address': customer.address,
                'phone': customer.phone,
                'preference': customer.preference,
                'gstin': customer.gstin,
                'area_location': customer.area_location,
                'registration_source': customer.registration_source,
                'created_at': customer.created_at.isoformat() if customer.created_at else None
            }), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/orders/<order_no>', methods=['GET'])
    def get_order(order_no):
        try:
            order = Sales.query.get(order_no)
            if not order:
                return jsonify({'error': 'Order not found'}), 404
                
            return jsonify({
                'order_no': order.order_no,
                'customer_id': order.customer_id,
                'order_date': order.order_date.isoformat() if order.order_date else None,
                'due_date': order.due_date.isoformat() if order.due_date else None,
                'last_activity': order.last_activity.isoformat() if order.last_activity else None,
                'pieces': order.pieces,
                'weight': order.weight,
                'gross_amount': order.gross_amount,
                'discount': order.discount,
                'tax': order.tax,
                'net_amount': order.net_amount,
                'advance': order.advance,
                'paid': order.paid,
                'adjustment': order.adjustment,
                'balance': order.balance,
                'advance_received': order.advance_received,
                'advance_used': order.advance_used,
                'booked_by': order.booked_by,
                'workshop_note': order.workshop_note,
                'order_note': order.order_note,
                'home_delivery': order.home_delivery,
                'garments_inspected_by': order.garments_inspected_by,
                'order_from_pos': order.order_from_pos,
                'package': order.package,
                'package_type': order.package_type,
                'package_name': order.package_name,
                'feedback': order.feedback,
                'tags': order.tags,
                'comment': order.comment,
                'primary_services': order.primary_services,
                'topup_service': order.topup_service,
                'order_status': order.order_status,
                'last_payment_activity': order.last_payment_activity.isoformat() if order.last_payment_activity else None,
                'coupon_code': order.coupon_code,
                'created_at': order.created_at.isoformat() if order.created_at else None
            }), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500 

    @app.route('/api/constants', methods=['GET'])
    def get_constants():
        return jsonify({
            'TRANSACTION_TYPES': TRANSACTION_TYPES,
            'INCOME_CATEGORIES': INCOME_CATEGORIES,
            'EXPENSE_CATEGORIES': EXPENSE_CATEGORIES,
            'PAYMENT_MODES': PAYMENT_MODES,
            'PAYMENT_STATUSES': PAYMENT_STATUSES
        })

    @app.route('/api/customers/search', methods=['GET'])
    def search_customers():
        query = request.args.get('q', '')
        if len(query) < 2:
            return jsonify([])
        
        customers = Customer.query.filter(
            or_(
                Customer.name.ilike(f'%{query}%'),
                Customer.customer_code.ilike(f'%{query}%'),
                Customer.phone.ilike(f'%{query}%')
            )
        ).limit(10).all()
        
        return jsonify([{
            'id': c.id,
            'name': c.name,
            'customer_code': c.customer_code,
            'phone': c.phone
        } for c in customers])

    @app.route('/api/transactions', methods=['POST'])
    def add_transaction():
        try:
            data = request.json
            data['source'] = 'manual'  # Add source for manually added transactions
            
            # Convert string amounts to float
            for field in ['amount', 'tax_amount', 'total_amount']:
                if data.get(field):
                    data[field] = float(data[field])
            
            # Convert date string to datetime
            if data.get('transaction_date'):
                data['transaction_date'] = datetime.strptime(data['transaction_date'], '%Y-%m-%d')
            
            # Convert empty strings to None
            for key in data:
                if data[key] == '':
                    data[key] = None
            
            transaction = Accounts(**data)
            db.session.add(transaction)
            db.session.commit()
            
            return jsonify({'message': 'Transaction added successfully', 'id': transaction.id}), 201
        
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400 

    @app.route('/admin')
    @login_required
    @admin_required
    def admin_panel():
        return render_template('admin.html')

    @app.route('/api/users', methods=['GET'])
    @login_required
    @admin_required
    def get_users():
        users = User.query.all()
        return jsonify([{
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'is_active': user.is_active,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'last_login': user.last_login.isoformat() if user.last_login else None
        } for user in users])

    @app.route('/api/users', methods=['POST'])
    @login_required
    @admin_required
    def create_user():
        try:
            data = request.json
            
            # Check if username or email already exists
            if User.query.filter_by(username=data['username']).first():
                return jsonify({'error': 'Username already exists'}), 400
            if User.query.filter_by(email=data['email']).first():
                return jsonify({'error': 'Email already exists'}), 400
            
            user = User(
                username=data['username'],
                email=data['email'],
                role=data['role'],
                is_active=True
            )
            user.set_password(data['password'])
            
            db.session.add(user)
            db.session.commit()
            
            return jsonify({'message': 'User created successfully'}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400

    @app.route('/api/users/<int:user_id>', methods=['PUT'])
    @login_required
    @admin_required
    def update_user(user_id):
        try:
            user = User.query.get(user_id)
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            data = request.json
            if 'username' in data and data['username'] != user.username:
                if User.query.filter_by(username=data['username']).first():
                    return jsonify({'error': 'Username already exists'}), 400
                user.username = data['username']
            
            if 'email' in data and data['email'] != user.email:
                if User.query.filter_by(email=data['email']).first():
                    return jsonify({'error': 'Email already exists'}), 400
                user.email = data['email']
            
            if 'password' in data:
                user.set_password(data['password'])
            
            if 'role' in data:
                user.role = data['role']
            
            if 'is_active' in data:
                user.is_active = data['is_active']
            
            db.session.commit()
            return jsonify({'message': 'User updated successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400 

    @app.route('/dashboard')
    @login_required
    @admin_required
    def dashboard():
        return render_template('dashboard.html')

    @app.route('/api/dashboard/stats')
    @login_required
    @admin_required
    def get_dashboard_stats():
        try:
            # Get date range (default: last 30 days)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)

            try:
                # Total orders
                total_orders = Sales.query.count()
                recent_orders = Sales.query.filter(
                    Sales.order_date >= start_date
                ).count()
                print(f"Orders count: {total_orders}, Recent: {recent_orders}")
            except Exception as e:
                print(f"Error getting orders count: {str(e)}")
                total_orders = recent_orders = 0

            try:
                # Total customers
                total_customers = Customer.query.count()
                recent_customers = Customer.query.filter(
                    Customer.created_at >= start_date
                ).count()
                print(f"Customers count: {total_customers}, Recent: {recent_customers}")
            except Exception as e:
                print(f"Error getting customers count: {str(e)}")
                total_customers = recent_customers = 0

            try:
                # Revenue stats
                total_revenue = db.session.query(
                    func.sum(Accounts.amount)
                ).filter(
                    Accounts.transaction_type == 'Income',
                    Accounts.category == 'Sales'
                ).scalar()
                total_revenue = float(total_revenue) if total_revenue else 0

                recent_revenue = db.session.query(
                    func.sum(Accounts.amount)
                ).filter(
                    Accounts.transaction_type == 'Income',
                    Accounts.category == 'Sales',
                    Accounts.transaction_date >= start_date
                ).scalar()
                recent_revenue = float(recent_revenue) if recent_revenue else 0
                print(f"Revenue - Total: {total_revenue}, Recent: {recent_revenue}")
            except Exception as e:
                print(f"Error getting revenue: {str(e)}")
                total_revenue = recent_revenue = 0

            try:
                # Order status distribution
                status_distribution = db.session.query(
                    Sales.order_status,
                    func.count(Sales.order_no)
                ).group_by(
                    Sales.order_status
                ).all()
                status_dict = {
                    status if status else 'Unprocessed': count 
                    for status, count in status_distribution
                }
                print(f"Status distribution: {status_dict}")
            except Exception as e:
                print(f"Error getting status distribution: {str(e)}")
                status_dict = {}

            try:
                # Daily revenue
                print("Fetching daily revenue...")
                
                # First, let's check if we have any transactions in this period
                transaction_check = db.session.query(Accounts).filter(
                    Accounts.transaction_type == 'Income',
                    Accounts.category == 'Sales',
                    Accounts.transaction_date >= start_date,
                    Accounts.transaction_date <= end_date
                ).first()
                print(f"Any transactions found: {transaction_check is not None}")

                # Get daily revenue with more detailed date handling
                daily_revenue = db.session.query(
                    func.date(Accounts.transaction_date).label('date'),
                    func.sum(Accounts.amount).label('amount')
                ).filter(
                    Accounts.transaction_type == 'Income',
                    Accounts.category == 'Sales',
                    Accounts.transaction_date >= start_date,
                    Accounts.transaction_date <= end_date
                ).group_by(
                    func.date(Accounts.transaction_date)
                ).order_by(
                    func.date(Accounts.transaction_date)
                ).all()

                print(f"Raw daily revenue data: {daily_revenue}")

                # Fill in missing dates
                all_dates = []
                current_date = start_date
                
                # Create a dictionary of existing revenues
                revenue_dict = {}
                for date, amount in daily_revenue:
                    try:
                        date_str = date.strftime('%Y-%m-%d')
                        revenue_dict[date_str] = float(amount if amount is not None else 0)
                        print(f"Processed revenue for {date_str}: {revenue_dict[date_str]}")
                    except Exception as e:
                        print(f"Error processing date {date}: {str(e)}")

                # Fill in all dates
                while current_date.date() <= end_date.date():
                    date_str = current_date.date().strftime('%Y-%m-%d')
                    amount = revenue_dict.get(date_str, 0.0)
                    all_dates.append({
                        'date': date_str,
                        'amount': amount
                    })
                    print(f"Added date {date_str} with amount {amount}")
                    current_date += timedelta(days=1)

                print(f"Final daily revenue data: {all_dates}")
                print(f"Number of dates: {len(all_dates)}")

            except Exception as e:
                print(f"Error getting daily revenue: {str(e)}")
                print("Traceback:", traceback.format_exc())
                all_dates = []

            try:
                # Payment mode distribution
                payment_distribution = db.session.query(
                    Accounts.payment_mode,
                    func.sum(Accounts.amount)
                ).filter(
                    Accounts.transaction_type == 'Income',
                    Accounts.category == 'Sales'
                ).group_by(
                    Accounts.payment_mode
                ).all()
                payment_dict = {
                    mode if mode else 'Unknown': float(amount or 0)
                    for mode, amount in payment_distribution
                }
                print(f"Payment distribution: {payment_dict}")
            except Exception as e:
                print(f"Error getting payment distribution: {str(e)}")
                payment_dict = {}

            return jsonify({
                'total_orders': total_orders,
                'recent_orders': recent_orders,
                'total_customers': total_customers,
                'recent_customers': recent_customers,
                'total_revenue': total_revenue,
                'recent_revenue': recent_revenue,
                'status_distribution': status_dict,
                'daily_revenue': all_dates,
                'payment_distribution': payment_dict
            })

        except Exception as e:
            print(f"Main dashboard error: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500 

    whatsapp_service = WhatsAppService()

    @app.route('/api/customer-engagement/send-message', methods=['POST'])
    def send_whatsapp_message():
        try:
            data = request.json
            phone = data.get('phone')
            message = data.get('message')
            
            if not phone or not message:
                return jsonify({'error': 'Phone and message are required'}), 400
            
            result = whatsapp_service.send_message(phone, message)
            return jsonify(result), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/customer-engagement/send-bulk-message', methods=['POST'])
    def send_bulk_message():
        try:
            data = request.json
            message = data.get('message')
            filter_criteria = data.get('filter', {})
            
            # Build query based on filter criteria
            query = Customer.query
            
            if filter_criteria.get('last_order_days'):
                days = filter_criteria['last_order_days']
                date_threshold = datetime.now() - timedelta(days=days)
                query = query.join(Sales).filter(Sales.order_date >= date_threshold)
                
            if filter_criteria.get('min_orders'):
                query = query.having(func.count(Sales.order_no) >= filter_criteria['min_orders'])
                
            customers = query.all()
            
            results = []
            for customer in customers:
                if customer.phone:
                    result = whatsapp_service.send_message(customer.phone, message)
                    results.append({
                        'customer': customer.name,
                        'phone': customer.phone,
                        'status': 'success' if result else 'failed'
                    })
                    
            return jsonify({'results': results}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/webhook', methods=['GET'])
    def verify_webhook():
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        if mode and token:
            if mode == 'subscribe' and token == whatsapp_service.verify_token:
                return challenge, 200
            return 'Invalid verification token', 403
        return 'Invalid request', 400

    @app.route('/webhook', methods=['POST'])
    def webhook():
        try:
            data = request.json
            
            # Handle incoming messages
            if 'entry' in data and data['entry']:
                for entry in data['entry']:
                    for change in entry.get('changes', []):
                        if change.get('value', {}).get('messages'):
                            handle_incoming_message(change['value']['messages'][0])
                            
            return jsonify({'status': 'ok'}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500 

    @app.route('/api/accounting/insights', methods=['GET'])
    def get_accounting_insights():
        try:
            days = request.args.get('days', default=7, type=int)
            analysis_type = request.args.get('type', default='daily', type=str)
            date = request.args.get('date', type=str)  # Format: YYYY-MM-DD
            
            ai_agent = AccountingAIAgent()
            
            if analysis_type == 'daily':
                insights = ai_agent.get_daily_summary(days)
            elif analysis_type == 'monthly':
                months = days // 30
                insights = ai_agent.get_monthly_analysis(months)
            elif analysis_type == 'anomalies':
                insights = ai_agent.detect_anomalies(days)
            elif analysis_type == 'balance_sheet':
                insights = ai_agent.get_daily_balance_sheet(date)
            else:
                return jsonify({'error': 'Invalid analysis type'}), 400
            
            return jsonify({
                'success': True,
                'insights': insights
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500 

    @app.route('/api/transactions/<int:id>', methods=['DELETE'])
    @admin_required
    def delete_transaction(id):
        try:
            transaction = Accounts.query.get_or_404(id)
            
            # Only allow deletion of manual transactions
            if transaction.source != 'manual':
                return jsonify({'error': 'Can only delete manual transactions'}), 403
            
            db.session.delete(transaction)
            db.session.commit()
            
            return jsonify({'success': True})
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500 

    @app.route('/api/transactions/cleanup', methods=['DELETE'])
    @admin_required
    def cleanup_transactions():
        try:
            # Find all transactions with invalid order numbers
            invalid_transactions = Accounts.query.filter(
                ~Accounts.order_no.like('T%')  # ~ is the NOT operator in SQLAlchemy
            ).all()
            
            # Count transactions to be deleted
            count = len(invalid_transactions)
            
            # Delete the transactions
            for transaction in invalid_transactions:
                db.session.delete(transaction)
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Removed {count} invalid transactions',
                'count': count
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500 

    @app.route('/api/transactions/export/manual')
    @admin_required
    def export_manual_transactions():
        try:
            app.logger.info("Starting manual transactions export")
            
            # Get all manual transactions
            transactions = Accounts.query.filter_by(source='manual').order_by(Accounts.transaction_date.desc()).all()
            app.logger.info(f"Found {len(transactions)} manual transactions")
            
            # Create string buffer first
            string_buffer = StringIO()
            writer = csv.writer(string_buffer)
            
            # Write headers
            writer.writerow([
                'Date', 
                'Order No', 
                'Transaction Type',
                'Amount',
                'Payment Mode',
                'Reference No',
                'Description',
                'Notes'
            ])
            
            # Write transaction data
            for txn in transactions:
                writer.writerow([
                    txn.transaction_date.strftime('%Y-%m-%d') if txn.transaction_date else '',
                    txn.order_no or '',
                    txn.transaction_type or '',
                    str(txn.amount) if txn.amount else '0',
                    txn.payment_mode or '',
                    txn.reference_no or '',
                    txn.description or '',
                    txn.notes or ''
                ])
            
            # Convert to bytes for sending
            output = BytesIO()
            output.write(string_buffer.getvalue().encode('utf-8'))
            output.seek(0)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'manual_transactions_{timestamp}.csv'
            
            app.logger.info(f"Preparing to send file: {filename}")
            
            return send_file(
                output,
                mimetype='text/csv',
                as_attachment=True,
                download_name=filename
            )
            
        except Exception as e:
            app.logger.error(f"Export failed: {str(e)}")
            app.logger.exception("Full traceback:")
            return jsonify({
                'error': str(e),
                'details': 'Check server logs for more information'
            }), 500 

    @app.route('/employees')
    @login_required
    def employees_page():
        return render_template('employees.html')

    @app.route('/api/employees', methods=['GET'])
    @login_required
    def get_employees():
        employees = Employee.query.all()
        return jsonify([{
            'id': emp.id,
            'employee_code': emp.employee_code,
            'name': emp.name,
            'phone': emp.phone,
            'email': emp.email,
            'pan_number': emp.pan_number,
            'aadhar_number': emp.aadhar_number,
            'designation': emp.designation,
            'department': emp.department,
            'join_date': emp.join_date,
            'status': emp.status,
            'created_at': emp.created_at,
            'updated_at': emp.updated_at
        } for emp in employees])

    @app.route('/api/employees', methods=['POST'])
    @login_required
    def add_employee():
        try:
            data = request.json
            employee = Employee(
                employee_code=data['employee_code'],
                name=data['name'],
                phone=data.get('phone'),
                email=data.get('email'),
                pan_number=data.get('pan_number'),
                aadhar_number=data.get('aadhar_number'),
                designation=data.get('designation'),
                department=data.get('department'),
                join_date=datetime.strptime(data['join_date'], '%Y-%m-%d') if data.get('join_date') else None,
                status=data.get('status', 'Active')
            )
            db.session.add(employee)
            db.session.commit()
            return jsonify({'success': True, 'id': employee.id})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400 

    @app.route('/api/accounting/stats')
    def get_accounting_stats():
        try:
            # Get today's date range
            today = datetime.now().date()
            today_start = datetime.combine(today, datetime.min.time())
            today_end = datetime.combine(today, datetime.max.time())

            # Get month's date range
            month_start = today.replace(day=1)
            month_end = today_end

            # Get today's transactions
            today_transactions = Accounts.query.filter(
                Accounts.transaction_date.between(today_start, today_end)
            ).all()

            # Get month's transactions
            month_transactions = Accounts.query.filter(
                Accounts.transaction_date.between(month_start, month_end)
            ).all()

            # Calculate today's stats
            today_income = sum(t.amount for t in today_transactions if t.transaction_type == 'Income')
            today_expenses = sum(t.amount for t in today_transactions if t.transaction_type == 'Expense')

            # Calculate month's stats
            month_income = sum(t.amount for t in month_transactions if t.transaction_type == 'Income')
            month_expenses = sum(t.amount for t in month_transactions if t.transaction_type == 'Expense')

            return jsonify({
                'today': {
                    'income': float(today_income),
                    'expenses': float(today_expenses),
                    'transactions': len(today_transactions)
                },
                'month': {
                    'income': float(month_income),
                    'expenses': float(month_expenses),
                    'transactions': len(month_transactions)
                }
            })

        except Exception as e:
            app.logger.error(f"Error getting accounting stats: {str(e)}")
            app.logger.exception("Full traceback:")
            return jsonify({
                'error': str(e),
                'details': 'Check server logs for more information'
            }), 500 

    @app.route('/api/daily-balance', methods=['GET'])
    def get_daily_balance():
        try:
            date = request.args.get('date')
            if date:
                date = datetime.strptime(date, '%Y-%m-%d').date()
            else:
                date = datetime.now().date()
            
            balance = DailyBalance.query.filter_by(date=date).first()
            
            if balance:
                return jsonify({
                    'date': balance.date.isoformat(),
                    'bank_balance': float(balance.bank_balance),
                    'cash_in_hand': float(balance.cash_in_hand),
                    'notes': balance.notes,
                    'verified_by': balance.verified_by
                })
            else:
                return jsonify({
                    'date': date.isoformat(),
                    'bank_balance': 0.0,
                    'cash_in_hand': 0.0,
                    'notes': '',
                    'verified_by': ''
                })
            
        except Exception as e:
            app.logger.error(f"Error getting daily balance: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/daily-balance', methods=['POST'])
    @admin_required
    def add_daily_balance():
        try:
            data = request.json
            date = datetime.strptime(data['date'], '%Y-%m-%d').date()
            
            # Check if entry exists for this date
            balance = DailyBalance.query.filter_by(date=date).first()
            
            if balance:
                # Update existing
                balance.bank_balance = data['bank_balance']
                balance.cash_in_hand = data['cash_in_hand']
                balance.notes = data.get('notes', '')
                balance.verified_by = data.get('verified_by', '')
            else:
                # Create new
                balance = DailyBalance(
                    date=date,
                    bank_balance=data['bank_balance'],
                    cash_in_hand=data['cash_in_hand'],
                    notes=data.get('notes', ''),
                    verified_by=data.get('verified_by', '')
                )
                db.session.add(balance)
            
            db.session.commit()
            return jsonify({'success': True})
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error adding daily balance: {str(e)}")
            return jsonify({'error': str(e)}), 500 

    @app.route('/api/transactions/bulk-delete', methods=['POST'])
    @login_required
    def bulk_delete_transactions():
        try:
            data = request.get_json()
            if not data or 'ids' not in data:
                return jsonify({'error': 'No transaction IDs provided'}), 400
            
            # Delete transactions
            Accounts.query.filter(Accounts.id.in_(data['ids'])).delete(synchronize_session=False)
            db.session.commit()
            
            return jsonify({'success': True, 'message': f"Deleted {len(data['ids'])} transactions"})
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error deleting transactions: {str(e)}")
            return jsonify({'error': str(e)}), 500 