from accounting_agent import AccountingAgent

def main():
    try:
        # Initialize the accounting agent with your database
        agent = AccountingAgent(
            db_path="path/to/your/accounting.db",
            base_url="http://localhost:1234"
        )
        
        print("Accounting Assistant initialized successfully!")
        
        # Example: Analyze financial data
        question = "What were our total revenues for the last quarter?"
        print("\nAnalyzing:", question)
        analysis = agent.analyze_financial_data(question)
        print("\nAnalysis:", analysis)
        
        # Example: Generate a report
        print("\nGenerating Balance Sheet...")
        report = agent.get_financial_report(
            report_type="balance_sheet",
            period="2023-Q4"
        )
        print("\nReport:", report)
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 