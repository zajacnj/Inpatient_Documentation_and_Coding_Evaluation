"""
Extract and display the actual 23 notes that were pulled for the test patient
"""
import json
from pathlib import Path
import pyodbc
from datetime import datetime

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

conn = pyodbc.connect(conn_string, timeout=30)
cursor = conn.cursor()

# Patient from the test run
patient_id = 14528763  # From logs: "Starting review for patient=14528763"
admission_id = "1600004711061"

# From logs, admission was between 2026-01-05 and 2026-01-06
# Let me search a broader range - from the notes screenshot, it looks like Jan 2026
admission_start = "2026-01-02"  # A few days before
admission_end = "2026-01-07"    # A few days after

print("\n" + "=" * 100)
print(f"EXTRACTING ACTUAL NOTES PULLED FOR PATIENT {patient_id}")
print("=" * 100)

# Provider classes to include
provider_classes = [
    "PHYSICIAN", "PHYSICIAN ASSISTANT", "RESIDENT PODIATRIST", "RESIDENT- ORAL SURGERY",
    "RESIDENT PSYCHIATRIST", "CONSULTANT", "RESIDENT-PHYSICIAN", "RESIDENT PHYSICIAN",
    "RESIDENT SURGEON", "FELLOW", "PSYCHIATRIST", "SURGEON", "WOC ATTENDING",
    "ORAL SURGEON", "PHYSICIAN (DUPLICATE)", "PHYSICIAN (CONTRACT)", "PHYSICIAN (WOC)",
    "ANESTHESIOLOGIST", "PULMONOLOGIST", "PATHOLOGIST", "STAFF PSYCHIATRIST",
    "HOUSESTAFF", "RESIDENT-DENTIST", "ORTHOPEDICS", "OPTOMETRY", "DO", "PA", "INTERN"
]

placeholders = ", ".join(["?" for _ in provider_classes])

query = f"""
SELECT
    td.TIUDocumentSID,
    ddef.TIUDocumentDefinitionPrintName as NoteType,
    td.ReferenceDateTime as NoteDateTime,
    s.ProviderClass as AuthorProviderClass
FROM [TIU].[TIUDocument] td
LEFT JOIN [Dim].[TIUDocumentDefinition] ddef
    ON td.TIUDocumentDefinitionSID = ddef.TIUDocumentDefinitionSID
INNER JOIN [STIUNotes].[TIUDocument_8925] txt
    ON td.TIUDocumentSID = txt.TIUDocumentSID
INNER JOIN [Staff].[Staff] s
    ON td.SignedByStaffSID = s.StaffSID
WHERE td.PatientSID = ?
  AND td.ReferenceDateTime >= ?
  AND td.ReferenceDateTime <= ?
  AND txt.ReportText IS NOT NULL
  AND s.ProviderClass IN ({placeholders})
ORDER BY td.ReferenceDateTime DESC
"""

try:
    cursor.execute(query, (patient_id, admission_start, admission_end, *provider_classes))
    notes = cursor.fetchall()
    
    print(f"\nTotal notes found: {len(notes)}\n")
    print(f"{'#':<3} | {'Date & Time':<20} | {'Provider Class':<30} | Note Type")
    print("-" * 120)
    
    for idx, row in enumerate(notes, 1):
        note_sid, note_type, note_datetime, provider_class = row
        dt_str = note_datetime.strftime("%Y-%m-%d %H:%M") if note_datetime else "NULL"
        note_type = (note_type or "UNKNOWN")[:45]
        provider_class = (provider_class or "UNKNOWN")[:28]
        print(f"{idx:<3} | {dt_str:<20} | {provider_class:<30} | {note_type}")
    
    print("\n" + "=" * 120)
    
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()

conn.close()
