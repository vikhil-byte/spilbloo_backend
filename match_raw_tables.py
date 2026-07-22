import re
import json

raw_sql_path = "/Users/vikhil/Downloads/therapy_app_db_postgres.sql"
active_tables_path = "./active_tables.json"

with open(active_tables_path) as f:
    active_tables = set(json.load(f).keys())

raw_tables = set()
with open(raw_sql_path, 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        m = re.search(r"(?i)INSERT\s+INTO\s+`?([a-zA-Z0-9_\-]+)`?", line)
        if m:
            raw_tables.add(m.group(1).lower())

print("\n=== Summary of Tables in Raw SQL Dump ===")
print(f"Total tables with INSERTs in raw dump: {len(raw_tables)}")
print(f"Total active Django tables in schema:   {len(active_tables)}")

imported = sorted([t for t in raw_tables if t in active_tables])
skipped = sorted([t for t in raw_tables if t not in active_tables])

print(f"\n✅ Tables present in raw dump that ARE IN Django schema ({len(imported)}):")
for t in imported:
    print(f"   - {t}")

print(f"\n❌ Tables present in raw dump that ARE NOT IN Django schema ({len(skipped)}):")
for t in skipped:
    # Print first 20 to avoid overwhelming output, or print all if it's short
    print(f"   - {t}")
