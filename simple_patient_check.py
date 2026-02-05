"""
Direct query to find if patient exists
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

conn = pyodbc.connect(conn_string)
cursor = conn.cursor()

patient_id = 1600004711061

# Try querying Inpat.Inpatient directly
print(f"\nSearching for patient {patient_id} in Inpat.Inpatient...")
query = "SELECT TOP 1 PatientSID, InpatientSID, PTFIEN FROM [Inpat].[Inpatient] WHERE PatientSID = ?"

try:
    cursor.execute(query, (patient_id,))
    result = cursor.fetchone()
    
    if result:
        print(f"✓ Found!")
        print(f"  PatientSID: {result[0]}")
        print(f"  InpatientSID: {result[1]}")
        print(f"  PTFIEN: {result[2]}")
    else:
        print(f"✗ Patient not found")
        print("\nTrying to find all patients in database (first 5)...")
        query2 = "SELECT TOP 5 DISTINCT PatientSID FROM [Inpat].[Inpatient] ORDER BY PatientSID"
        cursor.execute(query2)
        results = cursor.fetchall()
        print(f"Sample PatientSIDs:")
        for row in results:
            print(f"  {row[0]}")
except Exception as e:
    print(f"ERROR: {e}")

conn.close()
