# Help & User Guide

## Getting Started

### 1. Patient Selection
- Use the **Discharge Date Range** selector to find patients discharged during a specific period
- Optionally filter by **Treating Specialty** to narrow results
- Click **Search Discharged Patients** to load the patient list

### 2. Running a Review
- Select one or more patients from the list
- Click **Review Hospitalization** to analyze the patient's clinical documentation
- Watch the **progress bar** to see analysis status (may take 15-20 minutes for large admissions)

### 3. Understanding Results

#### Summary Tab
- **Key statistics**: Number of notes, vital signs, and lab values analyzed
- **Overview**: Principal diagnosis and key clinical findings

#### AI Diagnoses Tab
- **AI-detected diagnoses**: Conditions identified by AI analysis of clinical notes
- **Confidence indicators**: Shows how strongly each diagnosis is supported by documentation

#### Coded Diagnoses (PTF) Tab
- **Official coded diagnoses**: ICD-10 codes entered in the Patient Treatment File (PTF)
- **Diagnosis sequence**: Principal diagnosis is listed first
- **Description**: Full text description of each coded diagnosis

#### Comparison Tab
- **Matches**: Diagnoses that appear in both AI analysis and coded diagnoses
- **Documented but not coded**: Conditions in clinical notes but missing from PTF
- **Coded but not documented**: ICD codes in PTF without clear clinical documentation
- **Recommendations**: Suggested coding improvements based on documentation review

### 4. Exporting Results
- Click **Export Results** to save analysis in your preferred format:
  - **Excel (.xlsx)**: For detailed spreadsheet review
  - **Word (.docx)**: For comprehensive reports
  - **PDF**: For archival and sharing
- Files are saved in the `data/exports/` folder

## FAQ

**Q: Why does the review take so long?**
- The clinical notes extraction queries against a large database can take 15-18 minutes. This is normal for comprehensive documentation review.

**Q: What if no notes are found?**
- Some patients may have minimal documentation during their hospital stay. The analysis will proceed with whatever data is available.

**Q: Can I export multiple patients at once?**
- Currently, exports are processed one patient at a time. Select one patient and export before proceeding to the next.

**Q: What do the different tabs contain?**
- **Summary**: Overview statistics
- **AI Diagnoses**: Machine learning analysis results
- **Coded (PTF)**: Official discharge diagnoses codes
- **Comparison**: Gap analysis and recommendations

## Troubleshooting

**Issue**: "No specialties found"
- The database connection may have failed. Refresh the page and try again.

**Issue**: Review seems stuck
- Progress updates every 2-3 seconds. If progress hasn't changed in 5+ minutes, check:
  - Server logs in the terminal
  - Database connectivity
  - Network connection

**Issue**: Export failed
- Ensure the `data/exports` folder exists
- Check that sufficient disk space is available
- Verify the analysis completed successfully before exporting

## Tips for Best Results

1. **Review During Low-Traffic Hours**: Better performance when the clinical data warehouse is less busy
2. **Select Relevant Specialties**: Filtering by specialty can improve result relevance
3. **Verify Clinical Documentation**: Cross-reference AI findings with actual patient notes
4. **Check for Missing Codes**: Pay attention to "Documented but Not Coded" section for coding opportunities
