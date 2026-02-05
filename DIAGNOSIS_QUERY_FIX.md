"""
Build and test the correct diagnosis query with ICD code lookups
"""

# This is the corrected diagnosis query that should be used in app.py
diagnosis_query = """
SELECT
    dd.InpatientDischargeDiagnosisSID,
    dd.InpatientSID,
    dd.PTFIEN,
    dd.OrdinalNumber as DiagnosisSequence,
    COALESCE(ic10.ICD10Code, ic9.ICD9Code, 'UNKNOWN') as ICD10Code,
    COALESCE(ic10.ICD10Description, ic9.ICD9Description, 'Unknown diagnosis') as DiagnosisDescription,
    CASE WHEN dd.ICD10SID IS NOT NULL THEN 'ICD-10' ELSE 'ICD-9' END as DiagnosisCodeType,
    dd.ICD10SID,
    dd.ICD9SID
FROM [Inpat].[InpatientDischargeDiagnosis] dd
LEFT JOIN [Dim].[ICD10Code] ic10 ON dd.ICD10SID = ic10.ICD10SID
LEFT JOIN [Dim].[ICD9Code] ic9 ON dd.ICD9SID = ic9.ICD9SID
WHERE (dd.PTFIEN = ? OR dd.InpatientSID = TRY_CAST(? as bigint))
  AND dd.Sta3n = ?
ORDER BY dd.OrdinalNumber
"""

print("PROPOSED DIAGNOSIS QUERY:")
print("=" * 80)
print(diagnosis_query)
print("\n" + "=" * 80)
print("\nThis query will:")
print("1. Join InpatientDischargeDiagnosis with Dim.ICD10Code using ICD10SID")
print("2. Also join with Dim.ICD9Code using ICD9SID for backward compatibility")
print("3. Use COALESCE to prefer ICD-10 codes but fallback to ICD-9")
print("4. Return ICD10Code (maps to 'icd10' field in app.py)")
print("5. Return DiagnosisDescription (maps to 'description' field)")
print("6. Return DiagnosisSequence from OrdinalNumber (maps to 'sequence' field)")
print("\nThis will replace the current NULL as DiagnosisText with actual diagnosis data.")
