from accounting_agent import AccountingAgent
import os

def main():
    try:
        # Get the correct database path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(current_dir, 'my_local_server', 'instance', 'database.db')
        
        # Initialize the accounting agent with the correct database path
        agent = AccountingAgent(
            db_path=db_path,
            base_url="http://localhost:1234"
        )
        
        print("Accounting Assistant initialized successfully!")
        
        # First, let's check the database schema
        schema = agent.get_table_schema()
        print("\nDatabase Schema:")
        for table, columns in schema.items():
            print(f"\nTable: {table}")
            for col in columns:
                print(f"  - {col['name']} ({col['type']})")
        
        # Now let's try a simple query
        question = "What tables are available in the database?"
        print(f"\nAnalyzing: {question}")
        analysis = agent.analyze_financial_data(question)
        print("\nAnalysis:", analysis)
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 