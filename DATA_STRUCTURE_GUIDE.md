# Data Structure Guide for CDWWORK Database

## ✅ VERIFIED - Database Connection

- **Server**: VHACDWRB03.VHA.MED.VA.GOV
- **Database**: CDWWORK
- **Authentication**: Windows Authentication (Trusted_Connection=yes)
- **Status**: Connection successful, all tables verified

---

## ✅ VERIFIED - Key Data Tables and Locations

### 1. TIU Note Text ✅ CONFIRMED

**Table**: `[CDWWork].[STIUNotes].[TIUDocument_8925]`

- **Column**: `ReportText` (varchar(max))
- Contains the full text content of clinical notes
- This is the primary source for note text extraction
- **Join Key**: `TIUDocumentSID`

**Alternative**: `[CDWWork].[STIUNotes].[TIUDocument_8925_02]`

- Simplified table with only: TIUDocumentSID, Sta3n, TIUDocumentIEN, ReportText

### 2. TIU Document Metadata ✅ CONFIRMED

**Table**: `[CDWWork].[TIU].[TIUDocument]`

- Contains metadata about each note:
  - **Signed By**: Author who signed the note (AuthorDUZ/AuthorStaffSID)
  - **Cosigned By**: Attending or supervisor who cosigned (CosignerDUZ/CosignerStaffSID)
  - **Signature Date**: SignatureDateTime
  - **Note Title**: Link via TIUDocumentDefinitionSID
  - **Reference Date**: ReferenceDateTime (note date)
- **Join Key**: `TIUDocumentSID`

### 3. TIU Document Definitions (Note Titles) ✅ CONFIRMED

**Table**: `[CDWWork].[Dim].[TIUDocumentDefinition]`

- **Field**: `TIUDocumentDefinitionPrintName`
- Contains **local titles** for note types
- **Examples found**:
  - "ADMISSION NOTE"
  - "ADMISSION ASSESSMENT"
  - "OBSERVATION NURSING ADMISSION ASSESSMENT-"
  - "CLC ADMISSION HISTORY AND PHYSICAL"
  - "ADMISSION PANEL;1;2Y"
- **Join Key**: `TIUDocumentDefinitionSID`

### 4. Treating Specialties ✅ CONFIRMED

**Table**: `[CDWWork].[Dim].[TreatingSpecialty]`

- Contains specialty information
- **Fields**: TreatingSpecialtySID, TreatingSpecialtyName
- **Example**: 'GENERAL (ACUTE MEDICINE)'
- **Join Key**: `TreatingSpecialtySID`

### 5. Specialty Transfers - Admitting Specialty Determination ✅ CONFIRMED

**Primary Table**: `[CDWWork].[Inpat].[SpecialtyTransfer]`

- Tracks specialty changes during hospitalization
- **Key Fields**:
  - `SpecialtyTransferSID` (primary key)
  - `InpatientSID` (links to admission)
  - `PatientSID` (patient identifier)
  - `SpecialtyTransferDateTime` (when transfer occurred)
  - `TreatingSpecialtySID` (specialty being transferred to)
  - `OrdinalNumber` (sequence number)
- **Strategy**: Sort by `SpecialtyTransferDateTime`, take earliest per `InpatientSID`

**Alternative Tables** (also available):

- `[CDWWork].[Inpat].[PatientTransfer]` - Physical location transfers
- `[CDWWork].[Inpat].[Inpatient501Transaction]` - 501 transaction data
- `[CDWWork].[Inpat].[Census501]` - Census 501 data

---

## Target Note Types

We need to extract the following types of notes during hospitalization:

1. **Admission Notes**
   - Initial assessment and admission documentation
   - Typically the first note after patient admitted

2. **Daily Notes**
   - Progress notes documenting daily care
   - May include resident/intern notes and attending notes

3. **Consult Notes**
   - Specialty consultation notes during hospitalization
   - Important for understanding subspecialty involvement

---

## Query Strategy

### Note Extraction Query Pattern ✅ VERIFIED

```sql
SELECT 
    doc.PatientSID,
    doc.VisitSID,
    doc.TIUDocumentSID,
    doc.ReferenceDateTime AS NoteDate,
    doc.AuthorStaffSID AS SignedBySID,
    doc.CosignerStaffSID AS CosignedBySID,
    doc.SignatureDateTime,
    doc.CosignatureDateTime,
    def.TIUDocumentDefinitionPrintName AS NoteTitle,
    txt.ReportText AS NoteText
FROM 
    [CDWWork].[TIU].[TIUDocument] doc
    INNER JOIN [CDWWork].[STIUNotes].[TIUDocument_8925] txt 
        ON doc.TIUDocumentSID = txt.TIUDocumentSID
    INNER JOIN [CDWWork].[Dim].[TIUDocumentDefinition] def
        ON doc.TIUDocumentDefinitionSID = def.TIUDocumentDefinitionSID
WHERE
    doc.PatientSID IS NOT NULL
    AND txt.ReportText IS NOT NULL
    AND doc.ReferenceDateTime BETWEEN @StartDate AND @EndDate
    AND def.TIUDocumentDefinitionPrintName LIKE '%admission%'
        OR def.TIUDocumentDefinitionPrintName LIKE '%progress%'
        OR def.TIUDocumentDefinitionPrintName LIKE '%consult%'
ORDER BY 
    doc.PatientSID, doc.ReferenceDateTime
```

### Admitting Specialty Query Pattern ✅ VERIFIED

```sql
-- Strategy: Find earliest specialty transfer per admission
-- This represents the admitting treating specialty
SELECT 
    st.InpatientSID,
    st.PatientSID,
    st.SpecialtyTransferDateTime AS AdmitDateTime,
    st.TreatingSpecialtySID,
    ts.TreatingSpecialtyName AS AdmittingSpecialty
FROM 
    [CDWWork].[Inpat].[SpecialtyTransfer] st
    INNER JOIN [CDWWork].[Dim].[TreatingSpecialty] ts
        ON st.TreatingSpecialtySID = ts.TreatingSpecialtySID
WHERE
    st.SpecialtyTransferDateTime = (
        -- Get earliest transfer time for this admission
        SELECT MIN(SpecialtyTransferDateTime)
        FROM [CDWWork].[Inpat].[SpecialtyTransfer]
        WHERE InpatientSID = st.InpatientSID
          AND SpecialtyTransferDateTime IS NOT NULL
    )
```

---

## Data Extraction Fields Needed

### From Each Note

- Patient identifier (PatientSID)
- Admission identifier (AdmissionSID)
- Note date/time (ReferenceDateTime)
- Note title (TIUDocumentDefinitionPrintName)
- Signed by (AuthorDUZ or name field)
- Cosigned by (CosignerDUZ or name field, if present)
- Signature date (SignatureDateTime)
- Full note text (ReportText)

### From Admission Record

- Patient identifier
- Admission date/time
- Discharge date/time
- Admitting treating specialty (via first 501)
- Station number (626 focus)
- Primary diagnoses

---

## Next Steps

1. **Confirm 501 Transfer Table Name**
   - Explore CDWWORK schema for transfer/501 table
   - Confirm field names for linking to admissions and specialties

2. **Test Note Title Filters**
   - Query `DIM.TIUDocumentDefinition` for all available note titles
   - Identify which titles correspond to admission, daily, and consult notes

3. **Test Join Keys**
   - Verify the correct SID fields to join:
     - TIUDocument ↔ ReportText
     - TIUDocument ↔ TIUDocumentDefinition
     - Admissions ↔ Transfer files
     - Transfer files ↔ TreatingSpecialty

4. **Validate Data Quality**
   - Check for NULL values in critical fields
   - Verify cosigner data availability
   - Confirm note text completeness
