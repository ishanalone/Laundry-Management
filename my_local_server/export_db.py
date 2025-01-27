import sqlite3
import os

def export_db():
    # Source database path
    src_db = "instance/database.db"
    # Backup file path
    backup_file = "database_backup.sql"
    
    try:
        # Connect to the database
        conn = sqlite3.connect(src_db)
        
        # Open backup file
        with open(backup_file, 'w') as f:
            # Iterate over the dump
            for line in conn.iterdump():
                f.write('%s\n' % line)
        
        print(f"Database successfully exported to {backup_file}")
        
    except Exception as e:
        print(f"Error exporting database: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    export_db() 