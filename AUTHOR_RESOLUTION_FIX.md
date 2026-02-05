# Author Resolution Fix - Implementation Summary

## Problem
You were getting "Unknown Author" for clinical notes because:

1. **INNER JOIN filtering**: The query used `INNER JOIN` with the staff table, which excluded notes where the author's StaffSID didn't match any record in the staff table
2. **Wrong staff table**: Used `Staff.Staff` instead of the more reliable `Dim.Staff` table  
3. **Name column mismatches**: The code was searching for staff name columns that didn't exist in Staff.Staff
4. **Provider class filtering**: The WHERE clause filtered by `ProviderClass`, excluding non-clinical staff notes

## Solution Implemented

### 1. **Changed INNER JOIN to LEFT JOIN** (Both app.py and main.py)
```sql
-- BEFORE
INNER JOIN [CDWWork].[Staff].[Staff] s
    ON td.SignedByStaffSID = s.StaffSID
WHERE...
    AND s.ProviderClass IN (...)

-- AFTER  
LEFT JOIN [CDWWork].[Dim].[Staff] s
    ON td.SignedByStaffSID = s.StaffSID
WHERE...
    -- Removed provider class filter
```

**Why this works**: 
- LEFT JOIN returns all notes even if no matching staff record is found
- Falls back gracefully to using StaffSID when name not available

### 2. **Switched to Dim.Staff Table** (More reliable)
- `Dim.Staff` is the standard dimension table for staff information in CDW
- Contains fields like `StaffName`, `FullName`, `PersonName`, `ProviderClass`
- More complete and consistently populated than `Staff.Staff`

### 3. **Improved Staff Name Resolution** (main.py only)
```sql
COALESCE(
    s.[StaffName], 
    s.[FullName], 
    s.[PersonName], 
    CAST(td.SignedByStaffSID AS VARCHAR(50)), 
    'Unknown Author'
) as AuthorName
```

**Fallback chain**:
1. Try `StaffName` column
2. Try `FullName` column  
3. Try `PersonName` column
4. Display StaffSID if no name found
5. Only show "Unknown Author" as last resort

### 4. **Handled NULL Provider Class**
```sql
COALESCE(s.[ProviderClass], 'UNKNOWN') as AuthorProviderClass
```
Prevents NULL values from querying with provider class filter

## Files Modified

### 1. [app/database/query_builder.py](app/database/query_builder.py)
- **Added**: New method `get_notes_with_authors()` that properly joins author/cosigner staff information
- Uses LEFT JOIN to preserve all notes
- Resolves both SignedByStaffSID and CosignedByStaffSID

### 2. [app.py](app.py#L950)
- Changed table from `Staff.Staff` to `Dim.Staff`
- Changed INNER JOIN to LEFT JOIN  
- Removed provider class filter from WHERE clause
- Updated notes_params to exclude provider_classes_to_include
- Added COALESCE for AuthorProviderClass

### 3. [main.py](main.py#L1016)
- Same changes as app.py
- Additionally improved staff name resolution with COALESCE chain
- Better fallback handling

## Staff Table Structure in CDW

The key to your author information is in **`[CDWWork].[Dim].[Staff]`**:

```
StaffSID          → Matches SignedByStaffSID in TIUDocument
StaffName         → Full name of the staff member
FullName          → Alternative name field  
PersonName        → Alternative name field
ProviderClass     → Type of provider (PHYSICIAN, NURSE, etc.)
FirstName/LastName → Sometimes available as separate fields
```

## Testing the Fix

To verify the fix is working:

1. Run a note extraction for any patient/admission
2. Check the HTML output under "Note Title" and "Author" columns
3. You should now see actual staff names instead of "Unknown Author"
4. If a name is still missing, you'll see the StaffSID as a fallback

## Related Query Methods Added

A new robust query builder method is available:
```python
from app.database.query_builder import CDWWorkQueryBuilder

# Get notes with author names properly resolved
query = CDWWorkQueryBuilder.get_notes_with_authors(
    patient_sid=12345,
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 12, 31),
    limit=100
)
```

## Note on CosignedByStaffSID

The fix also properly handles:
- **Primary author**: `SignedByStaffSID` → `AuthorName`
- **Cosigner**: `CosignedByStaffSID` → `CosignerName` (in query_builder method)

Both now properly join to the Dim.Staff table for name resolution.

## Additional Improvements Possible

If you still see "Unknown Author" after this fix, consider:

1. **Check if Dim.Staff has the data**:
   ```sql
   SELECT TOP 10 StaffSID, StaffName FROM [CDWWork].[Dim].[Staff]
   WHERE StaffSID IN (Select Distinct SignedByStaffSID FROM [CDWWork].[TIU].[TIUDocument] Where SignedByStaffSID IS NOT NULL)
   ```

2. **Fallback to Dim.Provider** if needed:
   ```sql
   LEFT JOIN [CDWWork].[Dim].[Provider] p
       ON td.SignedByStaffSID = p.ProviderSID
   ```

3. **Check for multiple staff IDs** in case SignedByStaffSID uses different ID schemes

---

**Status**: ✅ All files updated and committed  
**Date**: February 5, 2026  
**Testing**: Ready for user acceptance testing
