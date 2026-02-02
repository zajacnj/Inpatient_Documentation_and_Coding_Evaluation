# Inpatient Documentation and Coding Evaluation

AI-powered evaluation of inpatient clinical documentation against coded diagnoses (ICD-10) in the Patient Transfer File (PTF).

## Overview

This application helps evaluate whether the best diagnoses have been documented in clinical notes during hospital admissions. It:

1. **Extracts** clinical documentation (TIU notes), vital signs, and laboratory values for a hospitalization
2. **Analyzes** the documentation using VA GPT to identify documented and implied diagnoses
3. **Compares** AI-extracted diagnoses against the actual ICD-10 codes in PTF
4. **Reports** discrepancies and opportunities for documentation improvement

## Features

- Date-based patient selection for discharged patients
- Extraction of multiple clinical note types:
  - Admission notes
  - Progress notes
  - Attending notes and addendums
  - Consult notes
- Integration of vital signs and laboratory values for context
- AI-powered diagnosis extraction with confidence scoring
- Comparison against PTF coded diagnoses
- Export to DOCX, Excel, and PDF formats
- Comprehensive audit logging

## Prerequisites

- Python 3.9+
- ODBC Driver 17 for SQL Server
- Access to VA CDW (LSV database)
- VA GPT API key

## Installation

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate: `venv\Scripts\activate` (Windows)
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.template` to `Key.env` and add your VA GPT API key
6. Configure database tables in `config/database_config.json`

## Configuration Required

Before using the application, you need to identify and configure:

### Database Tables (in config/database_config.json)
- Discharge table: Table containing inpatient admissions and discharges
- TIU notes table: Table containing clinical documentation
- Vitals table: Table containing vital signs
- Labs table: Table containing laboratory results
- PTF diagnoses table: Table containing coded ICD-10 diagnoses

### Note Types
- Admission note titles/IENs
- Progress note titles/IENs
- Attending note titles/IENs
- Consult note titles/IENs

## Usage

1. Start: `python app.py`
2. Open browser to http://127.0.0.1:8000
3. Select date range for discharged patients
4. Select a patient
5. Click "Review Hospitalization"
6. Review results and export as needed

## Technology Stack

- Backend: FastAPI (Python)
- Database: SQL Server (CDW/LSV) with Windows Authentication
- AI: VA GPT (Azure OpenAI)
- Frontend: HTML/CSS/JavaScript

## License

Internal VA use only.
