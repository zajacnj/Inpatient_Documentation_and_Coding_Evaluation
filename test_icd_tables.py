"""
Quick test to check if ICD dimension tables exist
"""
import json
from pathlib import Path
import pyodbc

config_path = Path('config/database_config.json')
with open(config_path, 'r') as f:
    config = json.load(f)

db_config = config['databases']['LSV']

conn_string = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={db_config['server']};"
    f"DATABASE={db_config['database']};"
    f"Trusted_Connection=yes"
)

print("Testing ICD table existence...")
print("=" * 80)

try:
    conn = pyodbc.connect(conn_string, timeout=10)
    cursor = conn.cursor()
    
    # Test 1: Check if ICD10Code table exists
    print("\n1. Testing Dim.ICD10Code...")
    try:
        cursor.execute("SELECT TOP 1 ICD10SID, ICD10Code FROM [Dim].[ICD10Code]")
        result = cursor.fetchone()
        if result:
            print(f"   ✓ EXISTS - Sample: ICD10SID={result[0]}, ICD10Code={result[1]}")
    except Exception as e:
        print(f"   ✗ DOES NOT EXIST - Error: {str(e)[:100]}")
    
    # Test 2: Check if ICD9Code table exists
    print("\n2. Testing Dim.ICD9Code...")
    try:
        cursor.execute("SELECT TOP 1 ICD9SID, ICD9Code FROM [Dim].[ICD9Code]")
        result = cursor.fetchone()
        if result:
            print(f"   ✓ EXISTS - Sample: ICD9SID={result[0]}, ICD9Code={result[1]}")
    except Exception as e:
        print(f"   ✗ DOES NOT EXIST - Error: {str(e)[:100]}")
    
    # Test 3: Find what ICD tables DO exist
    print("\n3. Finding all tables with 'ICD' in name...")
    query = """
    SELECT TABLE_SCHEMA, TABLE_NAME 
    FROM INFORMATION_SCHEMA.TABLES 
    WHERE TABLE_NAME LIKE '%ICD%' 
    ORDER BY TABLE_SCHEMA, TABLE_NAME
    """
    cursor.execute(query)
    tables = cursor.fetchall()
    
    if tables:
        print(f"   Found {len(tables)} ICD-related tables:")
        for schema, table in tables[:20]:  # Limit to first 20
            print(f"   - {schema}.{table}")
    else:
        print("   No ICD tables found")
    
    conn.close()
    print("\n" + "=" * 80)
    
except Exception as e:
    print(f"\nFATAL ERROR: {e}")
    import traceback
    traceback.print_exc()
