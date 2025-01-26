from app import app
from extensions import db
from sqlalchemy import text

def add_payment_date_column():
    with app.app_context():
        try:
            # Add payment_date column
            db.engine.execute(text("""
                ALTER TABLE accounts 
                ADD COLUMN payment_date DATETIME;
            """))
            print("Added payment_date column to accounts table")
        except Exception as e:
            print(f"Error adding payment_date column: {str(e)}")
            db.session.rollback()

if __name__ == "__main__":
    add_payment_date_column() 