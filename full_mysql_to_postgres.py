import sys
import os
import re

TABLE_NAME_MAPPING = {
    # If any tables need to be explicitly mapped. We keep them identical to legacy.
}

def duration_str_to_seconds(val):
    if not val:
        return 0
    parts = val.split(':')
    if len(parts) == 3:
        try:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except ValueError:
            return 0
    elif len(parts) == 2:
        try:
            return int(parts[0]) * 60 + int(parts[1])
        except ValueError:
            return 0
    try:
        return int(val)
    except ValueError:
        return 0

def parse_values(values_str):
    tuples = []
    current_tuple = []
    in_string = False
    escape_next = False
    in_tuple = False
    current_val = []
    
    i = 0
    n = len(values_str)
    while i < n:
        char = values_str[i]
        
        if not in_tuple:
            if char == '(':
                in_tuple = True
                current_tuple = []
                current_val = []
            i += 1
            continue
            
        if escape_next:
            current_val.append(char)
            escape_next = False
            i += 1
            continue
            
        if char == '\\':
            current_val.append(char)
            escape_next = True
            i += 1
            continue
            
        if char == "'":
            if i + 1 < n and values_str[i+1] == "'":
                current_val.append("'")
                current_val.append("'")
                i += 2
                continue
            else:
                current_val.append(char)
                in_string = not in_string
                i += 1
                continue
                
        if in_string:
            current_val.append(char)
            i += 1
            continue
            
        if char == ',':
            current_tuple.append(''.join(current_val).strip())
            current_val = []
            i += 1
            continue
            
        if char == ')':
            current_tuple.append(''.join(current_val).strip())
            tuples.append(current_tuple)
            in_tuple = False
            current_val = []
            i += 1
            continue
            
        current_val.append(char)
        i += 1
        
    return tuples

def convert_create_table(stmt, table_numeric_cols):
    lines = stmt.split('\n')
    new_lines = []
    
    # Match CREATE TABLE `tablename`
    table_match = re.search(r"(?i)CREATE\s+TABLE\s+`?([a-zA-Z0-9_\-]+)`?", lines[0])
    if not table_match:
        return stmt
    
    table_name = table_match.group(1).lower()
    table_numeric_cols[table_name] = set()
    
    new_lines.append(f'CREATE TABLE "{table_name}" (')
    
    # Pre-scan for the presence of "id" column
    has_id = any(re.match(r'^\s*`?id`?\b', line.strip()) for line in lines)
    
    for line in lines[1:]:
        line_strip = line.strip()
        if not line_strip:
            continue
        
        # If it's the closing line of the table creation
        if line_strip.startswith(')') or line_strip.startswith(';'):
            new_lines.append(');')
            break
            
        # Ignore inline key/index definitions
        if line_strip.upper().startswith('KEY ') or line_strip.upper().startswith('KEY\t') or line_strip.upper().startswith('UNIQUE KEY '):
            continue
            
        # Remove foreign key constraints to make importing schema easier (inspectdb doesn't strictly need them)
        if line_strip.upper().startswith('CONSTRAINT ') or line_strip.upper().startswith('FOREIGN KEY '):
            continue
            
        # If the table has an id column, skip the PRIMARY KEY declaration at the bottom to avoid duplicate inline PK
        if has_id and line_strip.upper().startswith('PRIMARY KEY'):
            continue
            
        # Convert backticks to double quotes for column names
        line_clean = re.sub(r"`([a-zA-Z0-9_\-]+)`", r'"\1"', line_strip)
        
        # Parse column and check type
        col_match = re.match(r'^\s*"([a-zA-Z0-9_\-]+)"\s+([a-zA-Z0-9_]+)(\(.*?\))?', line_clean)
        if col_match:
            col_name = col_match.group(1).lower()
            data_type = col_match.group(2).lower()
            
            # Record numeric columns
            if data_type in ('int', 'integer', 'tinyint', 'smallint', 'mediumint', 'bigint', 'double', 'float', 'decimal', 'numeric'):
                table_numeric_cols[table_name].add(col_name)
                
            # Replace types
            if col_name == 'id':
                if data_type == 'bigint':
                    line_clean = re.sub(r'(?i)\bbigint(\(\d+\))?\s+NOT\s+NULL', 'bigserial PRIMARY KEY', line_clean)
                    line_clean = re.sub(r'(?i)\bbigint(\(\d+\))?', 'bigserial PRIMARY KEY', line_clean)
                else:
                    line_clean = re.sub(r'(?i)\bint(eger)?(\(\d+\))?\s+NOT\s+NULL', 'serial PRIMARY KEY', line_clean)
                    line_clean = re.sub(r'(?i)\bint(eger)?(\(\d+\))?', 'serial PRIMARY KEY', line_clean)
            elif 'auto_increment' in line_clean.lower():
                line_clean = re.sub(r'(?i)\bint(eger)?(\(\d+\))?\s+NOT\s+NULL\s+auto_increment', 'serial PRIMARY KEY', line_clean)
                line_clean = re.sub(r'(?i)\bbigint(\(\d+\))?\s+NOT\s+NULL\s+auto_increment', 'bigserial PRIMARY KEY', line_clean)
            else:
                # Type mappings
                line_clean = re.sub(r'(?i)\btinyint(\(\d+\))?', 'smallint', line_clean)
                line_clean = re.sub(r'(?i)\bint(eger)?(\(\d+\))?', 'integer', line_clean)
                line_clean = re.sub(r'(?i)\bbigint(\(\d+\))?', 'bigint', line_clean)
                line_clean = re.sub(r'(?i)\bdouble\b', 'double precision', line_clean)
                line_clean = re.sub(r'(?i)\bmediumtext\b', 'text', line_clean)
                line_clean = re.sub(r'(?i)\blongtext\b', 'text', line_clean)
                line_clean = re.sub(r'(?i)\bdatetime\b', 'timestamp', line_clean)
                
            # Remove character set / collation definitions
            line_clean = re.sub(r'(?i)\bcharacter\s+set\s+[a-zA-Z0-9_]+\b', '', line_clean)
            line_clean = re.sub(r'(?i)\bcollate\s+[a-zA-Z0-9_]+\b', '', line_clean)
            
        # Standardize PRIMARY KEY line if present at the end
        if line_clean.upper().startswith('PRIMARY KEY'):
            # e.g., PRIMARY KEY ("id")
            line_clean = re.sub(r"`", '"', line_clean)
            
        new_lines.append('  ' + line_clean)
        
    # Filter trailing commas in lines list
    cleaned_body_lines = []
    body_lines = new_lines[1:-1]
    for i, l in enumerate(body_lines):
        l_strip = l.strip()
        if not l_strip:
            continue
        if i == len(body_lines) - 1:
            if l_strip.endswith(','):
                l = l.rstrip().rstrip(',')
        cleaned_body_lines.append(l)
        
    final_stmt = new_lines[0] + '\n' + '\n'.join(cleaned_body_lines) + '\n' + new_lines[-1]
    return final_stmt

def convert_insert(stmt, table_numeric_cols):
    stmt_clean = stmt.replace('`', '')
    
    match = re.match(r"(?i)INSERT\s+INTO\s+([a-zA-Z0-9_\-]+)\s*\((.*?)\)\s*VALUES", stmt_clean, re.DOTALL)
    if not match:
        return stmt_clean
        
    table_name = match.group(1).lower()
    cols_str = match.group(2)
    columns = [c.strip().lower() for c in cols_str.split(',')]
    quoted_columns = [f'"{c}"' for c in columns]
    
    # Replace MySQL escaped single quotes (\') with standard SQL escaped single quotes ('')
    stmt_clean = re.sub(r"(?<!\\)\\'", "''", stmt_clean)
    
    values_idx = stmt_clean.upper().find("VALUES")
    values_str = stmt_clean[values_idx + len("VALUES"):]
    
    tuples = parse_values(values_str)
    filtered_tuples = []
    
    numeric_set = table_numeric_cols.get(table_name, set())
    
    for t in tuples:
        if len(t) != len(columns):
            return stmt_clean
            
        for i, col in enumerate(columns):
            val_clean = t[i].strip().strip("'")
            if val_clean in ('0000-00-00 00:00:00', '0000-00-00'):
                t[i] = 'NULL'
            
            # Check for numeric column with empty value
            if col in numeric_set:
                if val_clean == '':
                    t[i] = '0'
                elif col == 'duration' and table_name == 'tbl_call':
                    t[i] = str(duration_str_to_seconds(val_clean))
                    
        filtered_tuples.append(f"({', '.join(t)})")
        
    return f'INSERT INTO "{table_name}" ({", ".join(quoted_columns)}) VALUES\n' + ",\n".join(filtered_tuples) + ";"

def convert_mysql_to_postgres(input_path, output_path):
    print(f"[-] Reading MySQL raw dump from {input_path}...")
    with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    print("[-] Parsing SQL statements...")
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

    print(f"[+] Found {len(statements)} total statements. Starting syntax conversion...")
    
    table_numeric_cols = {}
    converted_count = 0
    
    with open(output_path, 'w', encoding='utf-8') as f_out:
        f_out.write("SET session_replication_role = 'replica';\n")
        f_out.write("BEGIN;\n\n")
        
        for stmt in statements:
            stmt_strip = stmt.strip()
            
            # Slice starting at statement keyword if leading comments exist
            create_idx = stmt_strip.upper().find("CREATE TABLE")
            insert_idx = stmt_strip.upper().find("INSERT INTO")
            
            if create_idx != -1 and (insert_idx == -1 or create_idx < insert_idx):
                # Translate CREATE TABLE
                stmt_clean = stmt_strip[create_idx:]
                converted_stmt = convert_create_table(stmt_clean, table_numeric_cols)
                f_out.write(converted_stmt + "\n\n")
                converted_count += 1
            elif insert_idx != -1:
                # Translate INSERT INTO
                stmt_clean = stmt_strip[insert_idx:]
                converted_stmt = convert_insert(stmt_clean, table_numeric_cols)
                f_out.write(converted_stmt + "\n")
                converted_count += 1
                
        f_out.write("\nCOMMIT;\n")
        f_out.write("SET session_replication_role = 'origin';\n")
        
    print(f"[+] Converted {converted_count} schema/data statements.")
    print(f"[+] Output written to {output_path}")

if __name__ == '__main__':
    convert_mysql_to_postgres('raw_dump.sql', 'full_postgres_import.sql')
