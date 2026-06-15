"""
Quick script to compare which tables have INSERT statements in the MySQL dump
but are missing from the current Django schema (active_tables.json).
"""
import json
import re

DUMP_PATH = "./raw_dump.sql"
ACTIVE_TABLES_PATH = "./active_tables.json"

# Load active tables from Django schema
with open(ACTIVE_TABLES_PATH) as f:
    active_tables = set(json.load(f).keys())

# Extract all tables that have INSERT statements in the dump
dump_tables = {}
with open(DUMP_PATH, 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        m = re.match(r"INSERT INTO `?([a-zA-Z0-9_]+)`?", line.strip())
        if m:
            t = m.group(1).lower()
            dump_tables[t] = dump_tables.get(t, 0) + 1

print(f"\n{'='*60}")
print(f"Total tables with INSERTs in dump: {len(dump_tables)}")
print(f"Total active Django tables:        {len(active_tables)}")

missing = sorted([(t, c) for t, c in dump_tables.items() if t not in active_tables], key=lambda x: -x[1])
present = sorted([(t, c) for t, c in dump_tables.items() if t in active_tables], key=lambda x: -x[1])

print(f"\n✅ Tables that WILL be imported ({len(present)}):")
for t, c in present:
    print(f"   {t:<45} ({c} batches)")

print(f"\n❌ Tables that are SKIPPED — not in Django schema ({len(missing)}):")
for t, c in missing:
    print(f"   {t:<45} ({c} batches)")
