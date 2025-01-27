from lm_studio_agent import LMStudioAgent
import sqlite3
import json
from flask import jsonify

class AccountingAgent(LMStudioAgent):
    def __init__(self, db_path, base_url="http://localhost:1234", **kwargs):
        """
        Initialize the Accounting Agent with database connection and LM Studio settings.
        
        Args:
            db_path (str): Path to the SQLite database file
            base_url (str): LM Studio API base URL
        """
        super().__init__(base_url=base_url, **kwargs)
        self.db_path = db_path
        self.system_prompt = """You are an expert accounting assistant with deep knowledge of:
        - Financial analysis
        - Bookkeeping
        - Tax regulations
        - Accounting principles
        - Financial reporting
        
        You have access to the accounting database and can help with queries and analysis.
        Always provide clear, professional responses with accurate financial information."""
        
    def connect_db(self):
        """Create a database connection"""
        try:
            return sqlite3.connect(self.db_path)
        except sqlite3.Error as e:
            raise Exception(f"Database connection error: {str(e)}")
            
    def get_table_schema(self):
        """Get the database schema information"""
        try:
            conn = self.connect_db()
            cursor = conn.cursor()
            
            # Get list of tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            schema = {}
            for table in tables:
                table_name = table[0]
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = cursor.fetchall()
                schema[table_name] = [
                    {"name": col[1], "type": col[2]} for col in columns
                ]
            
            conn.close()
            return schema
            
        except Exception as e:
            raise Exception(f"Error getting schema: {str(e)}")
    
    def query_database(self, query):
        """Execute a database query safely"""
        try:
            conn = self.connect_db()
            cursor = conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            conn.close()
            
            # Convert to list of dictionaries
            return [dict(zip(columns, row)) for row in results]
            
        except sqlite3.Error as e:
            raise Exception(f"Database query error: {str(e)}")
    
    def analyze_financial_data(self, question):
        """
        Analyze financial data based on user question.
        """
        try:
            schema = self.get_table_schema()
            
            # Create a more specific prompt with clear SQL guidelines
            analysis_prompt = f"""Based on the following database schema:
            {json.dumps(schema, indent=2)}
            
            Please help analyze this financial question: {question}
            
            If you need to query the database, follow these strict SQL guidelines:
            1. Use only standard SQLite syntax
            2. Start with 'SELECT' followed by specific column names (avoid SELECT *)
            3. Use proper table names: Accounts, Customer, Sales, DailyBalance
            4. For table aliases, use meaningful names like 'acc' for Accounts
            5. Use proper date functions: date('now', '-7 days') for date operations
            6. End with a semicolon
            
            Example valid queries:
            - SELECT amount, transaction_type FROM Accounts WHERE transaction_date >= date('now', '-7 days');
            - SELECT acc.transaction_date, acc.amount, acc.tax_amount, acc.total_amount, acc.order_no 
              FROM Accounts acc 
              WHERE acc.transaction_date >= date('now', '-30 days');
            - SELECT SUM(amount) as total, SUM(tax_amount) as tax_total, transaction_type, category 
              FROM Accounts 
              GROUP BY transaction_type, category;
            
            Provide either a valid SQL query or a clear analysis."""
            
            response = self.simple_chat(analysis_prompt, self.system_prompt)
            print(response)
            if "SELECT" in response.upper():
                
                query = self._clean_sql_query(response)
                print(query)
                try:
                    data = self.query_database(query)
                    
                    # Get analysis of the data
                    data_prompt = f"""Based on these query results:
                    {json.dumps(data, indent=2)}
                    
                    Provide a clear analysis addressing the original question:
                    {question}
                    
                    Include:
                    1. Summary of key findings
                    2. Relevant numbers and trends
                    3. Business insights or recommendations"""
                    
                    return self.simple_chat(data_prompt, self.system_prompt)
                    
                except sqlite3.Error as e:
                    return f"Database query error: {str(e)}. Please rephrase your question."
            
            return response
            
        except Exception as e:
            return f"Analysis error: {str(e)}"

    def _clean_sql_query(self, text):
        # Look for SQL query between triple backticks
        start = text.find('```')
        if start != -1:
            # Find the closing backticks after the start
            end = text.find('```', start + 3)
            if end != -1:
                # Extract the query between backticks
                query = text[start + 3:end].strip()
                # Remove 'sql' if it appears at the start
                if query.lower().startswith('sql'):
                    query = query[3:].strip()
                return query
        return text

    def get_financial_report(self, report_type, period=None):
        """
        Generate financial reports.
        
        Args:
            report_type (str): Type of report (e.g., 'balance_sheet', 'income_statement')
            period (str, optional): Time period for the report
        """
        try:
            report_prompt = f"""Please generate a {report_type} report"""
            if period:
                report_prompt += f" for the period: {period}"
            
            return self.analyze_financial_data(report_prompt)
            
        except Exception as e:
            return f"Report generation error: {str(e)}"

    def process_chat_message(self, message, conversation_history=None):
        """
        Process a chat message from the web UI.
        
        Args:
            message (str): User's message
            conversation_history (list): Previous messages in the conversation
            
        Returns:
            dict: Response containing assistant's message and any relevant data
        """
        try:
            # Get database schema for context
            schema = self.get_table_schema()
            
            # Build conversation context
            context = f"""Database Schema: {json.dumps(schema, indent=2)}
            
            Previous conversation:
            {self._format_conversation_history(conversation_history) if conversation_history else 'No previous context.'}
            
            User question: {message}
            """
            
            # Get initial response
            response = self.simple_chat(context, self.system_prompt)
            
            # Check if response contains SQL query
            if "SELECT" in response.upper():
                # Extract and execute query
                query = response[response.upper().find("SELECT"):].split(";")[0] + ";"
                data = self.query_database(query)
                
                # Get final analysis with the data
                data_context = f"""Based on the query results:
                {json.dumps(data, indent=2)}
                
                Please provide a clear explanation for the user."""
                
                final_response = self.simple_chat(data_context, self.system_prompt)
                
                return {
                    'message': final_response,
                    'data': data,
                    'query': query
                }
            
            return {
                'message': response,
                'data': None,
                'query': None
            }
            
        except Exception as e:
            return {
                'message': f"Error processing request: {str(e)}",
                'error': True
            }

    def _format_conversation_history(self, history):
        """Format conversation history for context"""
        if not history:
            return ""
        
        formatted = []
        for msg in history:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            formatted.append(f"{role}: {content}")
        
        return "\n".join(formatted) 