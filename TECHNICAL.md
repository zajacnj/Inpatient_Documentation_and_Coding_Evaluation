# Technical Documentation

## System Architecture

### Technology Stack
- **Backend**: FastAPI (Python web framework)
- **Database**: SQL Server (VHACDWRB03.VHA.MED.VA.GOV / CDWWORK)
- **AI**: Azure OpenAI API (GPT-4) for clinical documentation analysis
- **Frontend**: HTML5, JavaScript (vanilla, no frameworks)
- **Export Formats**: Excel (openpyxl), Word (python-docx), PDF (reportlab)

### Core Components

#### 1. Database Connection (`app/database/connection.py`)
- Manages SQL Server connections with Windows Authentication
- Implements connection pooling and retry logic
- Query timeout: 300 seconds for large document extractions
- Executes parameterized queries with type safety

#### 2. Data Extraction (`app.py` - Review Endpoint)
Extracts four main data categories:

**Clinical Notes** (`TIU.TIUDocument`)
- Filters by provider class (clinicians, not nursing staff)
- ~29 provider classes included (PHYSICIAN, RESIDENT, FELLOW, SURGEON, etc.)
- ~10-15 notes per hospitalization expected
- Query time: 15-18 minutes (slow due to large table size)

**Vital Signs** (`Vital.VitalSign`)
- Temperature, blood pressure, heart rate, respiratory rate, O2 saturation
- ~100+ measurements per hospitalization
- Query time: 2-5 seconds

**Laboratory Values** (`Chem.LabChem`)
- Chemistry, hematology, microbiology results
- Includes units and reference ranges
- ~150-200 values per hospitalization
- Query time: 20-30 seconds

**Coded Diagnoses** (`Inpat.InpatientDischargeDiagnosis`)
- ICD-10 and ICD-9 codes from Patient Treatment File (PTF)
- Joins to dimension tables for diagnosis descriptions:
  - `Dim.ICD10DiagnosisVersion` - ICD-10 diagnosis text
  - `Dim.ICD9DiagnosisVersion` - ICD-9 diagnosis text
- Uses `CurrentVersionFlag = 'Y'` for active codes only
- Principal diagnosis (sequence 1) listed first
- ~10-20 diagnoses per hospitalization
- Query time: 5 seconds

#### 3. AI Analysis (`app/ai/va_gpt_client.py`)
- Analyzes clinical notes using Azure OpenAI GPT-4
- Three main operations:
  1. **analyze_clinical_note()** - Single note analysis
  2. **consolidate_analyses()** - Combine all note analyses
  3. **compare_diagnoses()** - Compare AI findings vs coded diagnoses
- Includes context from vitals and labs for clinical accuracy
- Query time: 2-3 minutes for typical admission

#### 4. Progress Tracking
- Real-time progress updates via `/api/review/progress/{review_id}` endpoint
- 9 progress checkpoints (5% → 100%)
- Global in-memory tracking dictionary
- Frontend polls every 2-3 seconds for updates

#### 5. Logging & Audit (`app/logging/`)
- **AuditLogger** - Compliance logging (who, what, when)
- **QueryLogger** - Database query performance tracking
- Session-based logging with unique session IDs
- Sanitizes PII before logging query results

#### 6. Export Functionality
- Converts analysis results to three formats:
  - **Excel**: Tabular data with multiple sheets
  - **Word**: Formatted report with summaries
  - **PDF**: Professional document suitable for archival

## Key Tables & Schemas

### TIU Schema (Clinical Notes)
```sql
TIU.TIUDocument
├── SignedByStaffSID (links to Staff.Staff for provider info)
├── ReferenceDateTime (when note was created)
├── TIUDocumentDefinitionSID (links to Dim.TIUDocumentDefinition for note type)
└── SignedDateTime (when note was finalized)
```

### Inpat Schema (Admissions)
```sql
Inpat.Inpatient
├── InpatientSID (unique admission identifier)
├── PatientSID (links to SPatient.SPatient for demographics)
├── PTFIEN (Patient Treatment File identifier)
├── AdmitDateTime / DischargeDateTime
├── PrincipalDiagnosisICD10SID (primary diagnosis code)
└── SpecialtyTransfer (tracks ward/unit movements)

Inpat.InpatientDischargeDiagnosis
├── InpatientSID (links to Inpatient.Inpatient)
├── OrdinalNumber (sequence: 1=principal, 2+=secondary)
├── ICD10SID (links to Dim.ICD10)
└── ICD9SID (links to Dim.ICD9)
```

### Vital Schema
```sql
Vital.VitalSign
├── PatientSID
├── VitalSignTakenDateTime
├── VitalType (temperature, BP, HR, RR, O2 sat, etc.)
├── VitalResult (numeric value)
└── VitalTypeSID (links to Dim.VitalType)
```

### Chem Schema (Labs)
```sql
Chem.LabChem
├── PatientSID
├── LabChemSpecimenDateTime
├── LabChemProcedure (test name)
├── ResultValue / Units / ReferenceRange
└── LabChemSID
```

### Dimension Tables
```sql
Dim.ICD10 / Dim.ICD9
└── ICD10Code / ICD9Code (e.g., "C34.11", "250.00")

Dim.ICD10DiagnosisVersion / Dim.ICD9DiagnosisVersion
├── ICD10Diagnosis / ICD9Diagnosis (full description)
└── CurrentVersionFlag = 'Y' (currently active)

Dim.TreatingSpecialty
└── Specialty (surgical, medical, etc.)

Staff.Staff
└── ProviderClass (PHYSICIAN, PHYSICIAN ASSISTANT, NURSE, etc.)
```

## API Endpoints

### Review Endpoints
```
POST /api/review/start
  ├─ Accepts: patient_id, admission_id
  ├─ Returns: review_id, analysis results
  └─ Time: 18-20 minutes

GET /api/review/progress/{review_id}
  ├─ Returns: status, percentage, current_step, elapsed_seconds
  └─ Time: <100ms
```

### Export Endpoints
```
POST /api/export
  ├─ Accepts: patient_id, format (xlsx/docx/pdf), payload
  ├─ Returns: file_path, success message
  └─ Time: 5-30 seconds depending on format
```

### Utility Endpoints
```
GET /api/specialties          - List available treating specialties
POST /api/patients/discharged - Search discharged patients by date range
GET /api/diagnostics          - System health check
```

## Performance Characteristics

| Operation | Duration | Notes |
|-----------|----------|-------|
| Notes Extraction | 15-18 min | Bottleneck; large table size |
| Vitals Extraction | 2-5 sec | Very fast; indexed table |
| Labs Extraction | 20-30 sec | Moderate; many lab results |
| Diagnoses Extraction | 5 sec | Dimension joins quick |
| AI Analysis | 2-3 min | API calls to Azure OpenAI |
| Diagnosis Comparison | 1-2 sec | In-memory operation |
| Export (Excel) | 5-10 sec | Fast; tabular format |
| Export (Word) | 10-20 sec | Moderate; formatting |
| Export (PDF) | 20-30 sec | Slowest; rendering |

## Deployment Notes

### Required Environment Variables
- `AZURE_OPENAI_KEY` - Azure OpenAI API key
- `AZURE_OPENAI_ENDPOINT` - Azure OpenAI endpoint URL
- `AZURE_OPENAI_DEPLOYMENT` - GPT-4 deployment name (default: gpt-4o)

### Database Requirements
- Windows Authentication (must run on VA network)
- Access to VHACDWRB03 Clinical Data Warehouse
- Minimum query timeout: 300 seconds
- VPN required if external to VA network

### Hardware Recommendations
- **CPU**: 4+ cores recommended
- **RAM**: 8GB minimum, 16GB+ recommended
- **Disk**: 100GB+ for database operations and exports
- **Network**: Stable VA network connection

### Scaling Considerations
- Currently single-instance, blocking API design
- Future: Implement async background processing with Celery/RQ
- Future: Add caching for frequently accessed patients
- Future: Implement pagination for large result sets
