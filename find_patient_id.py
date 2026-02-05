"""
Find patient ID format in database
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

# Try to find patient with ID starting with 1600004711
patient_id = 1600004711061

print(f"\nSearching for patient ID: {patient_id}")
print("=" * 80)

# Try direct match
query = "SELECT TOP 1 PatientSID FROM [Dim].[Patient] WHERE PatientSID = ?"
cursor.execute(query, (patient_id,))
result = cursor.fetchone()

if result:
    print(f"✓ Found patient: {result[0]}")
else:
    print(f"✗ Patient {patient_id} not found")
    print("\nTrying substring search...")
    
    # Try substring match
    query2 = "SELECT TOP 10 PatientSID FROM [Dim].[Patient] WHERE CAST(PatientSID as VARCHAR) LIKE '160000471%' ORDER BY PatientSID"
    cursor.execute(query2)
    results = cursor.fetchall()
    
    if results:
        print(f"Found {len(results)} patients with similar ID:")
        for row in results:
            print(f"  PatientSID: {row[0]}")
    else:
        print("No similar patients found")

conn.close()
