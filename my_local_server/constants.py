TRANSACTION_TYPES = ['Income', 'Expense', 'Transfer']

# Categories
INCOME_CATEGORIES = [
    'Sales',
    'Service',
    'Interest',
    'Commission',
    'Other Income'
]

EXPENSE_CATEGORIES = [
    'Rent',
    'Utilities',
    'Salaries',
    'Supplies',
    'Marketing',
    'Maintenance',
    'SRN-Garment Return',
    'Other Expense'
]

# Payment Modes
PAYMENT_MODES = [
    'Cash',
    'UPI',
    'Bank Transfer',
    'Credit Card',
    'Debit Card',
    'Check',
    'Digital Wallet',
    'PhonePe',
    'Google Pay',
    'Paytm',
    'NEFT',
    'RTGS',
    'IMPS',
    'Package'
]

# Payment Statuses
PAYMENT_STATUSES = [
    'Pending',
    'Completed',
    'Failed',
    'Refunded',
    'Cancelled'
]

# Order Statuses
ORDER_STATUSES = [
    'Unprocessed',
    'Pending',
    'Processing',
    'Ready',
    'Delivered',
    'Cancelled'
]

# CSV Column Mappings
CSV_COLUMNS = {
    'ORDERS': {
        'order_date_time': ['order date / time', 'order date time', 'orderdatetime'],
        'order_no': ['order no', 'orderno', 'order number', 'ordernumber'],
        'customer_code': ['customer code', 'customercode', 'code'],
        'customer_name': ['customer name', 'customername', 'name'],
        'customer_address': ['customer address', 'customeraddress', 'address'],
        'customer_phone': ['customer phone', 'customerphone', 'phone'],
        'customer_preference': ['customer preference', 'customerpreference', 'preference'],
        'due_date': ['due date', 'duedate'],
        'last_activity': ['last activity', 'lastactivity'],
        'pieces': ['pcs.', 'pieces', 'piececount'],
        'weight': ['weight'],
        'gross_amount': ['gross amount', 'grossamount'],
        'discount': ['discount'],
        'tax': ['tax', 'taxamount'],
        'net_amount': ['net amount', 'netamount', 'totalamount'],
        'advance': ['advance', 'advanceamount'],
        'paid_amount': ['paid', 'paid amount', 'paidamount', 'payment received'],
        'adjustment': ['adjustment', 'adjustments'],
        'balance': ['balance', 'balanceamount'],
        'advance_received': ['advance received', 'advancereceived'],
        'advance_used': ['advance used', 'advanceused'],
        'booked_by': ['booked by', 'bookedby'],
        'workshop_note': ['workshop note', 'workshopnote'],
        'order_note': ['order note', 'ordernote'],
        'home_delivery': ['home delivery', 'homedelivery'],
        'area_location': ['area location', 'arealocation', 'area/location'],
        'garments_inspected_by': ['garments inspected by', 'garmentsinspectedby'],
        'customer_gstin': ['customer gstin', 'customergstin', 'gstin'],
        'registration_source': ['registration source', 'registrationsource'],
        'order_from_pos': ['order from pos', 'orderpos'],
        'package': ['package'],
        'package_type': ['package type', 'packagetype'],
        'package_name': ['package name', 'packagename'],
        'feedback': ['feedback'],
        'tags': ['tags'],
        'comment': ['comment', 'comments'],
        'primary_services': ['primary services', 'primaryservices'],
        'topup_service': ['top up/extra service', 'topupservice', 'extraservice'],
        'order_status': ['order status', 'orderstatus'],
        'last_payment_activity': ['last payment activity', 'lastpaymentactivity'],
        'coupon_code': ['coupon code', 'couponcode']
    },
    'PAYMENTS': {
        'transaction_date': ['transaction_date'],
        'order_no': ['order_no'],
        'customer_code': ['customer_code'],
        'customer_name': ['customer_name'],
        'customer_address': ['customer_address'],
        'customer_phone': ['customer_phone'],
        'payment_received': ['payment_received', 'paid_amount'],
        'payment_mode': ['payment_mode'],
        'adjustment': ['adjustment'],
        'balance': ['balance'],
        'transaction_id': ['transaction_id'],
        'accepted_by': ['accepted_by'],
        'payment_location': ['payment_location']
    },
    'TRANSACTIONS': {
        'transaction_date': ['transaction date', 'date', 'transactiondate'],
        'order_no': ['order no', 'order number', 'orderno', 'ordernumber'],
        'amount': ['amount', 'transaction amount', 'transactionamount'],
        'payment_mode': ['payment mode', 'mode', 'paymentmode'],
        'reference_no': ['reference no', 'transaction id', 'referenceno'],
        'notes': ['notes', 'description'],
        'created_by': ['created by', 'user', 'createdby']
    }
}

# Required columns for each type
REQUIRED_COLUMNS = {
    'ORDERS': [
        'order_date_time',
        'order_no',
        'customer_code',
        'customer_name',
        'customer_phone',
        'net_amount'
    ],
    'PAYMENTS': [
        'transaction_date',
        'order_no',
        'payment_received'
    ],
    'TRANSACTIONS': [
        'transaction_date',
        'amount'
    ]
}

# Date formats for different types of dates
DATE_FORMATS = {
    'ORDER_DATE': [
        '%d %b %Y %I:%M:%S %p',  # 31 Dec 2023 02:53:53 PM
        '%d %b %Y %H:%M:%S %p',  # Added this format
        '%d %b %Y',              # 26 Dec 2023
        '%Y-%m-%d %H:%M:%S',     # 2023-12-31 14:53:53
        '%Y-%m-%d',              # 2023-12-31
        '%d/%m/%Y %H:%M:%S',     # 31/12/2023 14:53:53
        '%d/%m/%Y',              # 31/12/2023
        '%d-%m-%Y %H:%M:%S',     # 31-12-2023 14:53:53
        '%d-%m-%Y'               # 31-12-2023
    ],
    'PAYMENT_DATE': [
        '%d %b %Y %I:%M:%S %p',  # Added this format for "13 Jan 2025 07:28:03 PM"
        '%d %b %Y %H:%M:%S %p',  # Added this format
        '%d/%m/%Y %I:%M %p',     # 31/12/2023 02:53 PM
        '%d/%m/%Y %H:%M',        # 31/12/2023 14:53
        '%d/%m/%Y',              # 31/12/2023
        '%d %b %Y'               # 26 Dec 2023
    ],
    'TRANSACTION_DATE': [
        '%d %b %Y %I:%M:%S %p',  # 30 Dec 2023 10:40:29 AM
        '%d %b %Y'               # 26 Dec 2023
    ]
}

# Payment mode mappings
PAYMENT_MODE_MAPPING = {
    'phonep': 'PhonePe',
    'phonepe': 'PhonePe',
    'gpay': 'Google Pay',
    'google pay': 'Google Pay',
    'googlepay': 'Google Pay',
    'paytm': 'Paytm',
    'neft': 'NEFT',
    'rtgs': 'RTGS',
    'imps': 'IMPS',
    'cash': 'Cash',
    'upi': 'UPI',
    'bank': 'Bank Transfer',
    'bank transfer': 'Bank Transfer',
    'credit': 'Credit Card',
    'credit card': 'Credit Card',
    'debit': 'Debit Card',
    'debit card': 'Debit Card',
    'credit card/debit card': 'Credit Card',
    'credit/debit card': 'Credit Card',
    'credit/debit': 'Credit Card',
    'card': 'Credit Card',
    'cheque': 'Check',
    'check': 'Check',
    'wallet': 'Digital Wallet',
    'digital': 'Digital Wallet',
    'digital wallet': 'Digital Wallet',
    'package': 'Package',
    'pkg': 'Package',
    'pack': 'Package'
}

# Payment location mappings
PAYMENT_LOCATION_MAPPING = {
    'MOBILE APP': 'Mobile APP',
    'MOBILEAPP': 'Mobile APP',
    'APP': 'Mobile APP',
    'MOBILE POS': 'Mobile POS',
    'MOBILEPOS': 'Mobile POS',
    'POS': 'Mobile POS',
    'PAYMENT LINK': 'Payment Link',
    'PAYMENTLINK': 'Payment Link',
    'LINK': 'Payment Link',
    'WALK IN': 'Walk in Customer',
    'WALKIN': 'Walk in Customer',
    'WALK IN CUSTOMER': 'Walk in Customer',
    'WALK-IN': 'Walk in Customer'
}

# Add this new constant for standardizing column names
COLUMN_STANDARDIZATION = {
    'Order Date': 'order_date',
    'Payment Date': 'transaction_date',
    'Order No.': 'order_no',
    'Order Number': 'order_no',
    'Customer Code': 'customer_code',
    'Customer Name': 'customer_name',
    'Customer Address': 'customer_address',
    'Customer Mobile No.': 'customer_phone',
    'paid_amount': 'payment_received',
    'Payment Amount': 'payment_received',
    'Payment Received': 'payment_received',
    'Payment Mode': 'payment_mode',
    'Online TransactionID': 'transaction_id',
    'Accept By': 'accepted_by',
    'Payment Made At': 'payment_location',
    'Balance': 'balance',
    'Adjustment': 'adjustment',
    'Adjustments': 'adjustment',
    'Type': 'type'
}