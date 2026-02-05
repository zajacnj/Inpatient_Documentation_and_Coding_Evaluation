"""
Test diagnosis query to see what ICD dimension tables are available
"""
import json
from pathlib import Path
import pyodbc

config_path = Path('config/database_config.json')
with open(config_path, 'r') as f:
    db_config = json.load(f)

conn_string = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={db_config['server']};"
    f"DATABASE={db_config['database']};"
    f"Trusted_Connection=yes"
)

conn = pyodbc.connect(conn_string)
cursor = conn.cursor()

# First, let's see what we can get from InpatientDischargeDiagnosis
print("\n=== Testing current diagnosis structure ===\n")

query = """
SELECT TOP 10 
    dd.InpatientDischargeDiagnosisSID,
    dd.InpatientSID,
    dd.OrdinalNumber,
    dd.ICD10SID,
    dd.ICD9SID,
    dd.PatientSID,
    dd.AdmitDateTime,
    dd.DischargeDateTime
FROM [Inpat].[InpatientDischargeDiagnosis] dd
WHERE dd.PatientSID = 1600004711061
ORDER BY dd.OrdinalNumber
"""

try:
    cursor.execute(query)
    rows = cursor.fetchall()
    print(f"Found {len(rows)} diagnoses for patient 1600004711061\n")
    for row in rows:
        print(f"  Ordinal: {row[2]:2d} | ICD10SID: {row[3]:10} | ICD9SID: {row[4]:10}")
    
    if rows:
        print("\n=== Now looking for ICD10 dimension table ===\n")
        # Try to find ICD10 dimension table
        icd10_sid = rows[0][3]  # Get first ICD10SID
        
        if icd10_sid:
            # Try different possible table names
            possible_tables = [
                "[Dim].[ICD10Code]",
                "[Dim].[ICD10]",
                "[Dim].[ICD10Diagnosis]",
                "[Dim].[Diagnosis]",
            ]
            
            for table in possible_tables:
                try:
                    test_query = f"SELECT TOP 1 * FROM {table} WHERE ICD10SID = ?"
                    cursor.execute(test_query, (icd10_sid,))
                    result = cursor.fetchone()
                    if result:
                        print(f"✓ Found table: {table}")
                        # Get column names
                        col_names = [desc[0] for desc in cursor.description]
                        print(f"  Columns: {', '.join(col_names[:8])}")
                        print(f"  Sample data: {result[:3]}")
                        break
                except Exception as e:
                    print(f"✗ Table {table} - {str(e)[:50]}")
        else:
            print("No ICD10SID found in first row")
            
        # Also try ICD9
        print("\n=== Now looking for ICD9 dimension table ===\n")
        icd9_sid = rows[0][4]
        
        if icd9_sid:
            possible_tables = [
                "[Dim].[ICD9Code]",
                "[Dim].[ICD9]",
                "[Dim].[ICD9Diagnosis]",
            ]
            
            for table in possible_tables:
                try:
                    test_query = f"SELECT TOP 1 * FROM {table} WHERE ICD9SID = ?"
                    cursor.execute(test_query, (icd9_sid,))
                    result = cursor.fetchone()
                    if result:
                        print(f"✓ Found table: {table}")
                        col_names = [desc[0] for desc in cursor.description]
                        print(f"  Columns: {', '.join(col_names[:8])}")
                        print(f"  Sample data: {result[:3]}")
                        break
                except Exception as e:
                    print(f"✗ Table {table} - {str(e)[:50]}")
        else:
            print("No ICD9SID found in first row")
            
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

conn.close()
