from datetime import datetime, timedelta
from models import Accounts
from sqlalchemy import func
import pandas as pd

class AccountingAIAgent:
    def __init__(self):
        self.system_prompt = """You are an expert accounting analyst AI. Analyze financial data and provide insights about:
- Revenue trends
- Payment patterns
- Business performance
- Anomaly detection
- Recommendations for improvement

Keep responses concise and focused on actionable insights."""

    def _sanitize_data(self, accounts_data):
        """Remove sensitive information from accounts data"""
        sensitive_fields = ['customer_id', 'customer_name', 'customer_phone', 
                          'customer_address', 'created_by', 'notes']
        
        sanitized_data = []
        for record in accounts_data:
            safe_record = {
                'transaction_date': record.transaction_date,
                'transaction_type': record.transaction_type,
                'category': record.category,
                'amount': record.amount,
                'total_amount': record.total_amount,
                'payment_mode': record.payment_mode,
                'payment_status': record.payment_status,
                'source': record.source
            }
            sanitized_data.append(safe_record)
        
        return sanitized_data

    def get_daily_summary(self, days=7):
        """Get daily transaction summary for the last n days"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        transactions = Accounts.query.filter(
            Accounts.transaction_date.between(start_date, end_date)
        ).all()
        
        safe_data = self._sanitize_data(transactions)
        df = pd.DataFrame(safe_data)
        
        if df.empty:
            return "No transactions found for the specified period."
        
        summary = {
            'total_income': df[df['transaction_type'] == 'Income']['amount'].sum(),
            'total_expense': df[df['transaction_type'] == 'Expense']['amount'].sum(),
            'payment_modes': df['payment_mode'].value_counts().to_dict(),
            'daily_totals': df.groupby([df['transaction_date'].dt.date])['amount'].sum().to_dict(),
            'categories': df.groupby('category')['amount'].sum().to_dict()
        }
        
        return self._generate_insights(summary)

    def get_monthly_analysis(self, months=1):
        """Get monthly transaction analysis"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date.replace(day=1)  # Start from beginning of current month
            
            transactions = Accounts.query.filter(
                Accounts.transaction_date.between(start_date, end_date)
            ).all()
            
            safe_data = self._sanitize_data(transactions)
            df = pd.DataFrame(safe_data)
            
            if df.empty:
                return "No transactions found for this month."
            
            # Calculate monthly metrics
            analysis = {
                'period': f"{start_date.strftime('%B %Y')}",
                'total_income': df[df['transaction_type'] == 'Income']['amount'].sum(),
                'total_expense': df[df['transaction_type'] == 'Expense']['amount'].sum(),
                'payment_modes': df.groupby('payment_mode')['amount'].sum().to_dict(),
                'categories': df.groupby(['transaction_type', 'category'])['amount'].sum().to_dict(),
                'daily_totals': df.groupby([df['transaction_date'].dt.date, 'transaction_type'])['amount'].sum().to_dict()
            }
            
            # Generate insights
            insights = []
            insights.append(f"Monthly Analysis - {analysis['period']}")
            insights.append("=" * 50)
            
            # Income and Expense Summary
            net_income = analysis['total_income'] - analysis['total_expense']
            insights.append(f"\nSUMMARY")
            insights.append("-" * 20)
            insights.append(f"Total Income: ₹{analysis['total_income']:,.2f}")
            insights.append(f"Total Expenses: ₹{analysis['total_expense']:,.2f}")
            insights.append(f"Net Position: ₹{net_income:,.2f}")
            
            # Payment Mode Analysis
            insights.append(f"\nPAYMENT MODES")
            insights.append("-" * 20)
            for mode, amount in analysis['payment_modes'].items():
                if pd.notna(mode):  # Skip if payment mode is NaN
                    insights.append(f"{mode}: ₹{amount:,.2f}")
            
            # Category Analysis
            insights.append(f"\nCATEGORY BREAKDOWN")
            insights.append("-" * 20)
            
            # Income Categories
            insights.append("\nIncome Categories:")
            for (type_, category), amount in analysis['categories'].items():
                if type_ == 'Income' and pd.notna(category):
                    insights.append(f"{category}: ₹{amount:,.2f}")
            
            # Expense Categories
            insights.append("\nExpense Categories:")
            for (type_, category), amount in analysis['categories'].items():
                if type_ == 'Expense' and pd.notna(category):
                    insights.append(f"{category}: ₹{amount:,.2f}")
            
            # Daily Trend
            insights.append(f"\nDAILY TREND")
            insights.append("-" * 20)
            current_date = None
            for (date, type_), amount in sorted(analysis['daily_totals'].items()):
                if current_date != date:
                    insights.append(f"\n{date.strftime('%d %b %Y')}:")
                    current_date = date
                insights.append(f"{type_}: ₹{amount:,.2f}")
            
            return "\n".join(insights)
            
        except Exception as e:
            print(f"Error in monthly analysis: {str(e)}")
            return f"Error generating monthly analysis: {str(e)}"

    def detect_anomalies(self, days=30):
        """Detect unusual transaction patterns"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        transactions = Accounts.query.filter(
            Accounts.transaction_date.between(start_date, end_date)
        ).all()
        
        safe_data = self._sanitize_data(transactions)
        df = pd.DataFrame(safe_data)
        
        if df.empty:
            return "No transactions found for the specified period."
        
        # Calculate basic statistics
        stats = {
            'daily_mean': df.groupby(df['transaction_date'].dt.date)['amount'].mean().mean(),
            'daily_std': df.groupby(df['transaction_date'].dt.date)['amount'].mean().std(),
            'unusual_days': []
        }
        
        # Detect days with unusual transaction volumes
        daily_totals = df.groupby(df['transaction_date'].dt.date)['amount'].sum()
        threshold = stats['daily_mean'] + (2 * stats['daily_std'])
        
        stats['unusual_days'] = daily_totals[daily_totals > threshold].to_dict()
        
        return self._generate_insights(stats)

    def get_daily_balance_sheet(self, date=None):
        """Generate a daily balance sheet for a specific date"""
        if date is None:
            date = datetime.utcnow().date()
        else:
            # If date is string, convert to datetime
            if isinstance(date, str):
                date = datetime.strptime(date, '%Y-%m-%d').date()
        
        # Get all transactions for the day
        start_datetime = datetime.combine(date, datetime.min.time())
        end_datetime = datetime.combine(date, datetime.max.time())
        
        transactions = Accounts.query.filter(
            Accounts.transaction_date.between(start_datetime, end_datetime)
        ).all()
        
        safe_data = self._sanitize_data(transactions)
        df = pd.DataFrame(safe_data)
        
        if df.empty:
            return "No transactions found for the specified date."
        
        # Calculate balance sheet components
        balance_sheet = {
            'date': date.strftime('%d %b %Y'),
            'income': {
                'total': 0,
                'by_category': {},
                'by_payment_mode': {}
            },
            'expenses': {
                'total': 0,
                'by_category': {},
                'by_payment_mode': {}
            },
            'summary': {
                'total_transactions': len(df),
                'net_position': 0
            }
        }
        
        # Process income
        income_df = df[df['transaction_type'] == 'Income']
        if not income_df.empty:
            balance_sheet['income'].update({
                'total': income_df['amount'].sum(),
                'by_category': income_df.groupby('category')['amount'].sum().to_dict(),
                'by_payment_mode': income_df.groupby('payment_mode')['amount'].sum().to_dict()
            })
        
        # Process expenses
        expense_df = df[df['transaction_type'] == 'Expense']
        if not expense_df.empty:
            balance_sheet['expenses'].update({
                'total': expense_df['amount'].sum(),
                'by_category': expense_df.groupby('category')['amount'].sum().to_dict(),
                'by_payment_mode': expense_df.groupby('payment_mode')['amount'].sum().to_dict()
            })
        
        # Calculate summary
        balance_sheet['summary']['net_position'] = balance_sheet['income']['total'] - balance_sheet['expenses']['total']
        
        return self._format_balance_sheet(balance_sheet)

    def _format_balance_sheet(self, data):
        """Format balance sheet data into a readable string"""
        lines = []
        
        # Header
        lines.append(f"Daily Balance Sheet - {data['date']}")
        lines.append("=" * 50)
        
        # Income Section
        lines.append("\nINCOME")
        lines.append("-" * 20)
        for category, amount in data['income']['by_category'].items():
            lines.append(f"{category}: ₹{amount:,.2f}")
        lines.append(f"Total Income: ₹{data['income']['total']:,.2f}")
        
        # Income by Payment Mode
        lines.append("\nIncome by Payment Mode:")
        for mode, amount in data['income']['by_payment_mode'].items():
            lines.append(f"{mode}: ₹{amount:,.2f}")
        
        # Expenses Section
        lines.append("\nEXPENSES")
        lines.append("-" * 20)
        for category, amount in data['expenses']['by_category'].items():
            lines.append(f"{category}: ₹{amount:,.2f}")
        lines.append(f"Total Expenses: ₹{data['expenses']['total']:,.2f}")
        
        # Expenses by Payment Mode
        lines.append("\nExpenses by Payment Mode:")
        for mode, amount in data['expenses']['by_payment_mode'].items():
            lines.append(f"{mode}: ₹{amount:,.2f}")
        
        # Summary Section
        lines.append("\nSUMMARY")
        lines.append("-" * 20)
        lines.append(f"Total Transactions: {data['summary']['total_transactions']}")
        lines.append(f"Net Position: ₹{data['summary']['net_position']:,.2f}")
        
        return "\n".join(lines)

    def _generate_insights(self, data):
        """Generate insights from the analyzed data"""
        insights = []
        
        if 'total_income' in data and 'total_expense' in data:
            net_income = data['total_income'] - data['total_expense']
            insights.append(f"Net income for the period: ₹{net_income:,.2f}")
            
            if net_income > 0:
                profit_margin = (net_income / data['total_income']) * 100
                insights.append(f"Profit margin: {profit_margin:.1f}%")
        
        if 'payment_modes' in data:
            top_mode = max(data['payment_modes'].items(), key=lambda x: x[1])
            insights.append(f"Most popular payment mode: {top_mode[0]} ({top_mode[1]} transactions)")
        
        if 'daily_totals' in data:
            avg_daily = sum(data['daily_totals'].values()) / len(data['daily_totals'])
            insights.append(f"Average daily transaction volume: ₹{avg_daily:,.2f}")
        
        if 'unusual_days' in data and data['unusual_days']:
            insights.append("Detected unusual transaction volumes on:")
            for date, amount in data['unusual_days'].items():
                insights.append(f"- {date}: ₹{amount:,.2f}")
        
        return "\n".join(insights) 