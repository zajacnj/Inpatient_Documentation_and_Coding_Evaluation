# Error Log & Bug Tracking

## Bug #001: Review ID Mismatch - Progress Stuck at "Initializing"

**Status:** FIXED ✅  
**Date Discovered:** February 5, 2026  
**Date Fixed:** February 5, 2026  
**Severity:** CRITICAL  
**Category:** Backend/Frontend Synchronization

---

### Symptom
- UI progress bar stuck on "Initializing review..." for entire review duration (20+ minutes)
- Server logs showed review reaching 100% completion, but UI never transitioned
- UI only updated elapsed time display, never updated progress percentage or status
- Results screen never rendered despite backend processing completing successfully

### Root Cause Analysis
**Location:** `main.py`, function `_run_review_task()` at line ~814

**The Problem:**
When a review is started:
1. `POST /api/review/start` endpoint creates a progress tracker with `review_id="abc123"`
2. Frontend receives review_id and begins polling `/api/review/progress/abc123`
3. Backend spawns `_run_review_task()` as a background task
4. **BUG:** Inside `_run_review_task()`, code was generating a NEW review_id `review_id = str(uuid.uuid4())[:8]`
5. This new review_id was used to create a SECOND progress tracker
6. All `update_progress(review_id, ...)` calls inside the task updated the WRONG tracker
7. Frontend polling the original review_id never saw any progress updates
8. Status remained "processing" forever because the polled tracker was never updated

**Evidence:**
```python
# BEFORE (lines 814-821)
async def _run_review_task(review_id: str, request, ...):
    review_id = str(uuid.uuid4())[:8]  # ❌ OVERWRITES the parameter!
    create_progress_tracker(review_id)   # ❌ Creates SECOND tracker!
    # ...rest of task using wrong review_id
```

---

### Resolution Implemented

**Change Location:** `main.py`, lines 814-821

**Code Change:**
```python
# AFTER (corrected)
async def _run_review_task(review_id: str, request, ...):
    # REMOVED: review_id = str(uuid.uuid4())[:8]
    # REMOVED: create_progress_tracker(review_id)
    # Now uses the review_id passed as parameter
    # Progress tracker was already created in start_review() endpoint
```

**Files Modified:**
- `main.py` - Lines 814-821 (removed duplicate UUID generation and progress tracker init)

**Calling Code (Unchanged, Correct):**
```python
# In POST /api/review/start (line ~1469)
review_id = str(uuid.uuid4())[:8]
create_progress_tracker(review_id)  # Create tracker with this ID
background_tasks.add_task(_run_review_task, review_id, request, ...)
# ✅ review_id is passed as parameter to background task
```

---

### Communication Flow (After Fix)
```
START REVIEW
    ↓
POST /api/review/start
    ├─ Generate: review_id = "abc123"
    ├─ Create: progress_tracker["abc123"] = {status: "processing", ...}
    ├─ Spawn: _run_review_task(review_id="abc123", ...)
    └─ Return: {review_id: "abc123"}
    
FRONTEND POLLING
    ↓
GET /api/review/progress/abc123 every 2 seconds
    └─ Returns: current state from progress_tracker["abc123"]
    
BACKGROUND PROCESSING
    ↓
_run_review_task(review_id="abc123", ...) ← Uses same review_id!
    ├─ Step 1: update_progress("abc123", status="step1_extraction", percent=10)
    │   → progress_tracker["abc123"].status = "step1_extraction"
    │   → progress_tracker["abc123"].percent = 10
    │   └─ Frontend polling sees this ✅
    ├─ Step 2-5: Similar updates...
    └─ Complete: update_progress("abc123", status="complete", percent=100)
        → progress_tracker["abc123"].status = "complete"
        → progress_tracker["abc123"].percent = 100
        → Frontend sees completion, fetches results ✅
```

---

### Testing & Validation

**How to Test (After Server Restart):**
1. Stop the running server (Ctrl+C)
2. Re-run `start_app.bat` to restart with the fix
3. Load application in browser
4. Select a patient and start a review
5. **Verify:**
   - Progress bar shows 0% initially
   - Progress bar updates visibly: 10% → 30% → 45% → 55% → 60% → 70% → 80% → 100%
   - When status reaches "complete", UI transitions to results tabs
   - Results display with "Summary", "AI Diagnoses", "Coded (PTF)", etc. tabs populated
   - No 404 or synchronization errors in browser console

**Expected Behavior:**
- Progress updates should arrive every 2-3 seconds as extraction steps complete
- Total duration varies by patient note volume (typically 2-20 minutes)
- UI remains responsive throughout

---

### Related Issues Fixed in Same Session
- **Favicon 404 Logs:** Added `/favicon.ico` endpoint returning 204 status
- **Empty Results Display:** Added `/api/review/result/{review_id}` endpoint to fetch results only after processing completes
- **Type Errors:** Fixed `normalized_patient_id` parameter in 9+ logging calls in app.py
- **Python-docx Errors:** Removed unsupported `allow_autofit` attribute, cast Path to str in `doc.save()`
- **Markdown Lint Issues:** Fixed 86+ lint errors across 8 documentation files

---

### Code References

**Key Functions:**
- `start_review()` - Creates progress tracker, spawns background task - **main.py ~line 1469**
- `_run_review_task()` - Background worker that processes review - **main.py ~line 814** (FIXED)
- `update_progress()` - Updates progress tracker for given review_id - **main.py ~line 850**
- Frontend polling loop - Checks `/api/review/progress/{review_id}` every 2s - **templates/index.html ~line 1010**

**Related Configuration:**
- Progress polling interval: 2000ms
- Update progress timeout: 300s
- Review timeout: Configuration check in config/database_config.json

---

### Prevention Strategies

To prevent similar bugs in the future:

1. **Parameter Shadowing Prevention:**
   - Code review: Never reassign function parameters
   - Linter: Consider enabling `no-param-reassign` style rule

2. **ID Tracking:**
   - Add logging: `logger.info(f"_run_review_task started with review_id={review_id}")`
   - Verify: Log the ID used in progress_tracker lookups

3. **Testing:**
   - Add unit test: Mock `update_progress()` calls and verify tracker state
   - Add integration test: Start review, poll progress, verify values change
   - Add timeout test: If progress not seen after 30s, test should fail

4. **Monitoring:**
   - Dashboard: Display active review IDs and their progress tracker values
   - Alerts: Alert if progress not updated for >30s after review started

---

### Related Documentation
- See [SESSION_9_COMPLETION_SUMMARY.md](SESSION_9_COMPLETION_SUMMARY.md) for broader context
- See [TECHNICAL.md](TECHNICAL.md) for architecture overview
- See [README_SESSION_9.md](README_SESSION_9.md) for session notes

---

### Communication Log

**Initial Report:**
> "application shows this but application is still processing"  
> "app is stuck on updating visual rather and not allowing progress"  
> "server says review 100% complete. application stuck on just updating elapsed time"

**Root Cause Identified:**
> Backend was updating progress in a different tracker than what the frontend was polling

**User Direction:**
> "Restart the server so the fix is actually running"

---

## Archive

### Environment Details
- **OS:** Windows
- **Python Version:** 3.x
- **Backend:** FastAPI with Uvicorn
- **Database:** SQL Server (VA Clinical Data Warehouse)
- **Browser:** (Test with Chrome/Edge)

### Server Start Command
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Restart Procedure
```powershell
# In PowerShell at project root:
.\start_app.bat           # Spawns new uvicorn process
# Or manually:
Ctrl+C                    # Kill current process
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000  # Start new
```

---

**Last Updated:** February 5, 2026  
**Tracking Status:** CLOSED (Fix Implemented, Awaiting Validation)
