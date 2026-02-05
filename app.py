"""
Inpatient Documentation and Coding Evaluation
Main FastAPI Application

AI-powered evaluation of inpatient clinical documentation against coded diagnoses.
"""

import json
import logging
import os
import threading
import getpass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import time
import pandas as pd

# Load environment variables
from dotenv import load_dotenv
project_root = Path(__file__).parent
env_file = project_root / 'Key.env'
if env_file.exists():
    load_dotenv(env_file)

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pydantic import BaseModel

# Local imports
from app.database.connection import DatabaseConnection, load_database_config
from app.ai.va_gpt_client import VAGPTClient
from app.logging.audit_logger import AuditLogger
from app.logging.query_logger import QueryLogger
from app.utils.specialty_mapping import map_specialty_display

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title="Inpatient Documentation and Coding Evaluation",
    description="AI-powered evaluation of inpatient clinical documentation against coded diagnoses",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and templates
static_dir = project_root / "static"
templates_dir = project_root / "templates"
static_dir.mkdir(exist_ok=True)
templates_dir.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
templates = Jinja2Templates(directory=str(templates_dir))

# Initialize components
db_config = load_database_config()
logger.info(f"Database config loaded: {json.dumps(db_config, indent=2)[:500]}...")
audit_logger = AuditLogger(log_dir="logs")
query_logger = QueryLogger(log_dir="logs")
va_gpt_client = VAGPTClient()

# Global database connection (will be initialized on first use)
db_connection: Optional[DatabaseConnection] = None

# Progress tracking for long-running review operations
review_progress: Dict[str, Dict[str, Any]] = {}

def create_progress_tracker(review_id: str) -> None:
    """Initialize progress tracking for a review"""
    review_progress[review_id] = {
        "status": "initializing",
        "percentage": 0,
        "current_step": "Initializing review...",
        "steps_completed": [],
        "start_time": datetime.now().isoformat(),
        "error": None
    }

def update_progress(review_id: str, percentage: int, current_step: str, status: str = "processing") -> None:
    """Update progress for a review"""
    if review_id in review_progress:
        review_progress[review_id].update({
            "percentage": min(percentage, 99),  # Cap at 99% until complete
            "current_step": current_step,
            "status": status,
            "last_update": datetime.now().isoformat()
        })

def mark_step_complete(review_id: str, step_name: str) -> None:
    """Mark a step as completed"""
    if review_id in review_progress:
        if step_name not in review_progress[review_id]["steps_completed"]:
            review_progress[review_id]["steps_completed"].append(step_name)

def complete_review(review_id: str, data: Any = None) -> None:
    """Mark review as complete"""
    if review_id in review_progress:
        review_progress[review_id].update({
            "status": "complete",
            "percentage": 100,
            "current_step": "Review complete",
            "end_time": datetime.now().isoformat(),
            "result_data": data
        })

def fail_review(review_id: str, error: str) -> None:
    """Mark review as failed"""
    if review_id in review_progress:
        review_progress[review_id].update({
            "status": "error",
            "error": error,
            "end_time": datetime.now().isoformat()
        })


# ============================================================================
# Pydantic Models
# ============================================================================

class DateRangeRequest(BaseModel):
    start_date: str
    end_date: str
    specialties: Optional[List[str]] = None  # Optional list of specialty filters


class PatientSelectionRequest(BaseModel):
    patient_ids: List[str]


class ReviewRequest(BaseModel):
    patient_id: str | int
    admission_id: str | int


class NotesDiagnosticsRequest(BaseModel):
    patient_id: str | int
    admission_id: str | int


class ExportRequest(BaseModel):
    patient_id: str
    analysis_id: str
    format: str  # docx, xlsx, pdf
    payload: Optional[Dict[str, Any]] = None  # optional inline data to export


# ============================================================================
# Helper Functions
# ============================================================================

def get_database_name() -> str:
    """Get database name from config."""
    db_name = db_config.get("databases", {}).get("LSV", {}).get("database", "CDWWORK")
    return db_name


def get_table_reference(table_path: str) -> str:
    """
    Build fully qualified table reference from config table path.
    
    Args:
        table_path: Table reference like "Inpat.Inpatient" or "TIU.TIUDocument"
    
    Returns:
        Fully qualified reference like [CDWWORK].[Inpat].[Inpatient]
    """
    db_name = get_database_name()
    
    if '.' in table_path:
        parts = table_path.split('.')
        # Build [Database].[Schema].[Table]
        schema_table = '].['.join(parts)
        return f"[{db_name}].[{schema_table}]"
    else:
        return f"[{db_name}].[{table_path}]"


def get_username() -> str:
    """Get the current Windows username."""
    return getpass.getuser()


def get_db_connection() -> DatabaseConnection:
    """Get or create database connection."""
    global db_connection

    if db_connection is None or not db_connection.is_connected:
        lsv_config = db_config.get("databases", {}).get("LSV", {})
        logger.info(f"Loading database config: server={lsv_config.get('server')}, database={lsv_config.get('database')}")
        
        if not lsv_config:
            logger.error("Database configuration not found in config file")
            raise HTTPException(status_code=500, detail="Database configuration not found")

        db_connection = DatabaseConnection(
            server=lsv_config.get("server"),
            database=lsv_config.get("database"),
            timeout=lsv_config.get("query_timeout_seconds", 300)
        )

        logger.info(f"Attempting database connection to {lsv_config.get('server')}/{lsv_config.get('database')}")
        if not db_connection.connect():
            logger.error(f"Failed to connect to database at {lsv_config.get('server')}")
            raise HTTPException(status_code=500, detail="Failed to connect to database")
        
        logger.info("Database connection successful")

    return db_connection


def classify_provider_roles(conn: DatabaseConnection, staff_sids: List[int]) -> Dict[int, Dict[str, str]]:
    """
    Attempt to classify provider roles (LIP vs trainee vs unknown) for given StaffSIDs.

    Best-effort: tries multiple likely staff tables and uses available columns.
    """
    if not staff_sids:
        return {}

    candidates = [
        "Dim.Staff",
        "Staff.Staff",
        "Dim.Provider",
        "Dim.PersonClass"
    ]

    role_map: Dict[int, Dict[str, str]] = {}
    sid_list = ",".join(str(int(sid)) for sid in staff_sids if sid is not None)

    for table_path in candidates:
        try:
            table_ref = get_table_reference(table_path)
            # Discover available columns
            schema, name = table_path.split(".")
            col_query = """
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
            """
            cols_result = conn.execute_query(col_query, params=(schema, name))
            if not isinstance(cols_result, dict) or not cols_result.get("success"):
                continue
            available = {row["COLUMN_NAME"] for row in cols_result.get("rows", [])}

            select_cols = []
            for col in ["StaffSID", "PersonClass", "ProviderType", "Occupation", "PositionTitle", "StaffName", "Name"]:
                if col in available:
                    select_cols.append(col)

            if "StaffSID" not in select_cols:
                continue

            columns_sql = ", ".join(f"[{c}]" for c in select_cols)
            role_query = f"""
            SELECT {columns_sql}
            FROM {table_ref}
            WHERE StaffSID IN ({sid_list})
            """
            role_result = conn.execute_query(role_query)
            if not isinstance(role_result, dict) or not role_result.get("success"):
                continue

            for row in role_result.get("rows", []):
                sid = row.get("StaffSID")
                raw_values = " ".join(str(row.get(c, "") or "") for c in select_cols if c != "StaffSID")
                raw_upper = raw_values.upper()
                role = "UNKNOWN"
                if any(tag in raw_upper for tag in ["RESIDENT", "FELLOW"]):
                    role = "TRAINEE"
                elif any(tag in raw_upper for tag in ["PHYSICIAN", "MD", "DO", "NURSE PRACTITIONER", "NP", "PHYSICIAN ASSISTANT", "PA"]):
                    role = "LIP"
                elif any(tag in raw_upper for tag in ["ATTENDING", "CONSULTANT"]):
                    role = "LIP"

                role_map[int(sid)] = {
                    "role": role,
                    "raw": raw_values.strip()[:200]
                }

            if role_map:
                break  # Stop after first successful table

        except Exception as e:
            logger.warning(f"Provider role lookup failed for {table_path}: {e}")
            continue

    return role_map


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the main application page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request):
    """Serve the query logs page."""
    return templates.TemplateResponse("logs.html", {"request": request})


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "components": {
            "database": db_connection.is_connected if db_connection else False,
            "va_gpt": va_gpt_client.is_initialized()
        }
    }


@app.get("/api/user/info")
async def get_user_info():
    """Get current user information."""
    return {
        "username": get_username(),
        "session_id": audit_logger.session_id
    }


@app.get("/api/review/progress/{review_id}")
async def get_review_progress(review_id: str):
    """
    Get current progress of a review operation.
    
    Returns:
    {
        "status": "processing|complete|error",
        "percentage": 0-100,
        "current_step": "description of current operation",
        "steps_completed": ["step1", "step2", ...],
        "elapsed_seconds": seconds since start,
        "error": null or error message
    }
    """
    if review_id not in review_progress:
        raise HTTPException(status_code=404, detail="Review not found")
    
    progress = review_progress[review_id]
    
    # Calculate elapsed time
    start_time = datetime.fromisoformat(progress["start_time"])
    elapsed_seconds = (datetime.now() - start_time).total_seconds()
    
    return {
        "review_id": review_id,
        "status": progress["status"],
        "percentage": progress["percentage"],
        "current_step": progress["current_step"],
        "steps_completed": progress["steps_completed"],
        "elapsed_seconds": int(elapsed_seconds),
        "error": progress.get("error")
    }


@app.post("/api/diagnostics/notes")
async def diagnose_notes(request: NotesDiagnosticsRequest):
    """
    Return PHI-safe note-type counts for a given admission window.
    No note text or patient identifiers are returned.
    """
    try:
        conn = get_db_connection()

        # Build fully qualified table references
        tiu_doc_table = get_table_reference("TIU.TIUDocument")
        tiu_def_table = get_table_reference("Dim.TIUDocumentDefinition")
        inpat_table = get_table_reference("Inpat.Inpatient")

        # First: Get admission date info
        admit_query = f"""
        SELECT 
            AdmitDateTime,
            DischargeDateTime,
            DATEDIFF(day, AdmitDateTime, COALESCE(DischargeDateTime, GETDATE())) as LengthOfStay
        FROM {inpat_table}
        WHERE InpatientSID = ?
        """
        
        admit_result = conn.execute_query(admit_query, params=(request.admission_id,))
        admit_row = admit_result.get("rows", [])[0] if admit_result.get("success") and admit_result.get("rows") else None
        
        admit_info = None
        if admit_row:
            admit_info = {
                "admit_date": str(admit_row.get("AdmitDateTime")) if admit_row.get("AdmitDateTime") else None,
                "discharge_date": str(admit_row.get("DischargeDateTime")) if admit_row.get("DischargeDateTime") else None,
                "length_of_stay": admit_row.get("LengthOfStay")
            }

        # Second: Count ALL TIU notes for this patient (no date restriction)
        all_notes_query = f"""
        SELECT COUNT(*) as TotalCount
        FROM {tiu_doc_table} td
        WHERE td.PatientSID = TRY_CAST(? as int)
        """
        
        all_count_result = conn.execute_query(all_notes_query, params=(request.patient_id,))
        all_count_row = all_count_result.get("rows", [])[0] if all_count_result.get("success") and all_count_result.get("rows") else None
        total_all_notes = all_count_row.get("TotalCount", 0) if all_count_row else 0

        # Third: Count notes within admission window
        counts_query = f"""
        SELECT TOP 200
            COALESCE(ddef.TIUDocumentDefinitionPrintName, 'UNKNOWN') as NoteType,
            COUNT(1) as NoteCount
        FROM {tiu_doc_table} td
        LEFT JOIN {tiu_def_table} ddef
            ON td.TIUDocumentDefinitionSID = ddef.TIUDocumentDefinitionSID
        INNER JOIN {inpat_table} ip
            ON ip.InpatientSID = ?
            AND ip.PatientSID = td.PatientSID
        WHERE td.PatientSID = TRY_CAST(? as int)
          AND td.ReferenceDateTime >= ip.AdmitDateTime
          AND (ip.DischargeDateTime IS NULL OR td.ReferenceDateTime <= ip.DischargeDateTime)
        GROUP BY ddef.TIUDocumentDefinitionPrintName
        ORDER BY NoteCount DESC
        """

        params = (
            request.admission_id,
            request.patient_id
        )

        counts_result = conn.execute_query(counts_query, params=params)
        rows = counts_result.get("rows", []) if counts_result.get("success") else []

        include_terms = [
            "HISTORY & PHYSICAL",
            "HISTORY AND PHYSICAL",
            "ALLERGY",
            "AMBULATORY SURGERY",
            "ANES - ATTENDING",
            "PROCEDURE NOTE",
            "ANES",
            "ARRHYTHMIA",
            "ATTENDING",
            "RESIDENT",
            "FELLOW",
            "NP",
            "PHYSICIAN",
            "CONSULT",
            "PROGRESS NOTE",
            "CP",
            "DISCHARGE SUMMARY",
            "DISCHARGE",
            "INPATIENT NOTE",
            "GI",
            "MEDICINE SERVICE"
        ]

        exclude_terms = [
            "BNP",
            "NURSE",
            "NURSING"
        ]

        def matches_filters(note_type: str) -> bool:
            name = (note_type or "").upper()
            include_ok = any(term in name for term in include_terms)
            exclude_hit = any(term in name for term in exclude_terms)
            return include_ok and not exclude_hit

        matched = [
            {"NoteType": r.get("NoteType"), "NoteCount": r.get("NoteCount", 0)}
            for r in rows
            if matches_filters(r.get("NoteType"))
        ]

        return {
            "success": True,
            "admission_info": admit_info,
            "total_notes_for_patient": total_all_notes,
            "total_note_types": len(rows),
            "matched_note_types": len(matched),
            "note_types": rows,
            "matched_types": matched
        }
    except Exception as e:
        logger.error(f"Error running notes diagnostics: {e}")
        return {
            "success": False,
            "error": str(e),
            "admission_info": None,
            "total_notes_for_patient": 0,
            "note_types": [],
            "matched_types": []
        }


@app.get("/api/specialties")
async def get_available_specialties():
    """Get list of available treating specialties from database for Station 626."""
    try:
        try:
            conn = get_db_connection()
        except HTTPException as e:
            logger.error(f"Failed to get database connection: {e.detail}")
            return {
                "success": False,
                "specialties": [],
                "count": 0,
                "error": str(e.detail)
            }
        except Exception as e:
            logger.error(f"Unexpected error getting database connection: {e}", exc_info=True)
            return {
                "success": False,
                "specialties": [],
                "count": 0,
                "error": str(e)
            }
        
        specialty_table = get_table_reference("Dim.TreatingSpecialty")
        station = db_config.get("extraction_settings", {}).get("station_focus", 626)
        
        # Query treating specialties for the station - use [Specialty] column
        query = f"""
        SELECT DISTINCT [Specialty]
        FROM {specialty_table}
        WHERE [Sta3n] = {station}
          AND [Specialty] NOT LIKE '%Missing%'
          AND [Specialty] NOT LIKE '%Unknown%'
          AND [Specialty] NOT LIKE '%Delete%'
          AND [Specialty] IS NOT NULL
          AND LTRIM(RTRIM([Specialty])) != ''
        ORDER BY [Specialty]
        """
        
        logger.info(f"Executing specialty query with table: {specialty_table}, station: {station}")
        result = conn.execute_query(query)
        logger.info(f"Specialty query result: success={result.get('success')}, rows={len(result.get('rows', []))}, error={result.get('error')}")
        
        if result.get("success") and result.get("rows"):
            specialties = [
                {
                    "id": idx,
                    "name": row.get("Specialty", "Unknown")
                }
                for idx, row in enumerate(result.get("rows", []), 1)
            ]
            logger.info(f"Retrieved {len(specialties)} specialties for station {station}")
            return {
                "success": True,
                "specialties": specialties,
                "count": len(specialties)
            }
        else:
            error_msg = result.get("error", "No specialties found in database")
            logger.warning(f"No specialties found for station {station}. Query result: {result}")
            return {
                "success": False,
                "specialties": [],
                "count": 0,
                "error": "No specialties found in database"
            }
    except Exception as e:
        logger.error(f"Error fetching specialties: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "specialties": [],
            "count": 0,
            "error": str(e)
        }


@app.post("/api/patients/discharged")
async def get_discharged_patients(request: DateRangeRequest):
    """
    Get list of patients discharged within the specified date range.

    NOTE: This query will need to be updated once we identify the correct
    discharge table in the LSV schema.
    """
    username = get_username()

    try:
        conn = get_db_connection()
        discharge_table = db_config.get("tables", {}).get("discharge_table")
        station = db_config.get("extraction_settings", {}).get("station_focus", 626)

        if not discharge_table:
            raise HTTPException(status_code=500, detail="Discharge table not configured")

        # Split schema.table if needed
        if '.' in discharge_table:
            schema, table = discharge_table.split('.', 1)
            table_ref = get_table_reference(discharge_table)
        else:
            table_ref = get_table_reference(discharge_table)

        # Get other table references from config
        patient_table = get_table_reference("SPatient.SPatient")
        ward_table = get_table_reference("Inpat.Inpatient")  # Using base inpatient table
        specialty_transfer_table = get_table_reference("Inpat.SpecialtyTransfer")
        treating_specialty_table = get_table_reference("Dim.TreatingSpecialty")
        
        # Query inpatient admissions/discharges with patient demographics and admitting specialty
        # Admitting treating specialty comes from earliest SpecialtyTransfer (501 record)
        # joined to Dim.TreatingSpecialty using TreatingSpecialtySID
        # Specialty filter is applied AFTER query (in Python, below)
        query = f"""
        SELECT TOP 100
            i.InpatientSID,
            i.PatientSID,
            i.PTFIEN as AdmissionID,
            CAST(i.PatientSID AS VARCHAR(20)) as PatientID,
            p.PatientName,
            p.PatientSSN,
            p.ScrSSN,
            COALESCE(admitting_spec.Specialty, 'UNKNOWN') as AdmittingTreatingSpecialty,
            i.AdmitDateTime as AdmissionDate,
            i.DischargeDateTime as DischargeDate,
            i.AdmitDiagnosis as AdmittingDiagnosis,
            CASE 
                WHEN i.PrincipalDiagnosisICD10SID IS NOT NULL THEN 'ICD10'
                WHEN i.PrincipalDiagnosisICD9SID IS NOT NULL THEN 'ICD9'
                ELSE 'Not Coded'
            END as DischargeDiagnosis,
            DATEDIFF(day, i.AdmitDateTime, i.DischargeDateTime) as LOS,
            i.Sta3n as Station
        FROM {table_ref} i
        LEFT JOIN {patient_table} p ON i.PatientSID = p.PatientSID
        LEFT JOIN (
            -- Get the first (admitting) specialty transfer for each admission
            SELECT 
                ranked.InpatientSID,
                ranked.TreatingSpecialtySID,
                ts.Specialty
            FROM (
                SELECT 
                    st.InpatientSID,
                    st.TreatingSpecialtySID,
                    ROW_NUMBER() OVER (PARTITION BY st.InpatientSID ORDER BY st.SpecialtyTransferDateTime ASC) as rn
                FROM {specialty_transfer_table} st
                WHERE st.TreatingSpecialtySID IS NOT NULL AND st.TreatingSpecialtySID > 0
            ) ranked
            INNER JOIN {treating_specialty_table} ts 
                ON ranked.TreatingSpecialtySID = ts.TreatingSpecialtySID
            WHERE ranked.rn = 1
        ) admitting_spec ON i.InpatientSID = admitting_spec.InpatientSID
        WHERE i.DischargeDateTime >= '{request.start_date}'
          AND i.DischargeDateTime < DATEADD(day, 1, '{request.end_date}')
          AND i.Sta3n = {station}
          AND i.DischargeDateTime IS NOT NULL
          AND i.AdmitDateTime IS NOT NULL
        ORDER BY i.DischargeDateTime DESC
        """

        # Log the search parameters
        logger.info(f"Searching discharged patients: date_range={request.start_date} to {request.end_date}, specialties={request.specialties}")

        # Execute query with timing
        start_time = time.time()
        result = conn.execute_query(query)
        execution_time_ms = (time.time() - start_time) * 1000

        # Apply specialty filter AFTER query (in Python)
        # Only filter if specialties are actually selected (non-empty list)
        if request.specialties is not None and len(request.specialties) > 0 and result.get("rows"):
            original_count = len(result["rows"])
            selected_specialties = {
                s.strip().upper() for s in request.specialties if s and s.strip()
            }
            logger.info(
                f"Specialty filter: filtering {original_count} patients by specialties: {sorted(selected_specialties)}"
            )
            result["rows"] = [
                row for row in result["rows"]
                if row.get("AdmittingTreatingSpecialty", "").strip().upper() in selected_specialties
            ]
            filtered_count = len(result["rows"])
            logger.info(f"Specialty filter applied: {original_count} patients → {filtered_count} patients")
            result["row_count"] = filtered_count
        else:
            logger.info(f"No specialty filter applied - specialties list: {request.specialties}")

        # Sanitize results for logging (remove PII, keep non-PII identifiers)
        sanitized_results = []
        if result.get("rows"):
            for row in result["rows"][:3]:  # Only first 3 rows
                sanitized_row = {k: v for k, v in row.items() if k not in ['PatientName', 'PatientSSN']}
                # ScrSSN and PatientSID are kept for debugging
                sanitized_results.append(sanitized_row)

        # Log the query (without PII)
        query_logger.log_query(
            query_type="PATIENT_DISCHARGE_SEARCH",
            username=username,
            sql_query=query,
            parameters={
                "start_date": request.start_date,
                "end_date": request.end_date,
                "station": station,
                "discharge_table": discharge_table
            },
            success=result["success"],
            results=sanitized_results,  # Use sanitized results
            error=result.get("error"),
            row_count=result["row_count"],
            execution_time_ms=execution_time_ms
        )

        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])

        audit_logger.log_event(
            event_type="PATIENT_LIST_QUERY",
            username=username,
            details={
                "start_date": request.start_date,
                "end_date": request.end_date,
                "patients_found": result["row_count"]
            }
        )

        # Apply specialty mapping to convert database codes to display names
        if result.get("rows"):
            for patient in result["rows"]:
                if "AdmittingTreatingSpecialty" in patient:
                    patient["AdmittingTreatingSpecialtyRaw"] = patient["AdmittingTreatingSpecialty"]
                    patient["AdmittingTreatingSpecialty"] = map_specialty_display(
                        specialty_desc=patient["AdmittingTreatingSpecialty"],
                        los_in_service=patient.get("LOS")
                    )

        return {
            "success": True,
            "patients": result.get("rows", []),
            "count": len(result.get("rows", [])),
            "date_range": {
                "start": request.start_date,
                "end": request.end_date
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching discharged patients: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "patients": [],
            "count": 0,
            "error": str(e)
        }


@app.post("/api/review/start")
async def start_review(request: ReviewRequest):
    """
    Start the documentation review process for a patient.

    This endpoint:
    1. Extracts all relevant clinical notes
    2. Extracts vital signs
    3. Extracts laboratory values
    4. Extracts coded diagnoses from PTF
    5. Runs AI analysis on the documentation
    6. Compares AI diagnoses against coded diagnoses
    
    Returns review_id immediately; use /api/review/progress/{review_id} to track progress.
    """
    username = get_username()
    start_time = time.time()
    
    # Generate unique review ID
    import uuid
    review_id = str(uuid.uuid4())[:8]
    
    # Initialize progress tracking
    create_progress_tracker(review_id)

    try:
        # Validate request parameters
        if not request or not hasattr(request, 'patient_id') or not hasattr(request, 'admission_id'):
            fail_review(review_id, "Invalid request parameters: missing patient_id or admission_id")
            raise HTTPException(status_code=400, detail="Invalid request parameters: missing patient_id or admission_id")
        
        # Normalize IDs to strings for downstream queries
        normalized_patient_id = str(request.patient_id)
        normalized_admission_id = str(request.admission_id)
        
        update_progress(review_id, 5, "Loading patient admission data...")
        logger.info(f"Starting review {review_id} for patient={normalized_patient_id}, admission={normalized_admission_id}")

        conn = get_db_connection()
        if not conn or not conn.is_connected:
            fail_review(review_id, "Unable to connect to database")
            raise HTTPException(status_code=500, detail="Unable to connect to database")

        # Resolve admission (InpatientSID) and date window
        inpat_table = get_table_reference("Inpat.Inpatient")
        admission_lookup = f"""
        SELECT TOP 1
            InpatientSID,
            PatientSID,
            Sta3n,
            AdmitDateTime,
            DischargeDateTime
        FROM {inpat_table}
        WHERE (PTFIEN = ? OR CAST(InpatientSID AS varchar(50)) = ?)
          AND PatientSID = TRY_CAST(? as int)
        ORDER BY DischargeDateTime DESC
        """
        admission_res = conn.execute_query(admission_lookup, params=(normalized_admission_id, normalized_admission_id, normalized_patient_id))
        
        if not isinstance(admission_res, dict):
            logger.error(f"admission_res is not a dict, got {type(admission_res)}: {admission_res}")
            fail_review(review_id, "Database query returned invalid response")
            raise HTTPException(status_code=500, detail="Database query returned invalid response")

        # Fallback: user may pass InpatientSID as patient_id; try resolving without patient filter
        if (not admission_res.get("success") or not admission_res.get("rows")):
            fallback_lookup = f"""
            SELECT TOP 1
                InpatientSID,
                PatientSID,
                Sta3n,
                AdmitDateTime,
                DischargeDateTime
            FROM {inpat_table}
            WHERE InpatientSID = TRY_CAST(? as bigint)
               OR PTFIEN = ?
            ORDER BY DischargeDateTime DESC
            """
            admission_res = conn.execute_query(fallback_lookup, params=(normalized_patient_id, normalized_admission_id))
            
            if not isinstance(admission_res, dict):
                logger.error(f"Fallback admission_res is not a dict, got {type(admission_res)}: {admission_res}")
                raise HTTPException(status_code=500, detail="Database query returned invalid response")

        if not admission_res.get("success") or not admission_res.get("rows"):
            raise HTTPException(status_code=404, detail="Admission not found for provided identifiers")
        
        admission_info = admission_res["rows"][0]
        inpatient_sid = admission_info.get("InpatientSID")
        admission_start = admission_info.get("AdmitDateTime")
        admission_end = admission_info.get("DischargeDateTime") or admission_start
        station = admission_info.get("Sta3n") or db_config.get("extraction_settings", {}).get("station_focus", 626)

        # Log analysis start
        analysis_id = audit_logger.log_analysis_start(
            username=username,
            patient_id=request.patient_id,
            analysis_type="FULL_HOSPITALIZATION_REVIEW",
            document_count=0  # Will update after extraction
        )

        # ================================================================
        # Step 1: Extract Clinical Notes
        # ================================================================
        step_start = time.time()
        # Provider classes to include - notes authored by these provider types
        provider_classes_to_include = [
            "PHYSICIAN",
            "PHYSICIAN ",  # Note: Has trailing space in database
            "PHYSICIAN ASSISTANT",
            "RESIDENT PODIATRIST",
            "RESIDENT- ORAL SURGERY",
            "RESIDENT PSYCHIATRIST",
            "CONSULTANT",
            "RESIDENT-PHYSICIAN",
            "RESIDENT PHYSICIAN",
            "RESIDENT SURGEON",
            "FELLOW",
            "PSYCHIATRIST",
            "SURGEON",
            "WOC ATTENDING",
            "ORAL SURGEON",
            "PHYSICIAN (DUPLICATE)",
            "PHYSICIAN (CONTRACT)",
            "PHYSICIAN (WOC)",
            "ANESTHESIOLOGIST",
            "PULMONOLOGIST",
            "PATHOLOGIST",
            "STAFF PSYCHIATRIST",
            "HOUSESTAFF",
            "RESIDENT-DENTIST",
            "ORTHOPEDICS",
            "OPTOMETRY",
            "DO",
            "PA",
            "INTERN"
        ]

        text_column = None
        column_query = """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'TIU' AND TABLE_NAME = 'TIUDocument'
        """
        column_result = conn.execute_query(column_query)
        if not isinstance(column_result, dict):
            logger.error(f"column_result is not a dict, got {type(column_result)}")
            raise HTTPException(status_code=500, detail="Column query returned invalid response")
        if column_result.get("success") and column_result.get("rows"):
            available_columns = {row["COLUMN_NAME"] for row in column_result["rows"]}
            for candidate in ["ReportText", "NoteText", "DocumentText", "TIUText", "Text"]:
                if candidate in available_columns:
                    text_column = candidate
                    break
        note_text_expression = f"td.[{text_column}]" if text_column else "CAST(NULL as varchar(max))"

        # Build fully qualified table references
        tiu_doc_table = get_table_reference("TIU.TIUDocument")
        tiu_def_table = get_table_reference("Dim.TIUDocumentDefinition")
        note_text_table = get_table_reference("STIUNotes.TIUDocument_8925")
        staff_table = get_table_reference("Staff.Staff")

        # Build IN clause for provider classes
        provider_class_placeholders = ", ".join(["?" for _ in provider_classes_to_include])

        notes_query = f"""
        SELECT TOP 200
            td.TIUDocumentSID as NoteID,
            ddef.TIUDocumentDefinitionPrintName as NoteType,
            td.ReferenceDateTime as NoteDateTime,
            td.SignedByStaffSID as AuthorStaffSID,
            td.CosignedByStaffSID as CosignedByStaffSID,
            td.SignatureDateTime,
            txt.ReportText as NoteText,
            s.ProviderClass as AuthorProviderClass
        FROM {tiu_doc_table} td
        LEFT JOIN {tiu_def_table} ddef
            ON td.TIUDocumentDefinitionSID = ddef.TIUDocumentDefinitionSID
        INNER JOIN {note_text_table} txt
            ON td.TIUDocumentSID = txt.TIUDocumentSID
        INNER JOIN {staff_table} s
            ON td.SignedByStaffSID = s.StaffSID
        WHERE td.PatientSID = TRY_CAST(? as int)
          AND td.ReferenceDateTime >= ?
          AND ( ? IS NULL OR td.ReferenceDateTime <= ? )
          AND txt.ReportText IS NOT NULL
          AND s.ProviderClass IN ({provider_class_placeholders})
        ORDER BY td.ReferenceDateTime DESC
        """

        notes_params = (
            normalized_patient_id,
            admission_start,
            admission_end,
            admission_end,
            *provider_classes_to_include
        )

        notes_result = conn.execute_query(notes_query, params=notes_params)
        if not isinstance(notes_result, dict):
            logger.error(f"notes_result is not a dict, got {type(notes_result)}: {notes_result}")
            fail_review(review_id, "Notes query returned invalid response")
            raise HTTPException(status_code=500, detail="Database query returned invalid response")
        
        if not notes_result.get("success"):
            logger.warning(f"Notes extraction query failed: {notes_result.get('error')}. Continuing with empty notes.")
            clinical_notes = []
        else:
            clinical_notes = notes_result.get("rows", []) or []
        
        update_progress(review_id, 15, f"Extracted {len(clinical_notes)} clinical notes")
        mark_step_complete(review_id, "Extract Clinical Notes")

        # Enrich notes: add character counts and provider role tags (best-effort)
        staff_sids = set()
        for note in clinical_notes:
            note_text = note.get("NoteText") or ""
            note["NoteCharCount"] = len(note_text)
            if note.get("AuthorStaffSID"):
                staff_sids.add(note["AuthorStaffSID"])
            if note.get("CosignedByStaffSID"):
                staff_sids.add(note["CosignedByStaffSID"])

        provider_roles = classify_provider_roles(conn, list(staff_sids))
        for note in clinical_notes:
            author_sid = note.get("AuthorStaffSID")
            cosigner_sid = note.get("CosignedByStaffSID")
            if author_sid in provider_roles:
                note["AuthorRole"] = provider_roles[author_sid]["role"]
                note["AuthorRoleRaw"] = provider_roles[author_sid]["raw"]
            if cosigner_sid in provider_roles:
                note["CosignerRole"] = provider_roles[cosigner_sid]["role"]
                note["CosignerRoleRaw"] = provider_roles[cosigner_sid]["raw"]

        # No fallback without filters: enforce explicit include/exclude criteria
        
        query_logger.log_query(
            query_type="EXTRACT_CLINICAL_NOTES",
            username=username,
            sql_query=notes_query,
            parameters={
                "patient_id": request.patient_id,
                "admission_id": request.admission_id,
                "provider_classes_count": len(provider_classes_to_include),
                "note_text_column": text_column or "(none)"
            },
            success=notes_result["success"],
            results=clinical_notes,
            error=notes_result.get("error"),
            row_count=len(clinical_notes),
            execution_time_ms=(time.time() - step_start) * 1000
        )
        
        query_logger.log_evaluation_step(
            evaluation_id=analysis_id,
            patient_id=request.patient_id,
            username=username,
            step_name="Extract Clinical Notes",
            step_type="DATA_EXTRACTION",
            success=notes_result["success"],
            input_data={"patient_id": request.patient_id},
            output_data={"notes_count": len(clinical_notes)},
            error=notes_result.get("error"),
            execution_time_ms=(time.time() - step_start) * 1000
        )

        # ================================================================
        # Step 2: Extract Vital Signs
        # ================================================================
        step_start = time.time()
        vital_table = get_table_reference(db_config.get("tables", {}).get("vitals_table", "Vital.VitalSign"))
        vital_type_table = get_table_reference("Dim.VitalType")
        vitals_query = f"""
        SELECT
            vs.VitalSignSID,
            vs.PatientSID,
            vs.Sta3n,
            vs.VitalSignTakenDateTime AS TakenDateTime,
            vs.VitalSignTakenDateTime AS EnteredDateTime,
            vs.VitalTypeSID,
            vt.VitalType,
            vs.VitalResult,
            vs.VitalResultNumeric
        FROM {vital_table} vs
        LEFT JOIN {vital_type_table} vt
            ON vs.VitalTypeSID = vt.VitalTypeSID
        WHERE vs.PatientSID = TRY_CAST(? as int)
          AND vs.Sta3n = ?
          AND vs.VitalSignTakenDateTime BETWEEN ? AND DATEADD(day, 1, ?)
        ORDER BY vs.VitalSignTakenDateTime
        """

        vitals_result = conn.execute_query(
            vitals_query,
            params=(normalized_patient_id, station, admission_start, admission_end)
        )
        if not isinstance(vitals_result, dict):
            logger.error(f"vitals_result is not a dict, got {type(vitals_result)}")
            fail_review(review_id, "Vitals query returned invalid response")
            raise HTTPException(status_code=500, detail="Vitals query returned invalid response")
        
        if not vitals_result.get("success"):
            logger.warning(f"Vitals extraction query failed: {vitals_result.get('error')}. Continuing with empty vitals.")
            vitals = []
        else:
            vitals = vitals_result.get("rows", []) or []
        
        update_progress(review_id, 30, f"Extracted {len(vitals)} vital sign measurements")
        mark_step_complete(review_id, "Extract Vitals")

        query_logger.log_query(
            query_type="EXTRACT_VITALS",
            username=username,
            sql_query=vitals_query,
            parameters={
                "patient_id": request.patient_id,
                "station": station,
                "start": admission_start,
                "end_plus1": admission_end
            },
            success=vitals_result["success"],
            results=vitals,
            error=vitals_result.get("error"),
            row_count=len(vitals),
            execution_time_ms=(time.time() - step_start) * 1000
        )

        query_logger.log_evaluation_step(
            evaluation_id=analysis_id,
            patient_id=request.patient_id,
            username=username,
            step_name="Extract Vitals",
            step_type="DATA_EXTRACTION",
            success=vitals_result["success"],
            input_data={"patient_id": request.patient_id},
            output_data={"vitals_count": len(vitals)},
            error=vitals_result.get("error"),
            execution_time_ms=(time.time() - step_start) * 1000
        )

        # ================================================================
        # Step 3: Extract Laboratory Values
        # ================================================================
        labs_table = get_table_reference(db_config.get("tables", {}).get("labs_table", "Chem.LabChem"))
        lab_test_table = get_table_reference("Dim.LabChemTest")
        step_start = time.time()
        labs_query = f"""
        SELECT
            lc.LabChemSID,
            lc.PatientSID,
            lc.Sta3n,
            lc.LabChemSpecimenDateTime,
            lc.LabChemCompleteDateTime,
            lc.LabChemTestSID,
            dlt.LabChemTestName,
            lc.LabChemResultValue,
            lc.LabChemResultNumericValue,
            lc.Units as ResultUnits,
            lc.LOINCSID
        FROM {labs_table} lc
        LEFT JOIN {lab_test_table} dlt
            ON lc.LabChemTestSID = dlt.LabChemTestSID
        WHERE lc.PatientSID = TRY_CAST(? as int)
          AND lc.Sta3n = ?
          AND lc.LabChemSpecimenDateTime BETWEEN ? AND DATEADD(day, 1, ?)
        ORDER BY lc.LabChemSpecimenDateTime
        """

        labs_result = conn.execute_query(
            labs_query,
            params=(normalized_patient_id, station, admission_start, admission_end)
        )
        if not isinstance(labs_result, dict):
            logger.error(f"labs_result is not a dict, got {type(labs_result)}")
            fail_review(review_id, "Labs query returned invalid response")
            raise HTTPException(status_code=500, detail="Labs query returned invalid response")
        
        if not labs_result.get("success"):
            logger.warning(f"Labs extraction query failed: {labs_result.get('error')}. Continuing with empty labs.")
            labs = []
        else:
            labs = labs_result.get("rows", []) or []
        
        update_progress(review_id, 45, f"Extracted {len(labs)} laboratory values")
        mark_step_complete(review_id, "Extract Labs")

        query_logger.log_query(
            query_type="EXTRACT_LABS",
            username=username,
            sql_query=labs_query,
            parameters={
                "patient_id": request.patient_id,
                "station": station,
                "start": admission_start,
                "end_plus1": admission_end
            },
            success=labs_result["success"],
            results=labs,
            error=labs_result.get("error"),
            row_count=len(labs),
            execution_time_ms=(time.time() - step_start) * 1000
        )

        query_logger.log_evaluation_step(
            evaluation_id=analysis_id,
            patient_id=request.patient_id,
            username=username,
            step_name="Extract Labs",
            step_type="DATA_EXTRACTION",
            success=labs_result["success"],
            input_data={"patient_id": request.patient_id},
            output_data={"labs_count": len(labs)},
            error=labs_result.get("error"),
            execution_time_ms=(time.time() - step_start) * 1000
        )

        # ================================================================
        # Step 4: Extract Coded Diagnoses (PTF)
        # ================================================================
        ptf_table = get_table_reference(db_config.get("tables", {}).get("ptf_diagnoses_table", "Inpat.InpatientDischargeDiagnosis"))
        icd10_table = get_table_reference("Dim.ICD10")
        icd9_table = get_table_reference("Dim.ICD9")
        icd10_desc_table = get_table_reference("Dim.ICD10DiagnosisVersion")
        icd9_desc_table = get_table_reference("Dim.ICD9DiagnosisVersion")
        
        step_start = time.time()
        diagnoses_query = f"""
        SELECT
            dd.InpatientDischargeDiagnosisSID,
            dd.InpatientSID,
            dd.PTFIEN,
            dd.OrdinalNumber as DiagnosisSequence,
            dd.ICD10SID,
            dd.ICD9SID,
            COALESCE(icd10.ICD10Code, icd9.ICD9Code, 'UNKNOWN') as ICD10Code,
            COALESCE(icd10_desc.ICD10Diagnosis, icd9_desc.ICD9Diagnosis, 'No description available') as DiagnosisDescription,
            CASE 
                WHEN dd.ICD10SID IS NOT NULL AND dd.ICD10SID > 0 THEN 'ICD-10'
                WHEN dd.ICD9SID IS NOT NULL AND dd.ICD9SID > 0 THEN 'ICD-9'
                ELSE 'UNCODED'
            END as CodeSystem
        FROM {ptf_table} dd
        LEFT JOIN {icd10_table} icd10 ON dd.ICD10SID = icd10.ICD10SID
        LEFT JOIN {icd9_table} icd9 ON dd.ICD9SID = icd9.ICD9SID
        LEFT JOIN {icd10_desc_table} icd10_desc 
            ON dd.ICD10SID = icd10_desc.ICD10SID 
            AND icd10_desc.CurrentVersionFlag = 'Y'
        LEFT JOIN {icd9_desc_table} icd9_desc 
            ON dd.ICD9SID = icd9_desc.ICD9SID 
            AND icd9_desc.CurrentVersionFlag = 'Y'
        WHERE (dd.PTFIEN = ? OR dd.InpatientSID = TRY_CAST(? as bigint))
          AND dd.Sta3n = ?
        ORDER BY dd.OrdinalNumber
        """

        diagnoses_result = conn.execute_query(
            diagnoses_query,
            params=(normalized_admission_id, inpatient_sid, station)
        )
        if not isinstance(diagnoses_result, dict):
            logger.error(f"diagnoses_result is not a dict, got {type(diagnoses_result)}")
            fail_review(review_id, "Diagnoses query returned invalid response")
            raise HTTPException(status_code=500, detail="Diagnoses query returned invalid response")
        
        if not diagnoses_result.get("success"):
            logger.warning(f"Diagnoses extraction query failed: {diagnoses_result.get('error')}. Continuing with empty diagnoses.")
            coded_diagnoses = []
        else:
            coded_diagnoses = diagnoses_result.get("rows", []) or []
        
        update_progress(review_id, 55, f"Extracted {len(coded_diagnoses)} coded diagnoses")
        mark_step_complete(review_id, "Extract Diagnoses")

        query_logger.log_query(
            query_type="EXTRACT_PTF_DIAGNOSES",
            username=username,
            sql_query=diagnoses_query,
            parameters={
                "admission_id": request.admission_id,
                "inpatient_sid": inpatient_sid,
                "station": station
            },
            success=diagnoses_result["success"],
            results=coded_diagnoses,
            error=diagnoses_result.get("error"),
            row_count=len(coded_diagnoses),
            execution_time_ms=(time.time() - step_start) * 1000
        )

        query_logger.log_evaluation_step(
            evaluation_id=analysis_id,
            patient_id=request.patient_id,
            username=username,
            step_name="Extract PTF Diagnoses",
            step_type="DATA_EXTRACTION",
            success=diagnoses_result["success"],
            input_data={"patient_id": request.patient_id},
            output_data={"diagnosis_count": len(coded_diagnoses)},
            error=diagnoses_result.get("error"),
            execution_time_ms=(time.time() - step_start) * 1000
        )

        # Log document extraction
        audit_logger.log_document_extraction(
            username=username,
            patient_id=request.patient_id,
            document_types=["TIU Notes", "Vitals", "Labs", "PTF Diagnoses"],
            document_count=len(clinical_notes) + len(vitals) + len(labs),
            success=True
        )

        # ================================================================
        # Step 5: AI Analysis of Clinical Notes
        # ================================================================
        update_progress(review_id, 60, "Running AI analysis on clinical documentation...")
        
        note_analyses = []

        for note in clinical_notes:
            # Analyze each note
            analysis = va_gpt_client.analyze_clinical_note(
                note_text=note.get("NoteText", ""),
                note_type=note.get("NoteType", "Unknown"),
                patient_context={
                    "vitals": vitals,
                    "labs": labs
                }
            )

            if not isinstance(analysis, dict):
                logger.error(f"analysis is not a dict for note {note.get('NoteID')}, got {type(analysis)}")
                continue
                
            if analysis.get("success"):
                note_analyses.append({
                    "note_id": note.get("NoteID"),
                    "note_type": note.get("NoteType"),
                    "analysis": analysis.get("analysis")
                })

        update_progress(review_id, 70, f"Analyzed {len(note_analyses)} clinical notes")
        mark_step_complete(review_id, "Analyze Clinical Notes")

        # ================================================================
        # Step 6: Consolidate All Analyses
        # ================================================================
        if not note_analyses:
            consolidated = {
                "success": False,
                "consolidated": None,
                "error": "No clinical notes were extracted for this admission."
            }
        else:
            consolidated = va_gpt_client.consolidate_analyses(
                note_analyses=[a.get("analysis") for a in note_analyses if a.get("analysis")],
                patient_info={
                    "patient_id": request.patient_id,
                    "admission_id": request.admission_id
                }
            )
        
        if not isinstance(consolidated, dict):
            logger.error(f"consolidated is not a dict, got {type(consolidated)}")
            raise HTTPException(status_code=500, detail="Consolidation analysis returned invalid response")

        # ================================================================
        # Step 7: Compare Against Coded Diagnoses
        # ================================================================
        update_progress(review_id, 80, "Comparing AI diagnoses with coded diagnoses...")
        
        ai_diagnoses = []
        if consolidated.get("success") and consolidated.get("consolidated"):
            cons = consolidated["consolidated"]
            if cons.get("principal_diagnosis"):
                ai_diagnoses.append(cons["principal_diagnosis"])
            ai_diagnoses.extend(cons.get("secondary_diagnoses", []))

        comparison = va_gpt_client.compare_diagnoses(
            documented_diagnoses=ai_diagnoses,
            coded_diagnoses=[
                {
                    "icd10": d.get("ICD10Code"),
                    "description": d.get("DiagnosisDescription"),
                    "sequence": d.get("DiagnosisSequence")
                }
                for d in coded_diagnoses
            ]
        )
        
        if not isinstance(comparison, dict):
            logger.error(f"comparison is not a dict, got {type(comparison)}")
            raise HTTPException(status_code=500, detail="Diagnosis comparison returned invalid response")

        # Calculate processing time
        processing_time = time.time() - start_time

        # Log analysis completion
        audit_logger.log_analysis_complete(
            username=username,
            patient_id=request.patient_id,
            analysis_id=analysis_id,
            diagnoses_found=len(ai_diagnoses),
            processing_time_seconds=processing_time,
            success=True
        )

        # Log detailed analysis
        audit_logger.log_analysis_details(
            analysis_id=analysis_id,
            patient_id=request.patient_id,
            username=username,
            notes_analyzed=clinical_notes,
            ai_diagnoses=ai_diagnoses,
            coded_diagnoses=coded_diagnoses,
            comparison=comparison.get("comparison", {}),
            total_time_seconds=processing_time
        )

        # Log comparison results
        if comparison.get("success") and comparison.get("comparison"):
            comp = comparison["comparison"]
            audit_logger.log_comparison_result(
                username=username,
                patient_id=request.patient_id,
                documented_diagnoses=len(ai_diagnoses),
                coded_diagnoses=len(coded_diagnoses),
                matches=len(comp.get("matches", [])),
                discrepancies=len(comp.get("documented_not_coded", [])) + len(comp.get("coded_not_documented", []))
            )

        # ================================================================
        # Complete Review - Mark as Done
        # ================================================================
        update_progress(review_id, 100, "Review complete")
        mark_step_complete(review_id, "Diagnosis Comparison")
        
        review_result = {
            "success": True,
            "review_id": review_id,
            "analysis_id": analysis_id,
            "patient_id": request.patient_id,
            "processing_time_seconds": round(processing_time, 2),
            "documents_analyzed": {
                "notes": len(clinical_notes),
                "vitals": len(vitals),
                "labs": len(labs)
            },
            "clinical_notes": clinical_notes,
            "vitals_data": vitals,
            "labs_data": labs,
            "ai_analysis": {
                "consolidated": consolidated.get("consolidated") if isinstance(consolidated, dict) else None,
                "diagnoses_found": len(ai_diagnoses)
            },
            "coded_diagnoses": coded_diagnoses,
            "comparison": comparison.get("comparison") if isinstance(comparison, dict) else None,
            "recommendations": consolidated.get("consolidated", {}).get("recommendations", []) if isinstance(consolidated.get("consolidated"), dict) else []
        }
        
        complete_review(review_id, review_result)

        return review_result

    except HTTPException:
        fail_review(review_id, str(review_id) if isinstance(review_id, str) else "Unknown error")
        raise
    except Exception as e:
        logger.error(f"Error in review process: {e}", exc_info=True)
        fail_review(review_id, str(e))


@app.post("/api/export")
async def export_results(request: ExportRequest):
    """
    Export analysis results to specified format (DOCX, XLSX, PDF).
    """
    username = get_username()

    try:
        export_dir = project_root / "data" / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"analysis_{request.patient_id}_{timestamp}.{request.format}"
        file_path = export_dir / filename

        if request.format.lower() == "xlsx":
            if not request.payload:
                raise HTTPException(status_code=400, detail="No payload provided for export")

            summary_rows = request.payload.get("summary", [])
            comparison_rows = request.payload.get("comparison", [])
            evidence_rows = request.payload.get("evidence", [])

            with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
                if summary_rows:
                    pd.DataFrame(summary_rows).to_excel(writer, sheet_name="Hospitalization Summary", index=False)
                if comparison_rows:
                    pd.DataFrame(comparison_rows).to_excel(writer, sheet_name="Dx Comparison", index=False)
                if evidence_rows:
                    pd.DataFrame(evidence_rows).to_excel(writer, sheet_name="Daily Evidence", index=False)

        else:
            raise HTTPException(status_code=400, detail="Only XLSX export is implemented now")

        audit_logger.log_export(
            username=username,
            patient_id=request.patient_id,
            export_format=request.format,
            file_path=str(file_path),
            success=True
        )

        return {
            "success": True,
            "message": f"Exported to {request.format.upper()}",
            "file_path": str(file_path)
        }

    except Exception as e:
        logger.error(f"Export error: {e}")
        audit_logger.log_export(
            username=username,
            patient_id=request.patient_id,
            export_format=request.format,
            file_path="",
            success=False,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/audit/statistics")
async def get_audit_statistics():
    """Get audit statistics for the current session."""
    return audit_logger.get_statistics()


@app.get("/api/audit/recent")
async def get_recent_audit_events(count: int = 50, event_type: Optional[str] = None):
    """Get recent audit events."""
    return audit_logger.get_recent_events(count=count, event_type=event_type)


@app.get("/api/queries/recent")
async def get_recent_queries(count: int = 20, query_type: Optional[str] = None):
    """Get recent query logs with full details."""
    return {
        "queries": query_logger.get_recent_queries(count=count, query_type=query_type)
    }


@app.get("/api/queries/failed")
async def get_failed_queries(hours: int = 24):
    """Get failed queries from the last N hours."""
    return {
        "failed_queries": query_logger.get_failed_queries(hours=hours)
    }


@app.get("/api/queries/statistics")
async def get_query_statistics():
    """Get query statistics."""
    return query_logger.get_query_statistics()


@app.get("/api/evaluation/{evaluation_id}/log")
async def get_evaluation_log(evaluation_id: str):
    """Get detailed log for a specific evaluation."""
    return {
        "evaluation_id": evaluation_id,
        "steps": query_logger.get_evaluation_log(evaluation_id)
    }


@app.get("/api/diagnostics")
async def get_diagnostics():
    """Get system diagnostics information."""
    db_test = {"connected": False, "error": None}
    
    # Test database connection
    try:
        test_conn = get_db_connection()
        db_test["connected"] = test_conn.is_connected
        
        if test_conn.is_connected:
            # Try a simple query
            test_query = "SELECT @@VERSION AS SqlVersion, GETDATE() AS CurrentTime"
            test_result = test_conn.execute_query(test_query)
            db_test["test_query_success"] = test_result["success"]
            if test_result["success"] and test_result["rows"]:
                db_test["sql_version"] = test_result["rows"][0].get("SqlVersion", "Unknown")[:100]
                db_test["server_time"] = str(test_result["rows"][0].get("CurrentTime"))
            else:
                db_test["test_query_error"] = test_result.get("error")
    except Exception as e:
        db_test["error"] = str(e)
    
    return {
        "timestamp": datetime.now().isoformat(),
        "database": {
            "configured_server": db_config.get("databases", {}).get("LSV", {}).get("server", "Not configured"),
            "configured_database": db_config.get("databases", {}).get("LSV", {}).get("database", "Not configured"),
            **db_test
        },
        "va_gpt": {
            "initialized": va_gpt_client.is_initialized(),
            "api_key_configured": bool(os.getenv('VA_AI_API_KEY'))
        },
        "audit_logger": {
            "session_id": audit_logger.session_id,
            "log_dir": str(audit_logger.log_dir)
        },
        "query_logger": {
            "query_log_file": str(query_logger.query_log_file),
            "eval_log_file": str(query_logger.eval_log_file),
            "statistics": query_logger.get_query_statistics()
        },
        "configuration": {
            "tables_configured": all([
                db_config.get("tables", {}).get("discharge_table"),
                db_config.get("tables", {}).get("tiu_notes_table"),
                db_config.get("tables", {}).get("vitals_table"),
                db_config.get("tables", {}).get("labs_table"),
                db_config.get("tables", {}).get("ptf_diagnoses_table")
            ]),
            "discharge_table": db_config.get("tables", {}).get("discharge_table"),
            "note_types_configured": bool(db_config.get("note_types", {}).get("admission_notes"))
        }
    }

@app.post("/api/shutdown")
async def shutdown_server():
    """
    Gracefully shut down the application server.

    Responds immediately, then terminates the process shortly after.
    """
    def _shutdown():
        time.sleep(0.5)
        os._exit(0)

    threading.Thread(target=_shutdown, daemon=True).start()
    return {"success": True, "message": "Server is shutting down..."}


# ============================================================================
# Application Startup
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    try:
        logger.info("=" * 60)
        logger.info("Inpatient Documentation and Coding Evaluation")
        logger.info("Starting application...")
        logger.info("=" * 60)
        logger.info("Startup complete")
    except Exception as e:
        logger.error(f"Startup error: {e}", exc_info=True)
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    try:
        global db_connection

        if db_connection:
            db_connection.disconnect()

        audit_logger.log_event(
            event_type="APPLICATION_SHUTDOWN",
            username=get_username(),
            details={}
        )
        logger.info("Shutdown complete")
    except Exception as e:
        logger.error(f"Shutdown error: {e}", exc_info=True)

    logger.info("Application shutdown complete")


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
