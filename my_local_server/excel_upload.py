from flask import request, jsonify
import pandas as pd
from models import Customer, Sales, Accounts
from extensions import db
from datetime import datetime
from constants import (
    CSV_COLUMNS, 
    REQUIRED_COLUMNS, 
    DATE_FORMATS, 
    PAYMENT_MODE_MAPPING, 
    PAYMENT_LOCATION_MAPPING,
    COLUMN_STANDARDIZATION
)

def init_upload_routes(app):
    def map_column_name(df, upload_type='ORDERS'):
        """Map various possible column names to standardized names"""
        mapped_columns = {}
        column_mappings = CSV_COLUMNS[upload_type]
        
        # Create reverse mapping from variations to standard name
        reverse_mapping = {}
        for standard, variations in column_mappings.items():
            for variant in variations:
                reverse_mapping[variant] = standard  # Don't lowercase the variant
            
        # Map columns in dataframe
        for col in df.columns:
            # Try exact match first
            standard_name = reverse_mapping.get(col)
            if standard_name:
                mapped_columns[col] = standard_name
                continue
            
            # Try case-insensitive match
            col_lower = col.lower()
            for variant, standard in reverse_mapping.items():
                if variant.lower() == col_lower:
                    mapped_columns[col] = standard
                    break
        
        return df.rename(columns=mapped_columns)

    def verify_required_columns(df, upload_type='ORDERS'):
        """Verify that all required columns are present"""
        missing_columns = [col for col in REQUIRED_COLUMNS[upload_type] 
                          if col not in df.columns]
        
        if missing_columns:
            raise ValueError(
                f'Missing required columns: {", ".join(missing_columns)}\n'
                f'Available columns: {", ".join(df.columns)}'
            )

    def parse_date(date_str, date_type='ORDER_DATE'):
        """Parse dates using format list from constants"""
        if pd.isna(date_str):
            return None
        
        date_str = str(date_str).strip()
        
        # Skip non-date strings
        if any(skip in date_str.lower() for skip in ['walk in', 'customer', 'na', 'none', '-']):
            return None
        
        try:
            # Try pandas to_datetime first
            return pd.to_datetime(date_str)
        except:
            # Try specific formats for this date type
            for fmt in DATE_FORMATS[date_type]:
                try:
                    return datetime.strptime(date_str, fmt)
                except:
                    continue
            
            print(f"Could not parse {date_type}: {date_str}")
            return None

    def parse_payment_date(date_str):
        """Parse dates specifically for payment uploads"""
        if pd.isna(date_str):
            return None
        
        date_str = str(date_str).strip()
        
        # Skip non-date strings
        if any(skip in date_str.lower() for skip in ['walk in', 'customer', 'na', 'none', '-']):
            return None
        
        try:
            # Try specific payment date formats
            date_formats = [
                '%d/%m/%Y %I:%M %p',    # 31/12/2023 02:53 PM
                '%d/%m/%Y %H:%M',       # 31/12/2023 14:53
                '%d/%m/%Y',             # 31/12/2023
            ]
            
            for fmt in date_formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except:
                    continue
            
            # If specific formats fail, try pandas default parsing
            return pd.to_datetime(date_str)
                
        except:
            print(f"Could not parse payment date: {date_str}")
            return None

    def parse_transaction_date(date_str):
        """Parse dates specifically for transaction uploads"""
        if pd.isna(date_str):
            return None
        
        date_str = str(date_str).strip()
        
        # Skip non-date strings
        if any(skip in date_str.lower() for skip in ['walk in', 'customer', 'na', 'none', '-']):
            return None
        
        try:
            # Try specific transaction date formats
            date_formats = [
                '%d %b %Y %I:%M:%S %p',  # 30 Dec 2023 10:40:29 AM
                '%d %b %Y'               # 26 Dec 2023
            ]
            
            for fmt in date_formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except:
                    continue
            
            print(f"Could not parse transaction date: {date_str}")
            return None
        except:
            print(f"Error parsing transaction date: {date_str}")
            return None

    def is_return_order(order_no):
        """Check if order number indicates a return order"""
        return str(order_no).upper().startswith('SRN')

    def standardize_columns(df):
        """Standardize DataFrame column names to snake_case format"""
        # Convert all column names to the new format
        new_columns = {}
        for col in df.columns:
            if col in COLUMN_STANDARDIZATION:
                new_columns[col] = COLUMN_STANDARDIZATION[col]
            else:
                # Keep columns that don't need to be changed
                new_columns[col] = col
                
        return df.rename(columns=new_columns)

    @app.route('/upload-excel', methods=['POST'])
    def upload_excel():
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if not file.filename.endswith('.csv'):
            return jsonify({'error': 'Please upload a CSV file'}), 400
        
        try:
            df = pd.read_csv(file)
            # Map column names to standardized format
            df = map_column_name(df)
            
            print("Available columns:", df.columns.tolist())
            
            # Verify required columns for orders CSV
            required_columns = REQUIRED_COLUMNS['ORDERS']
            
            missing_columns = [col for col in required_columns 
                              if col not in df.columns]
            
            if missing_columns:
                return jsonify({
                    'error': f'Missing required columns: {", ".join(missing_columns)}\nAvailable columns: {", ".join(df.columns)}'
                }), 400

            print("Mapped CSV Columns:", df.columns.tolist())
            
            with db.session.no_autoflush:
                # First pass: Process customers
                for _, row in df.iterrows():
                    if pd.isna(row.get('customer_code')):
                        continue
                        
                    try:
                        # First try to get the existing customer
                        customer = db.session.query(Customer).filter_by(
                            customer_code=str(row['customer_code'])
                        ).first()
                        
                        # Prepare customer data with error handling
                        customer_data = {}
                        fields = [
                            ('name', 'customer_name'),
                            ('address', 'customer_address'),
                            ('phone', 'customer_phone'),
                            ('preference', 'customer_preference'),
                            ('gstin', 'customer_gstin'),
                            ('area_location', 'area_location'),
                            ('registration_source', 'registration_source')
                        ]
                        
                        for field, column in fields:
                            try:
                                value = row.get(column)
                                customer_data[field] = str(value) if pd.notna(value) else ''
                            except Exception as e:
                                print(f"Error processing {column}: {str(e)}")
                                customer_data[field] = ''

                        if customer:
                            # Update existing customer
                            print(f"Updating customer: {customer.customer_code}")
                            for key, value in customer_data.items():
                                setattr(customer, key, value)
                        else:
                            # Create new customer
                            print(f"Creating new customer: {row['customer_code']}")
                            customer = Customer(
                                customer_code=str(row['customer_code']),
                                **customer_data
                            )
                            db.session.add(customer)
                        
                        db.session.commit()
                        
                    except Exception as e:
                        print(f"Error processing customer row: {row}")
                        print(f"Error details: {str(e)}")
                        db.session.rollback()
                        continue

                # Second pass: Process sales
                for _, row in df.iterrows():
                    try:
                        customer = Customer.query.filter_by(customer_code=row['customer_code']).first()
                        
                        if customer:
                            # Convert 'Yes'/'No' strings to boolean
                            def convert_to_bool(value):
                                if pd.isna(value):
                                    return False
                                if isinstance(value, bool):
                                    return value
                                if isinstance(value, str):
                                    return True if value.lower() in ['yes', 'true', '1', 'y'] else False
                                return False

                            # Process numeric fields with better error handling
                            numeric_fields = {
                                'pieces': 'pieces',
                                'weight': 'weight',
                                'gross_amount': 'gross_amount',
                                'discount': 'discount',
                                'tax': 'tax',
                                'net_amount': 'net_amount',
                                'advance': 'advance',
                                'paid': 'paid_amount',
                                'adjustment': 'adjustment',
                                'balance': 'balance',
                                'advance_received': 'advance_received',
                                'advance_used': 'advance_used'
                            }
                            
                            processed_data = {}
                            for field, csv_column in numeric_fields.items():
                                try:
                                    value = row[csv_column]
                                    if pd.isna(value) or value == '':
                                        processed_data[field] = 0.0
                                    else:
                                        if isinstance(value, str):
                                            value = value.replace('₹', '').replace(',', '').strip()
                                        processed_data[field] = float(value)
                                except (ValueError, TypeError):
                                    processed_data[field] = 0.0

                            # Check if sale already exists
                            existing_sale = Sales.query.get(str(row['order_no']))
                            if existing_sale:
                                print(f"Updating existing sale: {row['order_no']}")
                                # Update existing sale
                                for key, value in processed_data.items():
                                    setattr(existing_sale, key, value)
                                existing_sale.customer_id = customer.id
                                existing_sale.order_date = pd.to_datetime(row['order_date_time'], dayfirst=True)
                                existing_sale.due_date = pd.to_datetime(row['due_date'], dayfirst=True) if pd.notna(row['due_date']) else None
                                existing_sale.last_activity = pd.to_datetime(row['last_activity'], dayfirst=True) if pd.notna(row['last_activity']) else None
                                existing_sale.booked_by = str(row['booked_by']) if pd.notna(row['booked_by']) else None
                                existing_sale.workshop_note = str(row['workshop_note']) if pd.notna(row['workshop_note']) else None
                                existing_sale.order_note = str(row['order_note']) if pd.notna(row['order_note']) else None
                                existing_sale.home_delivery = convert_to_bool(row['home_delivery'])
                                existing_sale.garments_inspected_by = str(row['garments_inspected_by']) if pd.notna(row['garments_inspected_by']) else None
                                existing_sale.order_from_pos = convert_to_bool(row['order_from_pos'])
                                existing_sale.package = convert_to_bool(row['package'])
                                existing_sale.package_type = str(row['package_type']) if pd.notna(row['package_type']) else None
                                existing_sale.package_name = str(row['package_name']) if pd.notna(row['package_name']) else None
                                existing_sale.feedback = str(row['feedback']) if pd.notna(row['feedback']) else None
                                existing_sale.tags = str(row['tags']) if pd.notna(row['tags']) else None
                                existing_sale.comment = str(row['comment']) if pd.notna(row['comment']) else None
                                existing_sale.primary_services = str(row['primary_services']) if pd.notna(row['primary_services']) else None
                                existing_sale.topup_service = str(row['topup_service']) if pd.notna(row['topup_service']) else None
                                existing_sale.order_status = str(row['order_status']) if pd.notna(row['order_status']) else None
                                existing_sale.last_payment_activity = pd.to_datetime(row['last_payment_activity'], dayfirst=True) if pd.notna(row['last_payment_activity']) else None
                                existing_sale.coupon_code = str(row['coupon_code']) if pd.notna(row['coupon_code']) else None
                            else:
                                # Create new sale
                                print(f"Creating new sale: {row['order_no']}")
                                sale = Sales(
                                    order_no=str(row['order_no']),
                                    customer_id=customer.id,
                                    order_date=pd.to_datetime(row['order_date_time'], dayfirst=True),
                                    due_date=pd.to_datetime(row['due_date'], dayfirst=True) if pd.notna(row['due_date']) else None,
                                    last_activity=pd.to_datetime(row['last_activity'], dayfirst=True) if pd.notna(row['last_activity']) else None,
                                    **processed_data,
                                    booked_by=str(row['booked_by']) if pd.notna(row['booked_by']) else None,
                                    workshop_note=str(row['workshop_note']) if pd.notna(row['workshop_note']) else None,
                                    order_note=str(row['order_note']) if pd.notna(row['order_note']) else None,
                                    home_delivery=convert_to_bool(row['home_delivery']),
                                    garments_inspected_by=str(row['garments_inspected_by']) if pd.notna(row['garments_inspected_by']) else None,
                                    order_from_pos=convert_to_bool(row['order_from_pos']),
                                    package=convert_to_bool(row['package']),
                                    package_type=str(row['package_type']) if pd.notna(row['package_type']) else None,
                                    package_name=str(row['package_name']) if pd.notna(row['package_name']) else None,
                                    feedback=str(row['feedback']) if pd.notna(row['feedback']) else None,
                                    tags=str(row['tags']) if pd.notna(row['tags']) else None,
                                    comment=str(row['comment']) if pd.notna(row['comment']) else None,
                                    primary_services=str(row['primary_services']) if pd.notna(row['primary_services']) else None,
                                    topup_service=str(row['topup_service']) if pd.notna(row['topup_service']) else None,
                                    order_status=str(row['order_status']) if pd.notna(row['order_status']) else None,
                                    last_payment_activity=pd.to_datetime(row['last_payment_activity'], dayfirst=True) if pd.notna(row['last_payment_activity']) else None,
                                    coupon_code=str(row['coupon_code']) if pd.notna(row['coupon_code']) else None
                                )
                                db.session.add(sale)
                        
                    except Exception as e:
                        print(f"Error processing row: {row}")
                        print(f"Error details: {str(e)}")
                        db.session.rollback()
                        continue

                db.session.commit()
                return jsonify({'message': 'Customer and sales data imported successfully'}), 200
                
        except Exception as e:
            print(f"Main error: {str(e)}")
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
        
    @app.route('/upload/transactions', methods=['POST'])
    def upload_transactions():
        try:
            if 'file' not in request.files:
                return jsonify({'error': 'No file uploaded'}), 400

            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400

            if not file.filename.endswith('.csv'):
                return jsonify({'error': 'File must be a CSV'}), 400

            # Read CSV file
            df = pd.read_csv(file)

            for _, row in df.iterrows():
                try:
                    # Create transaction record
                    transaction = Accounts(
                        transaction_date=parse_transaction_date(row['payment_date']),
                        transaction_type='Income',
                        category='Sales',
                        amount=float(row['payment_received']) if pd.notna(row['payment_received']) else 0.0,
                        total_amount=float(row['payment_received']) if pd.notna(row['payment_received']) else 0.0,
                        payment_mode=map_payment_mode(row['payment_mode']) if pd.notna(row['payment_mode']) else None,
                        payment_status='Completed',
                        reference_no=str(row['transaction_id']) if pd.notna(row['transaction_id']) else None,
                        order_no=str(row['order_no']) if pd.notna(row['order_no']) else None,
                        description=f"Payment for order {row['order_no']}",
                        created_by=row['accepted_by'] if pd.notna(row['accepted_by']) else None
                    )
                    db.session.add(transaction)

                except Exception as e:
                    print(f"Error processing transaction row: {row}")
                    print(f"Error details: {str(e)}")
                    db.session.rollback()
                    continue

            db.session.commit()
            return jsonify({'message': 'Transaction data imported successfully'}), 200

        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    @app.route('/upload/payments', methods=['POST'])
    def upload_payments():
        try:
            if 'file' not in request.files:
                return jsonify({'error': 'No file uploaded'}), 400

            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400

            if not file.filename.endswith('.csv'):
                return jsonify({'error': 'File must be a CSV'}), 400

            # Try different encodings
            encodings = ['utf-8', 'Windows-1252', 'iso-8859-1']
            df = None
            
            for encoding in encodings:
                try:
                    file.seek(0)
                    df = pd.read_csv(file, encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if df is None:
                return jsonify({'error': 'Unable to read CSV file. Please check the file encoding.'}), 400

            # Standardize column names first, before any other processing
            df = standardize_columns(df)

            # Then do the column mapping
            df = map_column_name(df, 'PAYMENTS')
            
            # Continue with the rest of the processing...

            # Map column names
            df = map_column_name(df)
            print("Mapped CSV Columns:", df.columns.tolist())

            for _, row in df.iterrows():
                try:
                    # Check if it's a return order first
                    is_return = is_return_order(row['order_no'])
                    
                    # Get payment amounts
                    payment_amount = float(row['paid_amount']) if pd.notna(row['paid_amount']) else 0.0
                    adjustment = float(row['adjustment']) if pd.notna(row['adjustment']) else 0.0
                    
                    # For return orders (SRN), convert negative amount to positive for expense entry
                    if is_return:
                        payment_amount = abs(payment_amount)  # Convert negative to positive
                        adjustment = abs(adjustment)  # Convert negative to positive
                        order = None  # Don't look up return orders
                    else:
                        # Only look up order for regular transactions
                        order = Sales.query.filter_by(order_no=str(row['order_no'])).first()
                        if not order:
                            print(f"Order not found: {row['order_no']}")
                            continue

                        # Update order payment details
                        order.paid = (order.paid or 0) + payment_amount
                        order.adjustment = (order.adjustment or 0) + adjustment
                        order.balance = float(row['balance']) if pd.notna(row['balance']) else (order.net_amount - order.paid)
                        order.last_payment_activity = parse_payment_date(row['transaction_date'])
                        order.order_status = 'Delivered'

                    # Create transaction record
                    payment_mode = map_payment_mode(row['payment_mode']) if pd.notna(row['payment_mode']) else None
                    
                    # Set transaction type based on order number
                    transaction_type = 'Expense' if is_return else 'Income'
                    description = (
                        f"Refund for return order {row['order_no']}" 
                        if is_return 
                        else f"Payment for order {row['order_no']}"
                    )
                    
                    transaction = Accounts(
                        transaction_date=parse_payment_date(row['transaction_date']),
                        transaction_type=transaction_type,
                        category='SRN-Garment Return' if is_return else 'Sales',
                        amount=payment_amount,
                        total_amount=payment_amount + adjustment,
                        payment_mode=payment_mode,
                        payment_status='Completed',
                        reference_no=str(row['transaction_id']) if pd.notna(row['transaction_id']) else None,
                        order_no=str(row['order_no']),
                        customer_id=order.customer_id if order else None,
                        description=description,
                        created_by=row.get('accepted_by', ''),
                        created_at=datetime.utcnow(),
                        notes=map_payment_location(row['payment_location']),
                        source='csv'
                    )
                    db.session.add(transaction)

                except Exception as e:
                    print(f"Error processing payment row: {row}")
                    print(f"Error details: {str(e)}")
                    db.session.rollback()
                    continue

            db.session.commit()
            return jsonify({'message': 'Payment data imported successfully'}), 200

        except Exception as e:
            print(f"Main error: {str(e)}")
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

def map_payment_mode(mode):
    """Map payment mode using constant mapping"""
    if pd.isna(mode):
        return None
        
    mode = str(mode).strip().lower()
    
    # Try exact match first
    mapped_value = PAYMENT_MODE_MAPPING.get(mode)
    if mapped_value:
        return mapped_value
        
    # Try removing spaces and slashes
    cleaned_mode = mode.replace(' ', '').replace('/', '')
    for key, value in PAYMENT_MODE_MAPPING.items():
        if cleaned_mode == key.replace(' ', '').replace('/', ''):
            return value
            
    return mode.title()

def map_payment_location(location):
    """Map payment location using constant mapping"""
    if pd.isna(location):
        return None
        
    location = str(location).strip().upper()
    return PAYMENT_LOCATION_MAPPING.get(location, location)

def process_payments(df):
    """Process payments data from CSV"""
    payments = []
    for _, row in df.iterrows():
        try:
            # Find the order
            order = Sales.query.filter_by(order_no=row['order_no']).first()
            if not order:
                continue

            # Create payment record
            payment = Accounts(
                order_no=row['order_no'],
                transaction_date=pd.to_datetime(row['transaction_date']),
                payment_received=float(row['payment_received']),
                payment_mode=map_payment_mode(row['payment_mode']),
                transaction_id=row.get('transaction_id', ''),
                accepted_by=row.get('accepted_by', ''),
                created_at=datetime.utcnow(),
                notes=map_payment_location(row['payment_location']),
                source='csv'
            )
            payments.append(payment)

        except Exception as e:
            print(f"Error processing payment row: {row}")
            print(f"Error details: {str(e)}")
            db.session.rollback()
            continue

    return payments

def process_orders(df):
    """Process orders data from CSV"""
    orders = []
    for _, row in df.iterrows():
        try:
            # Find or create customer
            customer = Customer.query.filter_by(customer_code=row['customer_code']).first()
            
            # Create order record
            order = Sales(
                order_no=row['order_no'],
                order_date=pd.to_datetime(row['order_date_time']),
                customer_code=row['customer_code'],
                customer_name=row['customer_name'],
                customer_phone=row['customer_phone'],
                net_amount=float(row['net_amount']),
                paid_amount=float(row.get('paid_amount', 0)),
                balance=float(row.get('balance', 0)),
                created_at=datetime.utcnow(),
                source='csv'
            )
            orders.append(order)

        except Exception as e:
            print(f"Error processing order row: {row}")
            print(f"Error details: {str(e)}")
            continue

    return orders


