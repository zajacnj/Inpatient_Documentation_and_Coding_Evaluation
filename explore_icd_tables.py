"""
Explore ICD dimension tables to understand available columns for diagnosis mapping
"""
import json
import os
from pathlib import Path
import pyodbc

# Load database config
config_path = Path('config/database_config.json')
with open(config_path, 'r') as f:
    db_config = json.load(f)

# Connect to database
conn_string = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={db_config['server']};"
    f"DATABASE={db_config['database']};"
    f"Trusted_Connection=yes"
)

try:
    conn = pyodbc.connect(conn_string)
    cursor = conn.cursor()
    
    print("=" * 80)
    print("EXPLORING ICD DIMENSION TABLES")
    print("=" * 80)
    
    # Get list of all tables in Dim schema
    query = """
    SELECT TABLE_SCHEMA, TABLE_NAME 
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = 'Dim'
    AND (TABLE_NAME LIKE '%ICD%' OR TABLE_NAME LIKE '%Diagnosis%')
    ORDER BY TABLE_NAME
    """
    
    print("\n1. Finding ICD-related tables in Dim schema:")
    print("-" * 80)
    cursor.execute(query)
    icd_tables = cursor.fetchall()
    for schema, table in icd_tables:
        print(f"  - {schema}.{table}")
    
    # For each ICD table, get columns
    for schema, table in icd_tables:
        print(f"\n2. Columns in {schema}.{table}:")
        print("-" * 80)
        col_query = f"""
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = '{schema}' AND TABLE_NAME = '{table}'
        ORDER BY ORDINAL_POSITION
        """
        cursor.execute(col_query)
        columns = cursor.fetchall()
        for col_name, data_type, nullable in columns:
            null_str = "NULL" if nullable == 'YES' else "NOT NULL"
            print(f"  - {col_name:40} {data_type:20} {null_str}")
    
    # Sample data from ICD10 table if it exists
    print("\n3. Sample data from ICD tables:")
    print("-" * 80)
    for schema, table in icd_tables:
        if 'ICD10' in table:
            print(f"\nSample from {schema}.{table}:")
            sample_query = f"SELECT TOP 5 * FROM {schema}.{table}"
            cursor.execute(sample_query)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            print(f"  Columns: {', '.join(columns[:5])}")
            for row in rows:
                print(f"  {row}")
    
    conn.close()
    print("\n" + "=" * 80)
    print("Exploration complete!")
    print("=" * 80)
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
