import sqlite3
import os

def import_db():
    # Destination database path
    dest_db = "path/to/new/location/database.db"
    # Backup file path
    backup_file = "database_backup.sql"
    
    try:
        # Remove destination db if it exists
        if os.path.exists(dest_db):
            os.remove(dest_db)
        
        # Connect to new database
        conn = sqlite3.connect(dest_db)
        
        # Read and execute the SQL script
        with open(backup_file, 'r') as f:
            sql_script = f.read()
            conn.executescript(sql_script)
        
        conn.commit()
        print(f"Database successfully imported to {dest_db}")
        
    except Exception as e:
        print(f"Error importing database: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    import_db() 