import sqlite3
import json
from datetime import datetime

def test_query():
    try:
        # Connect to your database
        db_path = 'instance/database.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # First, let's check the table structure
        cursor.execute("PRAGMA table_info(Accounts);")
        columns = cursor.fetchall()
        print("\nTable structure:")
        for col in columns:
            print(f"Column: {col[1]}, Type: {col[2]}")

        # Test the query with correct column names
        test_query = """
        SELECT acc.transaction_date AS date, SUM(acc.amount) AS total_amount, SUM(acc.tax_amount) AS total_tax, COUNT(*) AS number_of_transactions FROM Accounts acc WHERE acc.transaction_date >= date(datetime('now'), '-1 month') GROUP BY acc.transaction_date;
        """

        # Execute query
        print("\nExecuting query...")
        cursor.execute(test_query)
        
        # Get results
        results = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        
        # Format results as list of dictionaries
        formatted_results = [dict(zip(columns, row)) for row in results]
        
        print("\nQuery Results:")
        print(json.dumps(formatted_results, indent=2))

        # Get sample of raw data for verification
        print("\nSample of raw data (last 5 records):")
        cursor.execute("""
            SELECT transaction_date, transaction_type, amount, tax_amount, total_amount 
            FROM Accounts 
            ORDER BY transaction_date DESC 
            LIMIT 5
        """)
        sample_data = cursor.fetchall()
        for row in sample_data:
            print(row)

    except sqlite3.Error as e:
        print(f"SQLite error: {str(e)}")
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    test_query() 