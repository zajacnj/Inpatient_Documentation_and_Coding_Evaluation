# Specialty Filtering - Quick Start Guide

## User Guide

### How to Use the Specialty Filter

1. **Select Date Range**: Choose "Start Date" and "End Date" for discharge date range.

1. **Select Specialties** (Optional).

Specialty options:

- ☑ Medical Observation - Acute care/observation patients
- ☑ Medical - General medical patients
- ☑ Surgical - Surgical patients
- ☑ Psychiatric - Psychiatry patients
- ☑ Rehabilitation - Rehabilitation patients
- ☑ Hospice/Long-term Care - Hospice and long-term care patients

**Leave unchecked** to show all specialties for the date range.

1. **Click "Search Discharged Patients"**: Results will show only patients matching your criteria.

### Examples

| Goal                                  | Steps                                            |
| ------------------------------------- | ------------------------------------------------ |
| Find all observations from Jan 2024   | Select date range + ☑ Medical Observation        |
| Find all surgical cases from Jan 2024 | Select date range + ☑ Surgical                   |
| Find all hospice/LTC from Jan 2024    | Select date range + ☑ Hospice/Long-term Care     |
| Find all medical/surgical cases       | Select date range + ☑ Medical + ☑ Surgical       |
| Find all discharges (any specialty)   | Select date range only (no checkboxes)           |

## Technical Reference

### Files Modified

#### Frontend (User Interface)

- [templates/index.html](templates/index.html)
  - Added specialty filter checkboxes (lines 495-520)
  - Updated searchPatients() function (lines 665-708)

#### Backend (API)

- [app.py](app.py)
  - Updated DateRangeRequest model (lines 84-88) to include specialties parameter
  - Added filtering logic (lines 290-294)

#### Mapping (Unchanged)

- [app/utils/specialty_mapping.py](app/utils/specialty_mapping.py)
  - Maps database codes to display names
  - No changes needed

### How It Works

```text
User Interface
├─ Select dates: Jan 15-20, 2024
├─ Check boxes: Medical, Surgical
└─ Click "Search"
         ↓
JavaScript
├─ Collect: start_date, end_date, specialties=["MEDICAL", "SURGICAL"]
└─ Send POST request to /api/patients/discharged
         ↓
Backend API (app.py)
├─ Receive request with date range and specialties
├─ Query database for all discharges in date range (no specialty filter)
├─ Map specialty codes: "GENERAL(ACUTE MEDICINE)" → "MEDICAL OBSERVATION", etc.
├─ Filter results: keep only patients where specialty ∈ ["MEDICAL", "SURGICAL"]
└─ Return filtered results to UI
         ↓
User Interface
└─ Display patients matching all criteria
```

### Specialty Mappings

Database → Display Name

| Database Code                    | Display Name                                 |
| -------------------------------- | -------------------------------------------- |
| GENERAL(ACUTE MEDICINE)          | Medical Observation                          |
| GENERAL MEDICINE                 | Medical Observation                          |
| (Medicine with 0 LOS)            | Observation                                  |
| NHCU                             | Hospice/Long-term Care                       |
| TCU                              | Hospice/Long-term Care                       |
| (Other specialties)              | Surgical, Psychiatric, Rehabilitation, etc.  |

### API Details

**Endpoint:** `POST /api/patients/discharged`

**Request Body:**

```json
{
  "start_date": "2024-01-15",
  "end_date": "2024-01-20",
  "specialties": ["MEDICAL OBSERVATION", "SURGICAL"]
}
```

**Notes:**

- `specialties` is optional
- If not provided or empty array = show all specialties
- Values must match mapped display names (not database codes)
- Filtering is exact match (case-sensitive)

**Response:**

```json
{
  "success": true,
  "patients": [
    {
      "InpatientSID": 1234,
      "PatientName": "SMITH, JOHN",
      "AdmittingTreatingSpecialty": "MEDICAL OBSERVATION",
      "AdmissionDate": "2024-01-15T08:00:00",
      "DischargeDate": "2024-01-20T14:00:00",
      "LOS": 5,
      ...
    },
    ...
  ],
  "count": 12,
  "date_range": {
    "start": "2024-01-15",
    "end": "2024-01-20"
  }
}
```

## Troubleshooting

### Issue: Checkboxes don't filter results

- **Check:** All specialty filter boxes unchecked? Click "Search" without any boxes selected (shows all).
- **Check:** Did you click "Search Discharged Patients" button after selecting boxes?
- **Check:** Are there actually patients of that specialty in the selected date range?

### Issue: "No patients found" even with boxes checked

- **Possible Cause:** No patients of selected specialty discharged in that date range
- **Solution:** Try a longer date range or different specialty selection

### Issue: Patient shows in results but specialty doesn't match filter

- **Possible Cause:** Specialty mapping changed
- **Solution:** Restart the application

## Testing the Feature

To manually test filtering:

1. Start the app: `py -m uvicorn server:app --reload`
2. Open browser to `http://127.0.0.1:8000`
3. Select dates: Jan 15-20, 2024
4. Search with NO specialty selected → Should see ~100 patients
5. Check only "Medical Observation" → Should see ~15 patients
6. Check "Medical Observation" + "Surgical" → Should see ~30 patients
7. Check box, then uncheck → Verify results update

## Performance Notes

- Filter applied in-memory after results retrieved (list comprehension)
- Suitable for result sets up to several thousand patients
- If filtering becomes slow with large result sets, consider:
  - Adding database-level specialty filtering (requires SQL changes)
  - Pagination of results
  - Search optimization

## Future Enhancements

Possible improvements:

- Save filter preferences for next session
- "Select All" / "Clear All" buttons
- Filter by multiple fields (specialty + diagnosis)
- Specialty-specific documentation requirements display
