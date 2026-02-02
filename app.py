"""
Inpatient Documentation and Coding Evaluation
Main FastAPI Application

AI-powered evaluation of inpatient clinical documentation against coded diagnoses.
"""

import json
import logging
import os
import getpass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import time

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
audit_logger = AuditLogger(log_dir="logs")
va_gpt_client = VAGPTClient()

# Global database connection (will be initialized on first use)
db_connection: Optional[DatabaseConnection] = None


# ============================================================================
# Pydantic Models
# ============================================================================

class DateRangeRequest(BaseModel):
    start_date: str
    end_date: str


class PatientSelectionRequest(BaseModel):
    patient_ids: List[str]


class ReviewRequest(BaseModel):
    patient_id: str
    admission_id: str


class ExportRequest(BaseModel):
    patient_id: str
    analysis_id: str
    format: str  # docx, xlsx, pdf


# ============================================================================
# Helper Functions
# ============================================================================

def get_username() -> str:
    """Get the current Windows username."""
    return getpass.getuser()


def get_db_connection() -> DatabaseConnection:
    """Get or create database connection."""
    global db_connection

    if db_connection is None or not db_connection.is_connected:
        lsv_config = db_config.get("databases", {}).get("LSV", {})
        if not lsv_config:
            raise HTTPException(status_code=500, detail="Database configuration not found")

        db_connection = DatabaseConnection(
            server=lsv_config.get("server"),
            database=lsv_config.get("database"),
            timeout=lsv_config.get("query_timeout_seconds", 300)
        )

        if not db_connection.connect():
            raise HTTPException(status_code=500, detail="Failed to connect to database")

    return db_connection


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the main application page."""
    return templates.TemplateResponse("index.html", {"request": request})


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

        # TODO: Update this query once discharge table is identified
        # This is a placeholder query structure
        query = """
        -- Placeholder query - needs to be updated with actual discharge table
        -- Expected columns: PatientID, PatientName, AdmissionDate, DischargeDate,
        --                   AdmittingDiagnosis, DischargeDiagnosis, LOS
        SELECT TOP 100
            'PLACEHOLDER' as PatientID,
            'Query needs configuration' as PatientName,
            GETDATE() as AdmissionDate,
            GETDATE() as DischargeDate,
            'N/A' as AdmittingDiagnosis,
            'N/A' as DischargeDiagnosis,
            0 as LOS
        WHERE 1=0  -- Returns no results until configured
        """

        # Once we identify the discharge table, the query will look something like:
        # query = f"""
        # SELECT
        #     p.PatientICN as PatientID,
        #     p.PatientName,
        #     i.AdmitDateTime as AdmissionDate,
        #     i.DischargeDateTime as DischargeDate,
        #     i.AdmittingDiagnosisICD10Code as AdmittingDiagnosis,
        #     i.PrincipalDiagnosisICD10Code as DischargeDiagnosis,
        #     DATEDIFF(day, i.AdmitDateTime, i.DischargeDateTime) as LOS
        # FROM [LSV].[Inpat].[Inpatient] i
        # JOIN [LSV].[Patient].[Patient] p ON i.PatientSID = p.PatientSID
        # WHERE i.DischargeDateTime >= '{request.start_date}'
        #   AND i.DischargeDateTime < '{request.end_date}'
        #   AND i.Sta3n = 626
        # ORDER BY i.DischargeDateTime DESC
        # """

        result = conn.execute_query(query)

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

        return {
            "success": True,
            "patients": result["rows"],
            "count": result["row_count"],
            "date_range": {
                "start": request.start_date,
                "end": request.end_date
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching discharged patients: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
    """
    username = get_username()
    start_time = time.time()

    try:
        conn = get_db_connection()

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
        # TODO: Update with actual TIU query once note titles are identified
        notes_query = """
        -- Placeholder - needs actual TIU table and note title filters
        SELECT TOP 0
            'PLACEHOLDER' as NoteID,
            'Note type' as NoteType,
            GETDATE() as NoteDateTime,
            'Author' as AuthorName,
            'Note text would appear here' as NoteText
        """

        notes_result = conn.execute_query(notes_query)
        clinical_notes = notes_result.get("rows", [])

        # ================================================================
        # Step 2: Extract Vital Signs
        # ================================================================
        # TODO: Update with actual vitals query
        vitals_query = """
        -- Placeholder - needs actual vitals table
        SELECT TOP 0
            'Type' as VitalType,
            0.0 as Value,
            'units' as Units,
            GETDATE() as RecordedDateTime
        """

        vitals_result = conn.execute_query(vitals_query)
        vitals = vitals_result.get("rows", [])

        # ================================================================
        # Step 3: Extract Laboratory Values
        # ================================================================
        # TODO: Update with actual labs query
        labs_query = """
        -- Placeholder - needs actual labs table
        SELECT TOP 0
            'Test' as TestName,
            0.0 as ResultValue,
            'units' as Units,
            GETDATE() as CollectionDateTime,
            'Normal' as AbnormalFlag
        """

        labs_result = conn.execute_query(labs_query)
        labs = labs_result.get("rows", [])

        # ================================================================
        # Step 4: Extract Coded Diagnoses (PTF)
        # ================================================================
        # TODO: Update with actual PTF diagnosis query
        diagnoses_query = """
        -- Placeholder - needs actual PTF diagnosis table
        SELECT TOP 0
            'ICD10' as ICD10Code,
            'Description' as DiagnosisDescription,
            1 as DiagnosisSequence,
            'Y' as POAIndicator
        """

        diagnoses_result = conn.execute_query(diagnoses_query)
        coded_diagnoses = diagnoses_result.get("rows", [])

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

            if analysis.get("success"):
                note_analyses.append({
                    "note_id": note.get("NoteID"),
                    "note_type": note.get("NoteType"),
                    "analysis": analysis.get("analysis")
                })

        # ================================================================
        # Step 6: Consolidate All Analyses
        # ================================================================
        consolidated = va_gpt_client.consolidate_analyses(
            note_analyses=[a.get("analysis") for a in note_analyses if a.get("analysis")],
            patient_info={
                "patient_id": request.patient_id,
                "admission_id": request.admission_id
            }
        )

        # ================================================================
        # Step 7: Compare Against Coded Diagnoses
        # ================================================================
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

        return {
            "success": True,
            "analysis_id": analysis_id,
            "patient_id": request.patient_id,
            "processing_time_seconds": round(processing_time, 2),
            "documents_analyzed": {
                "notes": len(clinical_notes),
                "vitals": len(vitals),
                "labs": len(labs)
            },
            "ai_analysis": {
                "consolidated": consolidated.get("consolidated"),
                "diagnoses_found": len(ai_diagnoses)
            },
            "coded_diagnoses": coded_diagnoses,
            "comparison": comparison.get("comparison"),
            "recommendations": consolidated.get("consolidated", {}).get("recommendations", [])
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in review process: {e}", exc_info=True)

        audit_logger.log_analysis_complete(
            username=username,
            patient_id=request.patient_id,
            analysis_id="ERROR",
            diagnoses_found=0,
            processing_time_seconds=time.time() - start_time,
            success=False,
            error=str(e)
        )

        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/export")
async def export_results(request: ExportRequest):
    """
    Export analysis results to specified format (DOCX, XLSX, PDF).
    """
    username = get_username()

    try:
        # TODO: Implement export functionality
        # This will use python-docx for DOCX, openpyxl/xlsxwriter for XLSX, and reportlab for PDF

        export_dir = project_root / "data" / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"analysis_{request.patient_id}_{timestamp}.{request.format}"
        file_path = export_dir / filename

        # Placeholder - actual export implementation needed
        if request.format == "docx":
            # from docx import Document
            # doc = Document()
            # doc.add_heading('Documentation Analysis Report', 0)
            # doc.save(file_path)
            pass
        elif request.format == "xlsx":
            # import pandas as pd
            # df = pd.DataFrame(...)
            # df.to_excel(file_path, index=False)
            pass
        elif request.format == "pdf":
            # from reportlab.lib.pagesizes import letter
            # from reportlab.pdfgen import canvas
            # c = canvas.Canvas(str(file_path), pagesize=letter)
            # c.save()
            pass

        audit_logger.log_export(
            username=username,
            patient_id=request.patient_id,
            export_format=request.format,
            file_path=str(file_path),
            success=True
        )

        return {
            "success": True,
            "message": f"Export to {request.format.upper()} not yet implemented",
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


@app.get("/api/diagnostics")
async def get_diagnostics():
    """Get system diagnostics information."""
    return {
        "timestamp": datetime.now().isoformat(),
        "database": {
            "connected": db_connection.is_connected if db_connection else False,
            "server": db_config.get("databases", {}).get("LSV", {}).get("server", "Not configured"),
            "database": db_config.get("databases", {}).get("LSV", {}).get("database", "Not configured")
        },
        "va_gpt": {
            "initialized": va_gpt_client.is_initialized(),
            "api_key_configured": bool(os.getenv('VA_AI_API_KEY'))
        },
        "audit_logger": {
            "session_id": audit_logger.session_id,
            "log_dir": str(audit_logger.log_dir)
        },
        "configuration": {
            "tables_configured": all([
                db_config.get("tables", {}).get("discharge_table"),
                db_config.get("tables", {}).get("tiu_notes_table"),
                db_config.get("tables", {}).get("vitals_table"),
                db_config.get("tables", {}).get("labs_table"),
                db_config.get("tables", {}).get("ptf_diagnoses_table")
            ]),
            "note_types_configured": bool(db_config.get("note_types", {}).get("admission_notes"))
        }
    }


# ============================================================================
# Application Startup
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("=" * 60)
    logger.info("Inpatient Documentation and Coding Evaluation")
    logger.info("Starting application...")
    logger.info("=" * 60)

    # Check VA GPT initialization
    if va_gpt_client.is_initialized():
        logger.info("VA GPT client initialized successfully")
    else:
        logger.warning("VA GPT client not initialized - check API key in Key.env")

    # Log startup
    audit_logger.log_event(
        event_type="APPLICATION_START",
        username=get_username(),
        details={"version": "1.0.0"}
    )


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global db_connection

    if db_connection:
        db_connection.disconnect()

    audit_logger.log_event(
        event_type="APPLICATION_SHUTDOWN",
        username=get_username(),
        details={}
    )

    logger.info("Application shutdown complete")


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
