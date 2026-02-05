"""Get column names from InpatientDischargeDiagnosis table"""
import pyodbc
from app.database.connection import load_database_config

db_config = load_database_config()
server = db_config['databases']['LSV']['server']
database = db_config['databases']['LSV']['database']

conn_str = f'DRIVER={{SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;'
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

# Get column names
cursor.execute("""
SELECT COLUMN_NAME, DATA_TYPE 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = 'Inpat' AND TABLE_NAME = 'InpatientDischargeDiagnosis'
ORDER BY ORDINAL_POSITION
""")

print('\n=== Columns in Inpat.InpatientDischargeDiagnosis ===\n')
for row in cursor.fetchall():
    print(f'{row.COLUMN_NAME:<40} {row.DATA_TYPE}')

conn.close()
