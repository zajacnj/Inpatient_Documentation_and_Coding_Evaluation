"""
Validate database schema against expected queries.
This script checks which columns actually exist in the production database.
"""

import pyodbc
import json
import sys

def load_database_config():
    """Load database config from JSON file."""
    with open("config/database_config.json", "r") as f:
        return json.load(f)

def get_columns(cursor, schema, table):
    """Get all columns for a table."""
    query = """
    SELECT COLUMN_NAME
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
    ORDER BY ORDINAL_POSITION
    """
    cursor.execute(query, (schema, table))
    return [row[0] for row in cursor.fetchall()]

def validate_schema():
    """Validate all required tables and columns."""
    db_config = load_database_config()
    lsv_config = db_config.get("databases", {}).get("LSV", {})
    
    conn_str = (
        f"Driver={{ODBC Driver 17 for SQL Server}};"
        f"Server={lsv_config.get('server')};"
        f"Database={lsv_config.get('database')};"
        f"Trusted_Connection=yes;"
    )
    
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        print("=" * 80)
        print("DATABASE SCHEMA VALIDATION")
        print("=" * 80)
        
        # Define tables and their expected columns
        tables_to_check = {
            ("TIU", "TIUDocument"): [
                "TIUDocumentSID", "PatientSID", "InpatientSID", "Sta3n",
                "TIUDocumentDefinitionSID", "ReferenceDateTime", "SignedByStaffSID",
                "CosignedByStaffSID", "SignatureDateTime"
            ],
            ("Dim", "TIUDocumentDefinition"): [
                "TIUDocumentDefinitionSID", "TIUDocumentDefinitionPrintName"
            ],
            ("STIUNotes", "TIUDocument_8925"): [
                "TIUDocumentSID", "ReportText"
            ],
            ("Vital", "VitalSign"): [
                "VitalSignSID", "PatientSID", "Sta3n", "VitalSignTakenDateTime",
                "VitalEnteredDateTime", "VitalTypeSID", "VitalResult", "VitalResultNumeric"
            ],
            ("Dim", "VitalType"): [
                "VitalTypeSID", "VitalTypeName"
            ],
            ("Chem", "LabChem"): [
                "LabChemSID", "PatientSID", "Sta3n", "CollectionDateTime",
                "ResultDateTime", "LabChemTestSID", "LabChemResultValue",
                "LabChemResultNumericValue", "ResultUnits", "LOINCSID", "LabChemResultFlag"
            ],
            ("Dim", "LabChemTest"): [
                "LabChemTestSID", "LabChemTestName"
            ],
            ("Inpat", "InpatientDischargeDiagnosis"): [
                "InpatientDischargeDiagnosisSID", "InpatientSID", "PTFIEN", "OrdinalNumber",
                "ICD10SID", "ICD9SID", "DiagnosisText", "PresentOnAdmissionIndicator", "Sta3n"
            ],
            ("Inpat", "Inpatient"): [
                "InpatientSID", "PatientSID", "Sta3n", "AdmitDateTime", "DischargeDateTime"
            ]
        }
        
        all_valid = True
        validation_results = {}
        
        for (schema, table), expected_cols in tables_to_check.items():
            print(f"\n[{schema}.{table}]")
            try:
                actual_cols = get_columns(cursor, schema, table)
                actual_cols_set = set(actual_cols)
                expected_cols_set = set(expected_cols)
                
                missing = expected_cols_set - actual_cols_set
                extra = actual_cols_set - expected_cols_set
                
                validation_results[f"{schema}.{table}"] = {
                    "expected": expected_cols,
                    "actual": actual_cols,
                    "missing": list(missing),
                    "extra": list(extra)
                }
                
                if missing:
                    print(f"  ❌ MISSING COLUMNS: {', '.join(sorted(missing))}")
                    all_valid = False
                else:
                    print(f"  ✓ All expected columns present")
                
                if extra:
                    print(f"  ℹ Additional columns: {', '.join(sorted(extra)[:5])}{'...' if len(extra) > 5 else ''}")
                    
            except Exception as e:
                print(f"  ❌ ERROR: {e}")
                all_valid = False
                validation_results[f"{schema}.{table}"] = {"error": str(e)}
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 80)
        if all_valid:
            print("✓ SCHEMA VALIDATION PASSED - All tables and columns present")
        else:
            print("❌ SCHEMA VALIDATION FAILED - Some tables or columns are missing")
        print("=" * 80)
        
        # Save results
        with open("schema_validation_results.json", "w") as f:
            json.dump(validation_results, f, indent=2)
        print("\nDetailed results saved to: schema_validation_results.json")
        
        return all_valid
        
    except Exception as e:
        print(f"ERROR: Failed to connect to database: {e}")
        return False

if __name__ == "__main__":
    validate_schema()
