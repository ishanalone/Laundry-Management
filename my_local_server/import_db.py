import sqlite3
import os

def import_database():
    try:
        # Get the absolute path to the database file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        instance_dir = os.path.join(current_dir, 'instance')
        db_path = os.path.join(instance_dir, 'database.db')
        backup_path = os.path.join(current_dir, 'database_backup.sql')
        
        # Create instance directory if it doesn't exist
        os.makedirs(instance_dir, exist_ok=True)
        
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Read the SQL file with error handling for different encodings
        encodings_to_try = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        sql_commands = None
        
        for encoding in encodings_to_try:
            try:
                with open(backup_path, 'r', encoding=encoding) as f:
                    sql_commands = f.read()
                break  # If successful, break the loop
            except UnicodeDecodeError:
                continue
        
        if sql_commands is None:
            raise Exception("Could not decode the SQL file with any of the attempted encodings")
        
        # Split and execute commands
        # Split on semicolon but ignore semicolons inside quotes
        import re
        commands = re.split(r';(?=(?:[^\']*\'[^\']*\')*[^\']*$)', sql_commands)
        
        for command in commands:
            command = command.strip()
            if command:
                try:
                    cursor.execute(command)
                except sqlite3.Error as e:
                    print(f"Error executing command: {command[:100]}...")
                    print(f"Error message: {str(e)}")
                    continue
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
        print(f"Database successfully imported to {db_path}")
        return db_path
        
    except Exception as e:
        raise Exception(f"Error importing database: {str(e)}")

if __name__ == "__main__":
    try:
        db_path = import_database()
        print(f"Database path: {db_path}")
    except Exception as e:
        print(f"Error: {str(e)}") 