"""
Diagnostic: Check why provider class filtering returns 0 notes
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

print("Connecting to database...")
conn = pyodbc.connect(conn_string, timeout=30)
cursor = conn.cursor()

patient_id = 14528763
admission_start = "2026-01-02"
admission_end = "2026-01-07"

print("\n" + "=" * 100)
print("DIAGNOSTIC: Checking Provider Class Filtering")
print("=" * 100)

# Test 1: Check how many notes exist WITHOUT provider filter
print("\n1. Notes WITHOUT provider class filter:")
query1 = """
SELECT COUNT(*) as NoteCount
FROM [TIU].[TIUDocument] td
INNER JOIN [STIUNotes].[TIUDocument_8925] txt
    ON td.TIUDocumentSID = txt.TIUDocumentSID
WHERE td.PatientSID = ?
  AND td.ReferenceDateTime >= ?
  AND td.ReferenceDateTime <= ?
  AND txt.ReportText IS NOT NULL
"""
cursor.execute(query1, (patient_id, admission_start, admission_end))
result = cursor.fetchone()
print(f"   Total notes: {result[0]}")

# Test 2: Check how many have a matching Staff record
print("\n2. Notes WITH Staff table join (no provider filter):")
query2 = """
SELECT COUNT(*) as NoteCount
FROM [TIU].[TIUDocument] td
INNER JOIN [STIUNotes].[TIUDocument_8925] txt
    ON td.TIUDocumentSID = txt.TIUDocumentSID
INNER JOIN [Staff].[Staff] s
    ON td.SignedByStaffSID = s.StaffSID
WHERE td.PatientSID = ?
  AND td.ReferenceDateTime >= ?
  AND td.ReferenceDateTime <= ?
  AND txt.ReportText IS NOT NULL
"""
cursor.execute(query2, (patient_id, admission_start, admission_end))
result = cursor.fetchone()
print(f"   Notes with Staff match: {result[0]}")

# Test 3: Show what provider classes actually exist for these notes
print("\n3. Actual Provider Classes for these notes:")
query3 = """
SELECT 
    s.ProviderClass,
    COUNT(*) as Count
FROM [TIU].[TIUDocument] td
INNER JOIN [STIUNotes].[TIUDocument_8925] txt
    ON td.TIUDocumentSID = txt.TIUDocumentSID
INNER JOIN [Staff].[Staff] s
    ON td.SignedByStaffSID = s.StaffSID
WHERE td.PatientSID = ?
  AND td.ReferenceDateTime >= ?
  AND td.ReferenceDateTime <= ?
  AND txt.ReportText IS NOT NULL
GROUP BY s.ProviderClass
ORDER BY Count DESC
"""
cursor.execute(query3, (patient_id, admission_start, admission_end))
results = cursor.fetchall()
print(f"   Provider Classes found:")
for provider_class, count in results:
    print(f"   - {provider_class or '(NULL)'}: {count} notes")

# Test 4: Check with our filter list
print("\n4. Testing with our provider class filter:")
provider_classes = [
    "PHYSICIAN", "PHYSICIAN ASSISTANT", "RESIDENT PODIATRIST", "RESIDENT- ORAL SURGERY",
    "RESIDENT PSYCHIATRIST", "CONSULTANT", "RESIDENT-PHYSICIAN", "RESIDENT PHYSICIAN",
    "RESIDENT SURGEON", "FELLOW", "PSYCHIATRIST", "SURGEON", "WOC ATTENDING",
    "ORAL SURGEON", "PHYSICIAN (DUPLICATE)", "PHYSICIAN (CONTRACT)", "PHYSICIAN (WOC)",
    "ANESTHESIOLOGIST", "PULMONOLOGIST", "PATHOLOGIST", "STAFF PSYCHIATRIST",
    "HOUSESTAFF", "RESIDENT-DENTIST", "ORTHOPEDICS", "OPTOMETRY", "DO", "PA", "INTERN"
]
placeholders = ", ".join(["?" for _ in provider_classes])

query4 = f"""
SELECT COUNT(*) as NoteCount
FROM [TIU].[TIUDocument] td
INNER JOIN [STIUNotes].[TIUDocument_8925] txt
    ON td.TIUDocumentSID = txt.TIUDocumentSID
INNER JOIN [Staff].[Staff] s
    ON td.SignedByStaffSID = s.StaffSID
WHERE td.PatientSID = ?
  AND td.ReferenceDateTime >= ?
  AND td.ReferenceDateTime <= ?
  AND txt.ReportText IS NOT NULL
  AND s.ProviderClass IN ({placeholders})
"""
cursor.execute(query4, (patient_id, admission_start, admission_end, *provider_classes))
result = cursor.fetchone()
print(f"   Notes matching our filter: {result[0]}")

print("\n" + "=" * 100)
conn.close()
