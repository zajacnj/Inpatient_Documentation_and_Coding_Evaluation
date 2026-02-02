"""
LSV Schema Explorer for Inpatient Documentation Project

This script explores the LSV database schema to find tables relevant to:
1. Inpatient admissions and discharges (PTF)
2. TIU clinical notes
3. Vital signs
4. Laboratory values
5. Diagnoses (ICD-10 codes)

Run this script when connected to the VA network to identify the correct tables.

Usage:
    python tools/explore_schema.py

Output:
    - Console output with found tables
    - schema_exploration_results.json in the data/ directory
"""

import pyodbc
import json
import os
from datetime import datetime
from pathlib import Path

# Configuration
SERVER = "vhacdwdwhsql33.vha.med.va.gov"
DATABASE = "LSV"
OUTPUT_DIR = Path(__file__).parent.parent / "data"
OUTPUT_FILE = OUTPUT_DIR / "schema_exploration_results.json"

# Search terms for each category
SEARCH_CATEGORIES = {
    "inpatient_discharge": {
        "description": "Inpatient admissions, discharges, and PTF data",
        "table_keywords": ["inpat", "admission", "discharge", "ptf", "transfer", "census"],
        "schema_keywords": ["inpat", "patient"],
        "column_keywords": ["admit", "discharge", "los", "lengthofstay", "ptf"]
    },
    "tiu_notes": {
        "description": "TIU clinical documentation/notes",
        "table_keywords": ["tiu", "note", "document", "progress", "admission"],
        "schema_keywords": ["tiu"],
        "column_keywords": ["notetext", "reporttext", "documenttext", "tiudocument"]
    },
    "vital_signs": {
        "description": "Vital signs measurements",
        "table_keywords": ["vital", "sign", "measurement", "observation"],
        "schema_keywords": ["vital"],
        "column_keywords": ["pulse", "temperature", "bloodpressure", "respiration", "weight", "height", "bmi", "pain"]
    },
    "laboratory": {
        "description": "Laboratory test results",
        "table_keywords": ["lab", "chem", "hematology", "micro", "pathology", "loinc"],
        "schema_keywords": ["chem", "lab", "micro", "patho"],
        "column_keywords": ["labchemtest", "result", "specimen", "loinc"]
    },
    "diagnoses": {
        "description": "ICD-10 diagnosis codes",
        "table_keywords": ["diagnosis", "icd", "dx", "problem"],
        "schema_keywords": ["inpat", "outpat", "dim"],
        "column_keywords": ["icd10", "icd9", "diagnosis", "principaldiagnosis", "admittingdiagnosis"]
    }
}


def connect_to_database():
    """Connect to LSV database using Windows authentication."""
    connection_string = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        f"Trusted_Connection=yes;"
        f"timeout=60"
    )

    print(f"Connecting to {SERVER}/{DATABASE}...")
    try:
        conn = pyodbc.connect(connection_string)
        print("Connected successfully!")
        return conn
    except pyodbc.Error as e:
        print(f"Connection failed: {e}")
        return None


def get_all_tables(conn):
    """Get all tables and views from the database."""
    query = """
    SELECT
        TABLE_SCHEMA,
        TABLE_NAME,
        TABLE_TYPE
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_TYPE IN ('BASE TABLE', 'VIEW')
    ORDER BY TABLE_SCHEMA, TABLE_NAME
    """

    cursor = conn.cursor()
    cursor.execute(query)

    tables = []
    for row in cursor.fetchall():
        tables.append({
            "schema": row.TABLE_SCHEMA,
            "name": row.TABLE_NAME,
            "type": row.TABLE_TYPE,
            "full_name": f"{row.TABLE_SCHEMA}.{row.TABLE_NAME}"
        })

    cursor.close()
    return tables


def get_table_columns(conn, schema_name, table_name):
    """Get columns for a specific table."""
    query = """
    SELECT
        COLUMN_NAME,
        DATA_TYPE,
        IS_NULLABLE,
        CHARACTER_MAXIMUM_LENGTH
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
    ORDER BY ORDINAL_POSITION
    """

    cursor = conn.cursor()
    cursor.execute(query, (schema_name, table_name))

    columns = []
    for row in cursor.fetchall():
        columns.append({
            "name": row.COLUMN_NAME,
            "data_type": row.DATA_TYPE,
            "nullable": row.IS_NULLABLE,
            "max_length": row.CHARACTER_MAXIMUM_LENGTH
        })

    cursor.close()
    return columns


def get_table_row_count(conn, schema_name, table_name, sample_limit=1):
    """Get approximate row count and sample data existence."""
    try:
        query = f"SELECT TOP {sample_limit} 1 FROM [{schema_name}].[{table_name}]"
        cursor = conn.cursor()
        cursor.execute(query)
        has_data = cursor.fetchone() is not None
        cursor.close()
        return has_data
    except:
        return None


def search_tables_by_category(tables, category_config):
    """Search tables matching category keywords."""
    matches = []

    for table in tables:
        score = 0
        match_reasons = []

        table_lower = table["name"].lower()
        schema_lower = table["schema"].lower()

        # Check table name keywords
        for keyword in category_config["table_keywords"]:
            if keyword in table_lower:
                score += 2
                match_reasons.append(f"table name contains '{keyword}'")

        # Check schema keywords
        for keyword in category_config["schema_keywords"]:
            if keyword in schema_lower:
                score += 1
                match_reasons.append(f"schema contains '{keyword}'")

        if score > 0:
            matches.append({
                "table": table,
                "score": score,
                "reasons": match_reasons
            })

    # Sort by score descending
    matches.sort(key=lambda x: x["score"], reverse=True)
    return matches


def explore_top_matches(conn, matches, category_config, max_tables=10):
    """Get detailed info for top matching tables."""
    detailed_matches = []

    for match in matches[:max_tables]:
        table = match["table"]
        columns = get_table_columns(conn, table["schema"], table["name"])

        # Check if columns match expected keywords
        column_matches = []
        for col in columns:
            col_lower = col["name"].lower()
            for keyword in category_config["column_keywords"]:
                if keyword in col_lower:
                    column_matches.append(col["name"])
                    break

        # Check for data
        has_data = get_table_row_count(conn, table["schema"], table["name"])

        detailed_matches.append({
            "full_name": table["full_name"],
            "schema": table["schema"],
            "name": table["name"],
            "type": table["type"],
            "score": match["score"],
            "match_reasons": match["reasons"],
            "column_count": len(columns),
            "columns": columns[:30],  # First 30 columns
            "matching_columns": column_matches,
            "has_data": has_data
        })

    return detailed_matches


def find_specific_tables(conn):
    """Search for specific commonly-used VA tables."""
    specific_searches = [
        # Inpatient
        ("Inpat", "Inpatient", "Main inpatient admission table"),
        ("Inpat", "InpatientDiagnosis", "Inpatient diagnoses"),
        ("Inpat", "InpatientProcedure", "Inpatient procedures"),
        ("Inpat", "DailyCensus", "Daily inpatient census"),
        ("Inpat", "SpecialtyTransfer", "Specialty transfers"),
        ("Inpat", "PatientTransfer", "Patient transfers"),

        # TIU Notes
        ("TIU", "TIUDocument", "TIU documents"),
        ("TIU", "TIUDocumentDefinition", "TIU document types"),
        ("TIU", "TIUNote", "TIU notes"),

        # Vitals
        ("Vital", "VitalSign", "Vital signs"),
        ("Vital", "VitalType", "Vital types"),

        # Labs
        ("Chem", "LabChem", "Lab chemistry results"),
        ("Chem", "PatientLabChem", "Patient lab chemistry"),
        ("Micro", "Microbiology", "Microbiology results"),

        # Diagnoses
        ("Dim", "ICD10", "ICD-10 dimension table"),
        ("Dim", "ICD10Diagnosis", "ICD-10 diagnoses"),
        ("Outpat", "VDiagnosis", "Outpatient diagnoses"),
        ("Outpat", "WorkloadVDiagnosis", "Workload diagnoses"),

        # Patient
        ("SPatient", "SPatient", "Spatient table"),
        ("Patient", "Patient", "Patient demographics"),
    ]

    results = []

    for schema, table, description in specific_searches:
        query = """
        SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_NAME LIKE ?
        ORDER BY TABLE_SCHEMA, TABLE_NAME
        """

        cursor = conn.cursor()
        cursor.execute(query, (f"%{table}%",))

        matches = []
        for row in cursor.fetchall():
            matches.append({
                "schema": row.TABLE_SCHEMA,
                "name": row.TABLE_NAME,
                "type": row.TABLE_TYPE,
                "full_name": f"{row.TABLE_SCHEMA}.{row.TABLE_NAME}"
            })

        cursor.close()

        if matches:
            results.append({
                "search_term": f"{schema}.{table}",
                "description": description,
                "matches": matches
            })

    return results


def search_columns_across_tables(conn, column_keywords):
    """Search for specific column names across all tables."""
    results = {}

    for keyword in column_keywords:
        query = """
        SELECT
            TABLE_SCHEMA,
            TABLE_NAME,
            COLUMN_NAME,
            DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE COLUMN_NAME LIKE ?
        ORDER BY TABLE_SCHEMA, TABLE_NAME
        """

        cursor = conn.cursor()
        cursor.execute(query, (f"%{keyword}%",))

        matches = []
        for row in cursor.fetchall():
            matches.append({
                "full_name": f"{row.TABLE_SCHEMA}.{row.TABLE_NAME}",
                "column": row.COLUMN_NAME,
                "data_type": row.DATA_TYPE
            })

        cursor.close()

        if matches:
            results[keyword] = matches[:20]  # Top 20 matches

    return results


def main():
    """Main exploration function."""
    print("=" * 70)
    print("LSV Schema Explorer for Inpatient Documentation Project")
    print("=" * 70)
    print()

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Connect to database
    conn = connect_to_database()
    if not conn:
        print("\nCannot proceed without database connection.")
        print("Make sure you are connected to the VA network.")
        return

    results = {
        "exploration_date": datetime.now().isoformat(),
        "server": SERVER,
        "database": DATABASE,
        "categories": {},
        "specific_tables": [],
        "column_searches": {},
        "recommendations": {}
    }

    try:
        # Get all tables
        print("\nFetching all tables and views...")
        all_tables = get_all_tables(conn)
        print(f"Found {len(all_tables)} tables/views")
        results["total_tables"] = len(all_tables)

        # Search by category
        print("\n" + "=" * 70)
        print("SEARCHING BY CATEGORY")
        print("=" * 70)

        for category_name, category_config in SEARCH_CATEGORIES.items():
            print(f"\n--- {category_name.upper()}: {category_config['description']} ---")

            # Find matching tables
            matches = search_tables_by_category(all_tables, category_config)
            print(f"Found {len(matches)} potential matches")

            # Get detailed info for top matches
            if matches:
                detailed = explore_top_matches(conn, matches, category_config)
                results["categories"][category_name] = {
                    "description": category_config["description"],
                    "total_matches": len(matches),
                    "top_tables": detailed
                }

                # Print top 5
                print("Top 5 matches:")
                for i, table in enumerate(detailed[:5], 1):
                    data_status = "HAS DATA" if table["has_data"] else "NO DATA/ERROR"
                    print(f"  {i}. {table['full_name']} ({table['type']}) - {data_status}")
                    print(f"     Columns: {table['column_count']}, Matching cols: {table['matching_columns'][:5]}")

        # Search for specific known tables
        print("\n" + "=" * 70)
        print("SEARCHING FOR SPECIFIC VA TABLES")
        print("=" * 70)

        specific_results = find_specific_tables(conn)
        results["specific_tables"] = specific_results

        for search in specific_results:
            print(f"\n{search['description']} ({search['search_term']}):")
            for match in search["matches"][:3]:
                print(f"  - {match['full_name']} ({match['type']})")

        # Search for key columns
        print("\n" + "=" * 70)
        print("SEARCHING FOR KEY COLUMNS")
        print("=" * 70)

        key_columns = [
            "DischargeDateTime", "AdmitDateTime", "PatientICN", "PatientSID",
            "TIUDocumentSID", "ReportText", "NoteText",
            "VitalSignSID", "VitalResultNumeric",
            "LabChemSID", "LabChemResultValue",
            "ICD10Code", "ICD10SID", "DiagnosisSID"
        ]

        column_results = search_columns_across_tables(conn, key_columns)
        results["column_searches"] = column_results

        for col_name, matches in column_results.items():
            print(f"\n{col_name}: Found in {len(matches)} tables")
            for match in matches[:3]:
                print(f"  - {match['full_name']}.{match['column']}")

        # Generate recommendations
        print("\n" + "=" * 70)
        print("RECOMMENDATIONS")
        print("=" * 70)

        recommendations = generate_recommendations(results)
        results["recommendations"] = recommendations

        for category, rec in recommendations.items():
            print(f"\n{category}:")
            print(f"  Primary: {rec.get('primary', 'Not found')}")
            if rec.get('alternatives'):
                print(f"  Alternatives: {', '.join(rec['alternatives'][:3])}")

        # Save results
        print("\n" + "=" * 70)
        print(f"Saving results to {OUTPUT_FILE}")

        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str)

        print("Done!")

    except Exception as e:
        print(f"\nError during exploration: {e}")
        import traceback
        traceback.print_exc()

    finally:
        conn.close()
        print("\nConnection closed.")


def generate_recommendations(results):
    """Generate table recommendations based on exploration results."""
    recommendations = {}

    # Inpatient/Discharge
    inpat_tables = results["categories"].get("inpatient_discharge", {}).get("top_tables", [])
    inpat_with_data = [t for t in inpat_tables if t.get("has_data")]
    if inpat_with_data:
        # Prefer tables with "Inpatient" in name
        primary = next((t for t in inpat_with_data if "inpatient" in t["name"].lower() and "diagnosis" not in t["name"].lower()), inpat_with_data[0])
        recommendations["inpatient_discharge"] = {
            "primary": primary["full_name"],
            "alternatives": [t["full_name"] for t in inpat_with_data if t != primary][:5]
        }

    # TIU Notes
    tiu_tables = results["categories"].get("tiu_notes", {}).get("top_tables", [])
    tiu_with_data = [t for t in tiu_tables if t.get("has_data")]
    if tiu_with_data:
        primary = next((t for t in tiu_with_data if "document" in t["name"].lower()), tiu_with_data[0])
        recommendations["tiu_notes"] = {
            "primary": primary["full_name"],
            "alternatives": [t["full_name"] for t in tiu_with_data if t != primary][:5]
        }

    # Vital Signs
    vital_tables = results["categories"].get("vital_signs", {}).get("top_tables", [])
    vital_with_data = [t for t in vital_tables if t.get("has_data")]
    if vital_with_data:
        primary = vital_with_data[0]
        recommendations["vital_signs"] = {
            "primary": primary["full_name"],
            "alternatives": [t["full_name"] for t in vital_with_data if t != primary][:5]
        }

    # Laboratory
    lab_tables = results["categories"].get("laboratory", {}).get("top_tables", [])
    lab_with_data = [t for t in lab_tables if t.get("has_data")]
    if lab_with_data:
        primary = next((t for t in lab_with_data if "chem" in t["name"].lower()), lab_with_data[0])
        recommendations["laboratory"] = {
            "primary": primary["full_name"],
            "alternatives": [t["full_name"] for t in lab_with_data if t != primary][:5]
        }

    # Diagnoses
    dx_tables = results["categories"].get("diagnoses", {}).get("top_tables", [])
    dx_with_data = [t for t in dx_tables if t.get("has_data")]
    if dx_with_data:
        # Prefer inpatient diagnosis tables
        primary = next((t for t in dx_with_data if "inpat" in t["schema"].lower() and "diagnosis" in t["name"].lower()), dx_with_data[0])
        recommendations["diagnoses"] = {
            "primary": primary["full_name"],
            "alternatives": [t["full_name"] for t in dx_with_data if t != primary][:5]
        }

    return recommendations


if __name__ == "__main__":
    main()
