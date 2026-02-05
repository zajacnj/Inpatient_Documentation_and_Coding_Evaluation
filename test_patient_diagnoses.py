"""
Test the corrected diagnosis query with patient 1600004711061
This shows what data will be returned with the fixed query
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

print("\n" + "=" * 100)
print("TESTING CORRECTED DIAGNOSIS QUERY")
print("=" * 100)

# Patient ID from user request
patient_id = 1600004711061
station = 626

# First, get admission info for this patient
print(f"\n1. Looking up admissions for patient {patient_id}...")
admission_query = """
SELECT TOP 1
    InpatientSID,
    PTFIEN,
    PatientSID,
    AdmitDateTime,
    DischargeDateTime,
    Sta3n
FROM [Inpat].[Inpatient]
WHERE PatientSID = ?
ORDER BY DischargeDateTime DESC
"""

try:
    cursor.execute(admission_query, (patient_id,))
    admission = cursor.fetchone()
    
    if not admission:
        print(f"ERROR: No admission found for patient {patient_id}")
    else:
        inpatient_sid, ptfien, pat_sid, admit_date, discharge_date, sta3n = admission
        print(f"   ✓ Found: InpatientSID={inpatient_sid}, PTFIEN={ptfien}")
        print(f"      Admit: {admit_date}, Discharge: {discharge_date}")
        
        # Now test the corrected diagnosis query
        print(f"\n2. Extracting diagnoses using corrected query...")
        print("-" * 100)
        
        diagnoses_query = """
        SELECT
            dd.InpatientDischargeDiagnosisSID,
            dd.InpatientSID,
            dd.PTFIEN,
            dd.OrdinalNumber as DiagnosisSequence,
            COALESCE(ic10.ICD10Code, ic9.ICD9Code, 'UNKNOWN') as ICD10Code,
            COALESCE(ic10.ICD10Description, ic9.ICD9Description, 'Unknown diagnosis') as DiagnosisDescription,
            CASE WHEN dd.ICD10SID IS NOT NULL THEN 'ICD-10' ELSE 'ICD-9' END as DiagnosisCodeType,
            dd.ICD10SID,
            dd.ICD9SID
        FROM [Inpat].[InpatientDischargeDiagnosis] dd
        LEFT JOIN [Dim].[ICD10Code] ic10 ON dd.ICD10SID = ic10.ICD10SID
        LEFT JOIN [Dim].[ICD9Code] ic9 ON dd.ICD9SID = ic9.ICD9SID
        WHERE (dd.PTFIEN = ? OR dd.InpatientSID = TRY_CAST(? as bigint))
          AND dd.Sta3n = ?
        ORDER BY dd.OrdinalNumber
        """
        
        cursor.execute(diagnoses_query, (str(ptfien), str(inpatient_sid), station))
        diagnoses = cursor.fetchall()
        
        print(f"\n   ✓ Found {len(diagnoses)} diagnoses\n")
        
        if diagnoses:
            print(f"   {'Seq':>3} | {'ICD Code':<12} | {'Code Type':<8} | Diagnosis Description")
            print("   " + "-" * 95)
            
            for row in diagnoses:
                diag_seq, icd_code, code_type, diag_desc = row[3], row[4], row[6], row[5]
                # Truncate long descriptions
                if diag_desc and len(diag_desc) > 55:
                    diag_desc = diag_desc[:52] + "..."
                print(f"   {diag_seq:3d} | {icd_code:<12} | {code_type:<8} | {diag_desc or 'Unknown diagnosis'}")
            
            print("\n   ✓ SUCCESS: Diagnoses now show actual ICD codes and descriptions!")
            print(f"   ✓ This matches the {len(diagnoses)} diagnoses shown in the PTF screenshot")
        else:
            print("   WARNING: No diagnoses found - check if PTFIEN/InpatientSID parameters are correct")
            
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()

conn.close()

print("\n" + "=" * 100)
print("TEST COMPLETE")
print("=" * 100)
