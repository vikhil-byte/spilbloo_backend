import sys
import os
import re
import json
import subprocess

DJANGO_DEFAULTS = {
    # AbstractUser system booleans
    'is_superuser': '0',
    'is_staff': '0',
    'is_active': '1',
    'date_joined': "CURRENT_TIMESTAMP",
    # AbstractUser string fields with empty string default
    'first_name': "''",
    'last_name': "''",
    'password': "''",
    # Custom User model fields with numeric defaults
    'tos': '0',
    'role_id': '2',
    'state_id': '1',
    'type_id': '0',
    'login_error_count': '0'
}

def load_db_config(env_path):
    config = {
        'POSTGRES_USER': 'db_user',
        'POSTGRES_DB': 'therapy_app_db'
    }
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line_strip = line.strip()
                if '=' in line_strip and not line_strip.startswith('#'):
                    key, val = line_strip.split('=', 1)
                    config[key] = val.strip()
    return config

def get_active_tables(env_path):
    config = load_db_config(env_path)
    compose_path = os.path.join(os.path.dirname(env_path), "docker-compose.yml")
    
    cmd = [
        "docker-compose",
        "-f", compose_path,
        "exec", "-T", "db",
        "psql", "-U", config['POSTGRES_USER'], "-d", config['POSTGRES_DB'],
        "-t", "-A",
        "-c", "SELECT table_name || '.' || column_name FROM information_schema.columns WHERE table_schema='public';"
    ]
    try:
        print(f"[-] Querying running Postgres container for active tables using: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        table_columns = {}
        for line in result.stdout.split('\n'):
            line = line.strip()
            if not line or '.' not in line:
                continue
            t_name, c_name = line.split('.', 1)
            t_name = t_name.lower()
            c_name = c_name.lower()
            if t_name not in table_columns:
                table_columns[t_name] = []
            table_columns[t_name].append(c_name)
        return table_columns
    except Exception as e:
        print(f"[!] Warning: Could not fetch active tables from database: {e}")
        print("[-] Proceeding without active table filtering.")
        return None

def parse_values(values_str):
    tuples = []
    current_tuple = []
    in_string = False
    escape_next = False
    in_tuple = False
    current_val = []
    
    for char in values_str:
        if not in_tuple:
            if char == '(':
                in_tuple = True
                current_tuple = []
                current_val = []
            continue
            
        if escape_next:
            current_val.append(char)
            escape_next = False
            continue
            
        if char == '\\':
            current_val.append(char)
            escape_next = True
            continue
            
        if char == "'":
            current_val.append(char)
            in_string = not in_string
            continue
            
        if in_string:
            current_val.append(char)
            continue
            
        if char == ',':
            current_tuple.append(''.join(current_val).strip())
            current_val = []
            continue
            
        if char == ')':
            current_tuple.append(''.join(current_val).strip())
            tuples.append(current_tuple)
            in_tuple = False
            current_val = []
            continue
            
        current_val.append(char)
        
    return tuples

def filter_insert_statement(stmt_clean, active_table_columns, warned_tables=None):
    if warned_tables is None:
        warned_tables = set()

    match = re.match(r"(?i)INSERT\s+INTO\s+([a-zA-Z0-9_\-]+)\s*\((.*?)\)\s*VALUES", stmt_clean, re.DOTALL)
    if not match:
        return stmt_clean
        
    table_name = match.group(1).lower()
    if table_name not in active_table_columns:
        return None
        
    active_cols = active_table_columns[table_name]
    cols_str = match.group(2)
    columns = [c.strip().lower() for c in cols_str.split(',')]
    
    # 1. Remove columns that do not exist in the target schema
    missing_cols = [c for c in columns if c not in active_cols]
    if missing_cols and table_name not in warned_tables:
        print(f"[-] Table {table_name} has missing columns in target schema: {missing_cols}. Filtering columns...")
        warned_tables.add(table_name)
    
    indices_to_keep = [i for i, col in enumerate(columns) if col in active_cols]
    if not indices_to_keep:
        return None
        
    # 2. Check for required Django fields that are in active_cols but missing from columns list
    defaults_to_add = {}
    for field, default_val in DJANGO_DEFAULTS.items():
        if field in active_cols and field not in columns:
            defaults_to_add[field] = default_val
            
    if defaults_to_add and f"{table_name}__defaults" not in warned_tables:
        print(f"[-] Table {table_name} is missing Django fields {list(defaults_to_add.keys())}. Adding defaults...")
        warned_tables.add(f"{table_name}__defaults")
        
    new_columns = [columns[i] for i in indices_to_keep]
    for field in defaults_to_add:
        new_columns.append(field)
    
    values_idx = stmt_clean.upper().find("VALUES")
    values_str = stmt_clean[values_idx + len("VALUES"):]
    
    tuples = parse_values(values_str)
    
    filtered_tuples = []
    for t in tuples:
        if len(t) != len(columns):
            print(f"[!] Warning: Value tuple length mismatch in {table_name}. Expected {len(columns)}, got {len(t)}.")
            return stmt_clean
        
        # Replace NULL values with defaults if the column has a defined fallback
        for i, col in enumerate(columns):
            if t[i].strip().upper() == 'NULL' and col in DJANGO_DEFAULTS:
                t[i] = DJANGO_DEFAULTS[col]
                
        filtered_t = [t[i] for i in indices_to_keep]
        for field in defaults_to_add:
            filtered_t.append(defaults_to_add[field])
        filtered_tuples.append(f"({', '.join(filtered_t)})")
        
    new_stmt = f"INSERT INTO {table_name} ({', '.join(new_columns)}) VALUES\n" + ",\n".join(filtered_tuples) + ";"
    return new_stmt

def convert_mysql_to_postgres(input_path, output_path, env_path=None):
    print(f"[-] Reading from {input_path}...")
    with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    active_tables = None
    if env_path:
        if env_path.endswith('.json') or env_path.endswith('.txt') or 'active_tables' in env_path:
            if os.path.exists(env_path):
                # Check if it is JSON or TXT
                if env_path.endswith('.json'):
                    with open(env_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    active_tables = {}
                    for k, v in data.items():
                        if isinstance(v, list):
                            active_tables[k.lower()] = [c.lower() for c in v]
                        else:
                            active_tables[k.lower()] = []
                    print(f"[+] Loaded {len(active_tables)} active tables from JSON file: {env_path}")
                else:
                    with open(env_path, 'r', encoding='utf-8') as f:
                        active_tables = {line.strip().lower(): [] for line in f if line.strip()}
                    print(f"[+] Loaded {len(active_tables)} active tables from text file: {env_path}")
            else:
                print(f"[!] Warning: Table file {env_path} does not exist.")
        else:
            active_tables = get_active_tables(env_path)
            if active_tables:
                print(f"[+] Loaded {len(active_tables)} active tables from Postgres.")

    print("[-] Splitting SQL file into statements using state-machine...")
    
    statements = []
    current_statement = []
    in_string = False
    escape_next = False
    
    for char in content:
        current_statement.append(char)
        
        if escape_next:
            escape_next = False
            continue
            
        if char == '\\':
            escape_next = True
            continue
            
        if char == "'":
            in_string = not in_string
            continue
            
        if char == ';' and not in_string:
            statements.append(''.join(current_statement))
            current_statement = []
            
    if current_statement:
        statements.append(''.join(current_statement))

    print(f"[+] Found {len(statements)} total statements. Filtering and converting INSERTs...")
    
    insert_count = 0
    skipped_count = 0
    warned_tables = set()
    with open(output_path, 'w', encoding='utf-8') as f_out:
        f_out.write("SET session_replication_role = 'replica';\n")
        f_out.write("BEGIN;\n\n")
        
        for stmt in statements:
            stmt_strip = stmt.strip()
            if stmt_strip.upper().startswith("INSERT INTO"):
                stmt_clean = stmt_strip.replace('`', '')
                
                # Extract table name using regex
                match = re.match(r"(?i)INSERT\s+INTO\s+([a-zA-Z0-9_\-]+)", stmt_clean)
                if match:
                    table_name = match.group(1).lower()
                    if active_tables is not None and table_name not in active_tables:
                        skipped_count += 1
                        continue
                
                # Replace MySQL escaped single quotes (\') with standard SQL escaped single quotes ('')
                stmt_clean = re.sub(r"(?<!\\)\\'", "''", stmt_clean)
                
                # Filter columns if column info is available
                if active_tables is not None and isinstance(active_tables, dict):
                    stmt_clean = filter_insert_statement(stmt_clean, active_tables, warned_tables)
                    if stmt_clean is None:
                        skipped_count += 1
                        continue
                
                if not stmt_clean.endswith(';'):
                    stmt_clean += ';'
                    
                f_out.write(stmt_clean + "\n")
                insert_count += 1
                
        f_out.write("\nCOMMIT;\n")
        f_out.write("SET session_replication_role = 'origin';\n")
        
    print(f"[+] Successfully extracted and converted {insert_count} INSERT statements.")
    if active_tables is not None:
        print(f"[-] Skipped {skipped_count} statements/tables that do not exist or are filtered out.")
    print(f"[+] Output written to {output_path}")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python convert_mysql_to_postgres.py <input_file> <output_file> [path_to_spilbloo_backend_dir]")
        sys.exit(1)
    
    project_dir = sys.argv[3] if len(sys.argv) >= 4 else None
    env_file = os.path.join(project_dir, ".env") if project_dir else None
    
    convert_mysql_to_postgres(sys.argv[1], sys.argv[2], env_file)
