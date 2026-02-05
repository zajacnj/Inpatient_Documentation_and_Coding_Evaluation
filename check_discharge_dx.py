"""Check discharge diagnoses for InpatientSID 1600004711061"""
import pyodbc
from app.database.connection import load_database_config

# Load config
db_config = load_database_config()
server = db_config['databases']['LSV']['server']
database = db_config['databases']['LSV']['database']

# Connect
conn_str = f'DRIVER={{SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;'
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

# Query discharge diagnoses for InpatientSID = 1600004711061
query = '''
SELECT 
    d.InpatientSID,
    d.ICD10SID,
    d.ICD9SID,
    d.OrdinalNumber,
    d.InpatientDischargeDiagnosisSID,
    d.PTFIEN,
    icd10.ICD10Code,
    icd9.ICD9Code
FROM [CDWWork].[Inpat].[InpatientDischargeDiagnosis] d
LEFT JOIN [CDWWork].[Dim].[ICD10] icd10 ON d.ICD10SID = icd10.ICD10SID
LEFT JOIN [CDWWork].[Dim].[ICD9] icd9 ON d.ICD9SID = icd9.ICD9SID
WHERE d.InpatientSID = 1600004711061
ORDER BY d.OrdinalNumber
'''

print(f'\n=== Discharge Diagnoses for InpatientSID: 1600004711061 ===\n')

try:
    cursor.execute(query)
    rows = cursor.fetchall()
    
    print(f'Total diagnoses found: {len(rows)}\n')
    
    if rows:
        print(f'{'Ordinal':<10} {'Code':<15} {'ICD10SID':<15} {'ICD9SID':<15}')
        print('-' * 60)
        
        expected_codes = {
            'C34.11', 'G93.6', 'C79.31', 'C77.0', 'G93.40', 'I67.89', 
            'I16.0', 'R53.1', 'C61', 'D63.0', 'I10', 'E78.5', 
            'F17.210', 'W88.1XXA', 'Z92.3', 'Z92.21', 'Z91.81'
        }
        
        found_codes = set()
        
        for row in rows:
            ordinal = row.OrdinalNumber if row.OrdinalNumber else '--'
            
            if row.ICD10Code:
                code = row.ICD10Code
                found_codes.add(code)
            elif row.ICD9Code:
                code = row.ICD9Code
                found_codes.add(code)
            else:
                code = f'NO CODE'
            
            icd10sid = str(row.ICD10SID) if row.ICD10SID else 'NULL'
            icd9sid = str(row.ICD9SID) if row.ICD9SID else 'NULL'
            
            # Ordinal 1 is typically principal
            marker = '★ Principal' if ordinal == 1 else ''
            print(f'{str(ordinal):<10} {code:<15} {icd10sid:<15} {icd9sid:<15} {marker}')
        
        print(f'\n=== Comparison with Expected Diagnoses ===\n')
        print(f'Found {len(found_codes)} diagnosis codes in database')
        print(f'Expected {len(expected_codes)} diagnosis codes\n')
        
        missing = expected_codes - found_codes
        if missing:
            print(f'❌ MISSING {len(missing)} codes:')
            for code in sorted(missing):
                print(f'   - {code}')
        else:
            print('✓ All expected diagnosis codes found')
            
        extra = found_codes - expected_codes
        if extra:
            print(f'\n⚠ EXTRA {len(extra)} codes (not in expected list):')
            for code in sorted(extra):
                print(f'   - {code}')
                
    else:
        print('❌ No diagnoses found for this InpatientSID')
        print('\nTrying to verify if this InpatientSID exists...')
        
        verify_query = '''
        SELECT InpatientSID, PatientSID, AdmitDateTime, DischargeDateTime
        FROM [CDWWork].[Inpat].[Inpatient]
        WHERE InpatientSID = 1600004711061
        '''
        cursor.execute(verify_query)
        admit_rows = cursor.fetchall()
        
        if admit_rows:
            print('✓ InpatientSID exists in Inpat.Inpatient table:')
            for r in admit_rows:
                print(f'  PatientSID: {r.PatientSID}')
                print(f'  Admit: {r.AdmitDateTime}')
                print(f'  Discharge: {r.DischargeDateTime}')
        else:
            print('❌ InpatientSID NOT found in Inpat.Inpatient table')

except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
finally:
    cursor.close()
    conn.close()
