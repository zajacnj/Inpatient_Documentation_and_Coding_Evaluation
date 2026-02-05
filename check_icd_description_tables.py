"""Check ICD10DiagnosisVersion and ICD10DescriptionVersion tables"""
import pyodbc
from app.database.connection import load_database_config

db_config = load_database_config()
server = db_config['databases']['LSV']['server']
database = db_config['databases']['LSV']['database']

conn_str = f'DRIVER={{SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;'
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

# Check ICD10DiagnosisVersion
print('\n=== Checking Dim.ICD10DiagnosisVersion ===')
try:
    cursor.execute("""
    SELECT COLUMN_NAME, DATA_TYPE 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = 'Dim' AND TABLE_NAME = 'ICD10DiagnosisVersion'
    ORDER BY ORDINAL_POSITION
    """)
    
    columns = cursor.fetchall()
    if columns:
        print(f'\n✓ Table exists with {len(columns)} columns:\n')
        for row in columns:
            print(f'  {row.COLUMN_NAME:<40} {row.DATA_TYPE}')
        
        # Get sample data
        cursor.execute("SELECT TOP 5 * FROM [CDWWork].[Dim].[ICD10DiagnosisVersion]")
        print('\nSample rows:')
        for row in cursor.fetchall():
            print(f'  {row}')
    else:
        print('❌ Table not found')
except Exception as e:
    print(f'❌ Error: {e}')

# Check ICD10DescriptionVersion
print('\n=== Checking Dim.ICD10DescriptionVersion ===')
try:
    cursor.execute("""
    SELECT COLUMN_NAME, DATA_TYPE 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = 'Dim' AND TABLE_NAME = 'ICD10DescriptionVersion'
    ORDER BY ORDINAL_POSITION
    """)
    
    columns = cursor.fetchall()
    if columns:
        print(f'\n✓ Table exists with {len(columns)} columns:\n')
        for row in columns:
            print(f'  {row.COLUMN_NAME:<40} {row.DATA_TYPE}')
        
        # Get sample data
        cursor.execute("SELECT TOP 5 * FROM [CDWWork].[Dim].[ICD10DescriptionVersion]")
        print('\nSample rows:')
        for row in cursor.fetchall():
            print(f'  {row}')
    else:
        print('❌ Table not found')
except Exception as e:
    print(f'❌ Error: {e}')

# Try to join with our diagnoses to see if we can get descriptions
print('\n=== Testing JOIN with InpatientDischargeDiagnosis ===')
try:
    query = """
    SELECT TOP 5
        d.OrdinalNumber,
        icd10.ICD10Code,
        diag_ver.ICD10Diagnosis,
        desc_ver.ICD10Description
    FROM [CDWWork].[Inpat].[InpatientDischargeDiagnosis] d
    LEFT JOIN [CDWWork].[Dim].[ICD10] icd10 ON d.ICD10SID = icd10.ICD10SID
    LEFT JOIN [CDWWork].[Dim].[ICD10DiagnosisVersion] diag_ver ON d.ICD10SID = diag_ver.ICD10SID
    LEFT JOIN [CDWWork].[Dim].[ICD10DescriptionVersion] desc_ver ON d.ICD10SID = desc_ver.ICD10SID
    WHERE d.InpatientSID = 1600004711061
    ORDER BY d.OrdinalNumber
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    
    print(f'\nFound {len(rows)} diagnoses with descriptions:\n')
    print(f'{"Code":<12} {"Diagnosis":<50} {"Description":<50}')
    print('-' * 115)
    
    for row in rows:
        code = row[1] if row[1] else 'NULL'
        diagnosis = (row[2][:47] + '...') if row[2] and len(str(row[2])) > 50 else (row[2] if row[2] else 'NULL')
        description = (row[3][:47] + '...') if row[3] and len(str(row[3])) > 50 else (row[3] if row[3] else 'NULL')
        print(f'{code:<12} {str(diagnosis):<50} {str(description):<50}')
        
except Exception as e:
    print(f'❌ Error: {e}')

cursor.close()
conn.close()
