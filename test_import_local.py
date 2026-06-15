import os
import sys
import re
import sqlite3
import subprocess

def create_schema():
    db_path = "/Users/vikhil/Desktop/spilbloo/spilbloo_backend/test_db.sqlite3"
    if os.path.exists(db_path):
        os.remove(db_path)
        
    print("[-] Creating schema via Django migrations on local SQLite database...")
    env = os.environ.copy()
    env["USE_SQLITE"] = "1"
    env["SQLITE_DB_PATH"] = db_path
    
    try:
        subprocess.run(
            ["python3", "manage.py", "migrate"],
            env=env,
            check=True,
            capture_output=True,
            text=True
        )
        print("[+] Schema created successfully!")
    except subprocess.CalledProcessError as e:
        print(f"[!] Django migration failed: {e.stderr}")
        sys.exit(1)

    # Extract active tables and their columns from SQLite
    import json
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    
    table_columns = {}
    for t in tables:
        cursor.execute(f"PRAGMA table_info({t});")
        table_columns[t.lower()] = [row[1].lower() for row in cursor.fetchall()]
    conn.close()
    
    tables_file = "/Users/vikhil/Desktop/spilbloo/spilbloo_backend/active_tables.json"
    with open(tables_file, 'w', encoding='utf-8') as f:
        json.dump(table_columns, f, indent=2)
            
    print(f"[+] Active tables saved to {tables_file}")
    return tables_file

def run_conversion(tables_file):
    input_path = "/Users/vikhil/Downloads/therapy_app_db (1).sql"
    output_path = "/Users/vikhil/Desktop/spilbloo/spilbloo_backend/test_output.sql"
    
    # Import the conversion logic directly
    from convert_mysql_to_postgres import convert_mysql_to_postgres
    convert_mysql_to_postgres(input_path, output_path, tables_file)
    
    return output_path

def test_import(sql_path):
    db_path = "/Users/vikhil/Desktop/spilbloo/spilbloo_backend/test_db.sqlite3"
    print("[-] Importing filtered SQL into local SQLite database...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    success_count = 0
    error_count = 0
    
    with open(sql_path, 'r', encoding='utf-8') as f:
        # Simple split on statements
        statements = f.read().split(';\n')
        
    for stmt in statements:
        stmt = stmt.strip()
        if not stmt or not stmt.upper().startswith("INSERT INTO"):
            continue
            
        try:
            cursor.execute(stmt)
            success_count += 1
        except Exception as e:
            print(f"[!] Error executing statement: {stmt[:100]}... Error: {e}")
            error_count += 1
            
    conn.commit()
    conn.close()
    
    print(f"\n[+] Verification Complete:")
    print(f"    - Successfully imported: {success_count} statements.")
    print(f"    - Failed: {error_count} statements.")
    
    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)
    if os.path.exists(sql_path):
        os.remove(sql_path)
    # Keep active_tables.json for diagnostic purposes (can delete manually)
    # active_tables_file = "/Users/vikhil/Desktop/spilbloo/spilbloo_backend/active_tables.json"
    # if os.path.exists(active_tables_file):
    #     os.remove(active_tables_file)

if __name__ == '__main__':
    tables_file = create_schema()
    sql_file = run_conversion(tables_file)
    test_import(sql_file)
