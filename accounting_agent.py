from lm_studio_agent import LMStudioAgent
import sqlite3
import json

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
        
        Args:
            question (str): User's financial analysis question
        """
        try:
            # Get database schema for context
            schema = self.get_table_schema()
            
            # Create a detailed prompt with schema context
            analysis_prompt = f"""Based on the following database schema:
            {json.dumps(schema, indent=2)}
            
            Please help analyze this financial question: {question}
            
            If you need to query the database, please respond with a valid SQL query.
            Otherwise, provide your analysis and recommendations."""
            
            # Get initial response for query generation
            response = self.simple_chat(analysis_prompt, self.system_prompt)
            
            # Check if response contains SQL query
            if "SELECT" in response.upper():
                # Extract query and execute it
                query = response[response.upper().find("SELECT"):].split(";")[0] + ";"
                data = self.query_database(query)
                
                # Get final analysis with the data
                data_prompt = f"""Based on the query results:
                {json.dumps(data, indent=2)}
                
                Please provide a detailed analysis for the original question:
                {question}"""
                
                return self.simple_chat(data_prompt, self.system_prompt)
            
            return response
            
        except Exception as e:
            return f"Analysis error: {str(e)}"

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