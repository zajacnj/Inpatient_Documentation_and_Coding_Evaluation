"""Find ICD-related tables"""
import pyodbc
from app.database.connection import load_database_config

db_config = load_database_config()
server = db_config['databases']['LSV']['server']
database = db_config['databases']['LSV']['database']

conn_str = f'DRIVER={{SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;'
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

# Search for ICD-related tables
cursor.execute("""
SELECT TABLE_SCHEMA, TABLE_NAME 
FROM INFORMATION_SCHEMA.TABLES 
WHERE (TABLE_NAME LIKE '%ICD%' OR TABLE_NAME LIKE '%Diagnosis%')
  AND TABLE_TYPE = 'BASE TABLE'
ORDER BY TABLE_SCHEMA, TABLE_NAME
""")

print('\n=== ICD and Diagnosis Related Tables ===\n')
for row in cursor.fetchall():
    print(f'{row.TABLE_SCHEMA}.{row.TABLE_NAME}')

conn.close()
