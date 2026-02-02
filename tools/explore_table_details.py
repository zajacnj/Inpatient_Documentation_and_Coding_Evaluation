"""
Table Details Explorer for Inpatient Documentation Project

This script provides detailed information about specific tables including:
- All columns with data types
- Sample data (first 5 rows)
- Row counts
- Key relationships

Usage:
    python tools/explore_table_details.py "Schema.TableName"
    python tools/explore_table_details.py "Inpat.Inpatient"
    python tools/explore_table_details.py --all-recommended

This helps you understand the structure and content of tables
identified by the schema explorer.
"""

import pyodbc
import json
import sys
from datetime import datetime
from pathlib import Path

# Configuration
SERVER = "vhacdwdwhsql33.vha.med.va.gov"
DATABASE = "LSV"
OUTPUT_DIR = Path(__file__).parent.parent / "data"

# Tables to explore in detail (based on common VA CDW tables)
RECOMMENDED_TABLES = [
    # Inpatient
    ("Inpat", "Inpatient", "Main inpatient admission/discharge table"),
    ("Inpat", "InpatientDiagnosis", "Inpatient ICD-10 diagnoses"),
    ("Inpat", "InpatientProcedure", "Inpatient procedures"),

    # TIU Notes
    ("TIU", "TIUDocument", "TIU clinical documents"),
    ("TIU", "TIUDocument_8925", "TIU document text"),

    # Vitals
    ("Vital", "VitalSign", "Vital sign measurements"),

    # Labs
    ("Chem", "PatientLabChem", "Patient lab chemistry results"),

    # Patient
    ("SPatient", "SPatient", "Patient demographics"),

    # Dimensions
    ("Dim", "ICD10", "ICD-10 code dimension"),
    ("Dim", "TreatingSpecialty", "Treating specialty dimension"),
]


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


def get_table_columns(conn, schema_name, table_name):
    """Get all columns for a table with detailed info."""
    query = """
    SELECT
        c.COLUMN_NAME,
        c.DATA_TYPE,
        c.CHARACTER_MAXIMUM_LENGTH,
        c.NUMERIC_PRECISION,
        c.NUMERIC_SCALE,
        c.IS_NULLABLE,
        c.COLUMN_DEFAULT,
        CASE WHEN pk.COLUMN_NAME IS NOT NULL THEN 'YES' ELSE 'NO' END as IS_PRIMARY_KEY
    FROM INFORMATION_SCHEMA.COLUMNS c
    LEFT JOIN (
        SELECT ku.TABLE_SCHEMA, ku.TABLE_NAME, ku.COLUMN_NAME
        FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
        JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE ku
            ON tc.CONSTRAINT_NAME = ku.CONSTRAINT_NAME
        WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
    ) pk ON c.TABLE_SCHEMA = pk.TABLE_SCHEMA
        AND c.TABLE_NAME = pk.TABLE_NAME
        AND c.COLUMN_NAME = pk.COLUMN_NAME
    WHERE c.TABLE_SCHEMA = ? AND c.TABLE_NAME = ?
    ORDER BY c.ORDINAL_POSITION
    """

    cursor = conn.cursor()
    cursor.execute(query, (schema_name, table_name))

    columns = []
    for row in cursor.fetchall():
        col = {
            "name": row.COLUMN_NAME,
            "data_type": row.DATA_TYPE,
            "max_length": row.CHARACTER_MAXIMUM_LENGTH,
            "precision": row.NUMERIC_PRECISION,
            "scale": row.NUMERIC_SCALE,
            "nullable": row.IS_NULLABLE,
            "default": str(row.COLUMN_DEFAULT) if row.COLUMN_DEFAULT else None,
            "is_primary_key": row.IS_PRIMARY_KEY == 'YES'
        }
        columns.append(col)

    cursor.close()
    return columns


def get_row_count(conn, schema_name, table_name):
    """Get row count for a table."""
    try:
        query = f"SELECT COUNT(*) FROM [{schema_name}].[{table_name}]"
        cursor = conn.cursor()
        cursor.execute(query)
        count = cursor.fetchone()[0]
        cursor.close()
        return count
    except Exception as e:
        print(f"  Error getting row count: {e}")
        return None


def get_sample_data(conn, schema_name, table_name, limit=5):
    """Get sample rows from a table."""
    try:
        query = f"SELECT TOP {limit} * FROM [{schema_name}].[{table_name}]"
        cursor = conn.cursor()
        cursor.execute(query)

        columns = [desc[0] for desc in cursor.description]
        rows = []

        for row in cursor.fetchall():
            row_dict = {}
            for i, col in enumerate(columns):
                val = row[i]
                # Convert non-serializable types to strings
                if val is not None and not isinstance(val, (str, int, float, bool)):
                    val = str(val)
                # Truncate long strings
                if isinstance(val, str) and len(val) > 200:
                    val = val[:200] + "..."
                row_dict[col] = val
            rows.append(row_dict)

        cursor.close()
        return {"columns": columns, "rows": rows}
    except Exception as e:
        print(f"  Error getting sample data: {e}")
        return None


def get_key_columns_for_station(conn, schema_name, table_name):
    """Check if table has Sta3n column for station filtering."""
    columns = get_table_columns(conn, schema_name, table_name)
    col_names = [c["name"].lower() for c in columns]

    station_columns = []
    if "sta3n" in col_names:
        station_columns.append("Sta3n")
    if "stationno" in col_names:
        station_columns.append("StationNo")

    return station_columns


def get_date_columns(conn, schema_name, table_name):
    """Find date/datetime columns in a table."""
    columns = get_table_columns(conn, schema_name, table_name)
    date_cols = [c["name"] for c in columns if c["data_type"] in ("date", "datetime", "datetime2", "smalldatetime")]
    return date_cols


def get_foreign_key_relationships(conn, schema_name, table_name):
    """Get foreign key relationships for a table."""
    query = """
    SELECT
        fk.name AS FK_Name,
        tp.name AS Parent_Table,
        cp.name AS Parent_Column,
        tr.name AS Referenced_Table,
        cr.name AS Referenced_Column
    FROM sys.foreign_keys fk
    JOIN sys.tables tp ON fk.parent_object_id = tp.object_id
    JOIN sys.schemas sp ON tp.schema_id = sp.schema_id
    JOIN sys.tables tr ON fk.referenced_object_id = tr.object_id
    JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
    JOIN sys.columns cp ON fkc.parent_column_id = cp.column_id AND fkc.parent_object_id = cp.object_id
    JOIN sys.columns cr ON fkc.referenced_column_id = cr.column_id AND fkc.referenced_object_id = cr.object_id
    WHERE sp.name = ? AND tp.name = ?
    """

    cursor = conn.cursor()
    try:
        cursor.execute(query, (schema_name, table_name))
        relationships = []
        for row in cursor.fetchall():
            relationships.append({
                "fk_name": row.FK_Name,
                "parent_table": row.Parent_Table,
                "parent_column": row.Parent_Column,
                "referenced_table": row.Referenced_Table,
                "referenced_column": row.Referenced_Column
            })
        return relationships
    except:
        return []
    finally:
        cursor.close()


def explore_table(conn, schema_name, table_name, description=""):
    """Get comprehensive details about a table."""
    print(f"\n{'='*70}")
    print(f"TABLE: [{schema_name}].[{table_name}]")
    if description:
        print(f"Description: {description}")
    print("="*70)

    result = {
        "schema": schema_name,
        "name": table_name,
        "full_name": f"{schema_name}.{table_name}",
        "description": description,
        "explored_at": datetime.now().isoformat()
    }

    # Check if table exists
    try:
        check_query = """
        SELECT TABLE_TYPE FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
        """
        cursor = conn.cursor()
        cursor.execute(check_query, (schema_name, table_name))
        row = cursor.fetchone()
        cursor.close()

        if not row:
            print(f"  TABLE NOT FOUND!")
            result["exists"] = False
            return result

        result["exists"] = True
        result["type"] = row.TABLE_TYPE
        print(f"Type: {row.TABLE_TYPE}")

    except Exception as e:
        print(f"  Error checking table: {e}")
        result["exists"] = False
        return result

    # Get columns
    print("\nColumns:")
    columns = get_table_columns(conn, schema_name, table_name)
    result["columns"] = columns
    result["column_count"] = len(columns)

    for col in columns:
        pk_marker = " [PK]" if col["is_primary_key"] else ""
        null_marker = " NULL" if col["nullable"] == "YES" else " NOT NULL"
        type_info = col["data_type"]
        if col["max_length"]:
            type_info += f"({col['max_length']})"
        elif col["precision"]:
            type_info += f"({col['precision']},{col['scale']})"

        print(f"  {col['name']}: {type_info}{null_marker}{pk_marker}")

    # Get row count
    print("\nRow Count:")
    row_count = get_row_count(conn, schema_name, table_name)
    result["row_count"] = row_count
    print(f"  {row_count:,}" if row_count else "  Unable to determine")

    # Station filter columns
    station_cols = get_key_columns_for_station(conn, schema_name, table_name)
    result["station_columns"] = station_cols
    if station_cols:
        print(f"\nStation Filter Column(s): {', '.join(station_cols)}")

    # Date columns
    date_cols = get_date_columns(conn, schema_name, table_name)
    result["date_columns"] = date_cols
    if date_cols:
        print(f"\nDate Columns: {', '.join(date_cols)}")

    # Foreign keys
    fks = get_foreign_key_relationships(conn, schema_name, table_name)
    result["foreign_keys"] = fks
    if fks:
        print(f"\nForeign Keys:")
        for fk in fks:
            print(f"  {fk['parent_column']} -> {fk['referenced_table']}.{fk['referenced_column']}")

    # Sample data
    print("\nSample Data (first 5 rows):")
    sample = get_sample_data(conn, schema_name, table_name)
    result["sample_data"] = sample
    if sample and sample["rows"]:
        for i, row in enumerate(sample["rows"], 1):
            print(f"\n  Row {i}:")
            for key, val in list(row.items())[:10]:  # First 10 columns
                print(f"    {key}: {val}")
            if len(row) > 10:
                print(f"    ... and {len(row) - 10} more columns")
    else:
        print("  No sample data available")

    return result


def main():
    """Main function."""
    print("="*70)
    print("Table Details Explorer - Inpatient Documentation Project")
    print("="*70)

    # Parse arguments
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python tools/explore_table_details.py Schema.TableName")
        print("  python tools/explore_table_details.py --all-recommended")
        print("\nExamples:")
        print("  python tools/explore_table_details.py Inpat.Inpatient")
        print("  python tools/explore_table_details.py TIU.TIUDocument")
        print("  python tools/explore_table_details.py --all-recommended")
        return

    explore_all = sys.argv[1] == "--all-recommended"
    tables_to_explore = []

    if explore_all:
        tables_to_explore = [(s, t, d) for s, t, d in RECOMMENDED_TABLES]
    else:
        # Parse table name from argument
        table_arg = sys.argv[1]
        if "." in table_arg:
            schema, table = table_arg.split(".", 1)
            tables_to_explore = [(schema, table, "")]
        else:
            print(f"Invalid table format: {table_arg}")
            print("Use format: Schema.TableName")
            return

    # Ensure output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Connect
    conn = connect_to_database()
    if not conn:
        print("\nCannot proceed without database connection.")
        return

    results = {
        "exploration_date": datetime.now().isoformat(),
        "server": SERVER,
        "database": DATABASE,
        "tables": []
    }

    try:
        for schema, table, description in tables_to_explore:
            table_result = explore_table(conn, schema, table, description)
            results["tables"].append(table_result)

        # Save results
        output_file = OUTPUT_DIR / "table_details_results.json"
        print(f"\n{'='*70}")
        print(f"Saving results to {output_file}")

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str)

        print("Done!")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

    finally:
        conn.close()
        print("\nConnection closed.")


if __name__ == "__main__":
    main()
