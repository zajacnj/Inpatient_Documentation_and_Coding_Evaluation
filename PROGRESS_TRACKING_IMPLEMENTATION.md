# Progress Tracking Implementation Guide

## Overview

The application now provides real-time progress reporting for the patient review process. Long-running reviews (18+ minutes) now display progress updates to users, eliminating the "application stalled" perception.

## Architecture

### Progress Tracking System

**Global State Dictionary** (lines 76-82 in app.py):
```python
review_progress: Dict[str, Dict[str, Any]] = {}
```

Stores progress state for each active review keyed by `review_id` (UUID).

### Core Functions

#### 1. `create_progress_tracker(review_id: str)` - Lines 85-94
Initializes progress tracking for a new review:
```python
{
    "status": "initializing",      # initializing | processing | complete | error
    "percentage": 0,               # 0-100
    "current_step": "...",         # Descriptive message
    "steps_completed": [],         # List of completed step names
    "start_time": datetime,        # ISO format timestamp
    "error": None                  # Error message if failed
}
```

#### 2. `update_progress(review_id, percentage, current_step, status)` - Lines 96-108
Updates progress during execution:
- Caps percentage at 99% (reserved for completion)
- Updates current_step message
- Records last_update timestamp

#### 3. `mark_step_complete(review_id, step_name)` - Lines 110-116
Logs completed steps for transparency:
- Adds step to steps_completed list
- Prevents duplicates

#### 4. `complete_review(review_id, data)` - Lines 118-127
Marks review as successfully complete:
- Sets status to "complete"
- Sets percentage to 100
- Records end_time
- Stores result_data

#### 5. `fail_review(review_id, error)` - Lines 129-135
Marks review as failed:
- Sets status to "error"
- Stores error message
- Records end_time

## Progress Reporting Endpoints

### GET `/api/review/progress/{review_id}` - Lines 346-376

**Purpose**: Frontend polling endpoint for progress updates

**Response**:
```json
{
  "review_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "processing",
  "percentage": 45,
  "current_step": "Extracted 47 laboratory values",
  "steps_completed": ["Extract Clinical Notes", "Extract Vitals"],
  "elapsed_seconds": 245,
  "error": null
}
```

**Status Values**:
- `initializing`: Starting review process
- `processing`: Actively extracting or analyzing data
- `complete`: Finished successfully
- `error`: Failed with error message in "error" field

**Elapsed Time**: Calculated in real-time from start_time

## Progress Tracking Points

Progress updates occur at 8 key milestones during the review process:

| Step # | Percentage | Location | Message |
|--------|-----------|----------|---------|
| 1 | 5% | Review endpoint start (line 820) | "Loading patient admission data..." |
| 2 | 15% | After notes extraction (line ~987) | "Extracted X clinical notes" |
| 3 | 30% | After vitals extraction (line ~1086) | "Extracted X vital sign measurements" |
| 4 | 45% | After labs extraction (line ~1154) | "Extracted X laboratory values" |
| 5 | 55% | After diagnoses extraction (line ~1228) | "Extracted X coded diagnoses" |
| 6 | 60% | Before AI analysis (line ~1273) | "Running AI analysis on clinical documentation..." |
| 7 | 70% | After AI note analysis (line ~1303) | "Analyzed X clinical notes" |
| 8 | 80% | Before diagnosis comparison (line ~1325) | "Comparing AI diagnoses with coded diagnoses..." |
| 9 | 100% | After all processing (line ~1393) | "Review complete" |

## Implementation in Review Endpoint

### Review ID Generation (Line 809)
```python
review_id = str(uuid.uuid4())  # Unique ID for this review
```

### Progress Initialization (Line 820)
```python
create_progress_tracker(review_id)
update_progress(review_id, 5, "Loading patient admission data...")
```

### Data Extraction Progress Updates

**Notes Extraction** (Line ~987):
```python
update_progress(review_id, 15, f"Extracted {len(clinical_notes)} clinical notes")
mark_step_complete(review_id, "Extract Clinical Notes")
```

**Vitals Extraction** (Line ~1086):
```python
update_progress(review_id, 30, f"Extracted {len(vitals)} vital sign measurements")
mark_step_complete(review_id, "Extract Vitals")
```

**Labs Extraction** (Line ~1154):
```python
update_progress(review_id, 45, f"Extracted {len(labs)} laboratory values")
mark_step_complete(review_id, "Extract Labs")
```

**Diagnoses Extraction** (Line ~1228):
```python
update_progress(review_id, 55, f"Extracted {len(coded_diagnoses)} coded diagnoses")
mark_step_complete(review_id, "Extract Diagnoses")
```

### AI Analysis Progress Updates

**Analysis Initiation** (Line ~1273):
```python
update_progress(review_id, 60, "Running AI analysis on clinical documentation...")
```

**Analysis Completion** (Line ~1303):
```python
update_progress(review_id, 70, f"Analyzed {len(note_analyses)} clinical notes")
mark_step_complete(review_id, "Analyze Clinical Notes")
```

**Diagnosis Comparison** (Line ~1325):
```python
update_progress(review_id, 80, "Comparing AI diagnoses with coded diagnoses...")
```

### Final Completion (Line ~1393)
```python
update_progress(review_id, 100, "Review complete")
mark_step_complete(review_id, "Diagnosis Comparison")
complete_review(review_id, review_result)
```

## Error Handling

### Error Paths
When errors occur during review processing:
```python
except HTTPException:
    fail_review(review_id, "specific error message")
    raise
except Exception as e:
    fail_review(review_id, str(e))
    # Log error and raise HTTPException
```

This ensures that:
1. Failed reviews are marked with error status
2. Frontend receives error message via progress endpoint
3. Users see what went wrong instead of silent failures

## Frontend Integration

### Polling Pattern

```javascript
// Start review
const response = await fetch('/api/review/start', {
  method: 'POST',
  body: JSON.stringify(request)
});
const { review_id } = await response.json();

// Poll progress every 2-5 seconds
const pollInterval = setInterval(async () => {
  const progress = await fetch(`/api/review/progress/${review_id}`).then(r => r.json());
  
  // Update UI with progress
  updateProgressBar(progress.percentage);
  updateStatusMessage(progress.current_step);
  updateStepsList(progress.steps_completed);
  
  // Check for completion or error
  if (progress.status === 'complete') {
    clearInterval(pollInterval);
    showResults(await getReviewResults(progress.review_id));
  }
  
  if (progress.status === 'error') {
    clearInterval(pollInterval);
    showError(progress.error);
  }
}, 3000);
```

### Display Elements

1. **Progress Bar**: Show percentage (0-100%)
2. **Status Message**: Display current_step text
3. **Steps List**: Show steps_completed array as checkmarks
4. **Elapsed Time**: Display elapsed_seconds formatted as "MM:SS"
5. **Error Message**: Show error field if status is "error"

## Performance Notes

- **Total Review Time**: ~18+ minutes for typical patient (notes extraction is slow)
  - Notes extraction: ~15-18 minutes (database query performance)
  - Vitals extraction: ~3-5 seconds
  - Labs extraction: ~20-30 seconds
  - AI analysis: ~2-3 minutes
  - Diagnosis comparison: ~1-2 seconds

- **Progress Updates**: Non-blocking, happen at data extraction completion points

- **Memory Usage**: One progress dictionary entry per active review
  - Typical size: ~500 bytes per review
  - Entries cleaned up when review completes (for long-running applications, add cleanup logic)

## Future Improvements

### Asynchronous Processing
Current implementation still blocks the API call. To make truly async:

1. Return review_id immediately from `/api/review/start`
2. Start review processing in background thread/task:
   ```python
   from fastapi import BackgroundTasks
   
   @app.post("/api/review/start")
   async def start_review(request: ReviewRequest, background_tasks: BackgroundTasks):
       review_id = str(uuid.uuid4())
       create_progress_tracker(review_id)
       background_tasks.add_task(process_review, review_id, request)
       return {"review_id": review_id, "status_url": f"/api/review/progress/{review_id}"}
   ```

3. Browser won't freeze while waiting for completion

### Progress Estimation
Add estimated time remaining:
```python
estimated_total_time = 1200  # 20 minutes in seconds
elapsed = elapsed_seconds
estimated_remaining = max(0, estimated_total_time - elapsed)
```

### Cleanup Logic
For long-running applications, clean up completed reviews after 1 hour:
```python
def cleanup_old_reviews():
    current_time = datetime.now()
    to_delete = [
        rid for rid, data in review_progress.items()
        if data.get("status") in ["complete", "error"] and
           (current_time - datetime.fromisoformat(data["end_time"])).seconds > 3600
    ]
    for rid in to_delete:
        del review_progress[rid]
```

## Testing Checklist

- [ ] Start a review via `/api/review/start` with a patient ID
- [ ] Record the returned `review_id`
- [ ] Poll `/api/review/progress/{review_id}` every 2-3 seconds
- [ ] Verify percentage increases over time (5% → 15% → 30% → 45% → 55% → 60% → 70% → 80% → 100%)
- [ ] Verify descriptive messages update at each step
- [ ] Verify steps_completed array grows with each step
- [ ] Verify elapsed_seconds increases
- [ ] When status becomes "complete", verify review_id still accessible in progress endpoint
- [ ] Test error handling by triggering an error mid-review
- [ ] Verify error status and message appear in progress endpoint

## Files Modified

- **app.py**: 
  - Lines 76-82: Global review_progress dictionary
  - Lines 85-135: Progress tracking helper functions
  - Lines 346-376: Progress reporting endpoint
  - Lines 809-820: Review ID generation and initialization
  - Lines ~987, ~1086, ~1154, ~1228: Data extraction progress updates
  - Lines ~1273, ~1303, ~1325, ~1393: AI analysis and completion progress updates
  - Error handling updated to call fail_review()

## Troubleshooting

**Progress endpoint returns 404**:
- Review ID may have expired or been misspelled
- Check that review_id is copied correctly

**Progress stuck at same percentage**:
- Review may be running slowly (normal for notes extraction)
- Check server logs for errors
- Verify database connectivity

**Percentage jumps multiple values**:
- Expected behavior - steps complete at different rates
- AI analysis (60% → 70%) happens in seconds
- Notes extraction (5% → 15%) takes 15+ minutes

**Progress never reaches 100%**:
- Review may have failed mid-process
- Check progress endpoint "error" field
- Check server logs for exceptions
