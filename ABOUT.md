# About Inpatient Documentation & Coding Evaluation System

## Purpose

This application analyzes clinical documentation from VA patient hospitalizations to identify discrepancies between:
- **Clinical Findings** - What providers documented in their notes
- **Coded Diagnoses** - What was officially assigned and billed (ICD-10/ICD-9 codes)

Healthcare coding compliance is a critical patient safety and financial accuracy issue. This system uses AI to:
1. Identify diagnoses clinicians documented but did not formally code
2. Flag coded diagnoses without corresponding clinical documentation
3. Recommend corrections to improve documentation completeness

## Key Features

### 1. Multi-Source Clinical Data Integration
- **Clinical Notes**: Analysis of physician, resident, and specialist documentation
- **Vital Signs**: Temperature, BP, heart rate, respiratory rate, O2 saturation
- **Laboratory Results**: Chemistry, hematology, microbiology tests with reference ranges
- **Coded Diagnoses**: Patient Treatment File (PTF) diagnoses with ICD-10/ICD-9 codes

### 2. AI-Powered Analysis
- Uses Azure OpenAI (GPT-4) to extract diagnoses from unstructured clinical notes
- Performs automated comparison between clinical findings and official codes
- Generates recommendations for coding improvements

### 3. Real-Time Progress Tracking
- Live progress indicator during patient review (9 checkpoint steps)
- Estimated completion time based on extraction rates
- Detailed step-by-step status messages

### 4. Comprehensive Reporting
- **Summary Tab**: Overview of extracted data (notes, vitals, labs, diagnoses)
- **AI Diagnoses Tab**: Findings from clinical documentation analysis
- **PTF Diagnoses Tab**: Official coded diagnoses from billing records
- **Comparison Tab**: Side-by-side alignment showing:
  - Diagnoses documented AND coded (matches)
  - Documented NOT coded (potential compliance gaps)
  - Coded NOT documented (potential false billing)
- **Recommendations Tab**: Suggested corrective actions

### 5. Export Capabilities
- **Excel Format**: Structured data in spreadsheets for analysis
- **Word Format**: Professional report document for clinician review
- **PDF Format**: Archival-ready format for records management

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Web Frontend (HTML/JS)                     │
│                   - Patient selection                        │
│                   - Real-time progress display              │
│                   - Results visualization                    │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP/REST API
┌──────────────────────────▼──────────────────────────────────┐
│              FastAPI Backend (Python)                        │
│              - Data extraction orchestration                 │
│              - AI analysis coordination                      │
│              - Export formatting                            │
└──────────────────────────┬──────────────────────────────────┘
                           │ Parameterized SQL Queries
┌──────────────────────────▼──────────────────────────────────┐
│         SQL Server Clinical Data Warehouse (CDW)             │
│         - TIU Clinical Notes                                 │
│         - Vital Signs                                        │
│         - Laboratory Results                                 │
│         - Discharge Diagnoses (PTF)                         │
│         - Dimension Tables (diagnosis codes/descriptions)    │
└─────────────────────────────────────────────────────────────┘
```

## Clinical Use Cases

### 1. Documentation Quality Audit
**Scenario**: Quality improvement department conducts quarterly compliance review

**Usage**:
1. Select discharged patient from date range
2. System extracts all clinical data and analyzes it
3. Review identifies:
   - Sepsis documented but not coded
   - Hypertension coded but not mentioned in final diagnosis
   - Congestive heart failure with incomplete documentation
4. Export report for physician review and corrective feedback

### 2. Coder Training & Validation
**Scenario**: Medical coding supervisor verifies coder accuracy

**Usage**:
1. Run analysis on patient coded by trainee
2. Compare AI diagnoses against coder's selection
3. Identify over-coding, under-coding, or missed diagnoses
4. Use report to provide constructive feedback

### 3. Post-Discharge Clinician Review
**Scenario**: Attending physician completes final documentation review

**Usage**:
1. After discharge, run system on patient's full record
2. Review AI-extracted diagnoses from own notes
3. Verify all significant conditions properly coded
4. Add corrections or additional diagnoses as needed

### 4. Revenue Cycle Management
**Scenario**: Finance reviews potential claim compliance issues

**Usage**:
1. Identify patients with significant undercoding (documented not coded)
2. Route to clinical documentation improvement (CDI) team
3. Quantify financial impact of missing diagnoses
4. Track quality metrics over time

## Technical Specifications

### Supported Patients
- Discharged VA inpatients
- Must have clinical notes, vital signs, or lab data
- Supports both ICD-10 and ICD-9 coded diagnoses

### Data Extraction Scope
- **Notes**: All clinical documentation from admission to discharge
- **Vitals**: All recorded vital signs during hospitalization
- **Labs**: All chemistry, hematology, and microbiology results
- **Diagnoses**: All coded diagnoses from discharge summary

### Processing Time
- **Typical Admission**: 18-22 minutes
  - Notes extraction: 15-18 minutes (slowest step)
  - Vitals extraction: 2-5 seconds
  - Labs extraction: 20-30 seconds
  - AI analysis: 2-3 minutes
  - Comparison: 1-2 seconds

### Data Security & Compliance
- **Authentication**: Windows domain authentication (VA network)
- **Access Control**: User account must have CDW database access
- **Audit Logging**: All reviews logged with timestamp and user ID
- **PII Handling**: Names/SSNs used only for clinical context, sanitized in logs
- **HIPAA**: Operates within VA enterprise security controls

## Version History

| Version | Release Date | Key Features |
|---------|--------------|--------------|
| 2.0 | Current | AI diagnosis extraction, real-time progress, multi-format export |
| 1.5 | Previous | Manual diagnosis comparison, Excel export only |
| 1.0 | Initial | Basic data extraction, static reports |

## System Requirements

### Client (Web Browser)
- Modern browser (Chrome, Edge, Firefox, Safari)
- JavaScript enabled
- Broadband connection to VA network

### Server (Deployment)
- Windows Server with SQL Server access
- Python 3.9+
- 8GB+ RAM recommended
- VA network connectivity or VPN

### Database
- SQL Server 2016+ (CDW infrastructure)
- Windows authentication capability
- Query timeout: 300+ seconds

## Future Enhancements

1. **Async Processing**: Background processing for faster UI responsiveness
2. **Historical Trending**: Compare coding patterns over multiple admissions
3. **Recommendation Automation**: Auto-suggest corrections based on guidelines
4. **Integration Hooks**: Send findings directly to EHR documentation improvement workflow
5. **Advanced Analytics**: Department-level and facility-level quality metrics dashboard
6. **Mobile Support**: Responsive design for tablet/mobile clinician review
7. **Multilingual Support**: Documentation in Spanish and other VA patient languages

## Contact & Support

For issues, questions, or enhancement requests:
- **Technical Issues**: VA Informatics Team
- **Clinical Questions**: Hospital Quality Improvement Department
- **Data Access Issues**: VA Network Administration

## Disclaimer

This system is designed to support clinical documentation review and should not replace professional judgment. All recommendations require clinical validation by qualified healthcare providers. System findings are advisory only and do not constitute official diagnoses or medical opinions.

All patient data remains confidential and protected under HIPAA and VA security policies.
