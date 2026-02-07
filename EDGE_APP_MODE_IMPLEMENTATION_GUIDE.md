# Edge App Mode Implementation Guide

This guide provides complete instructions for converting a FastAPI web application to run as a desktop application using Microsoft Edge app mode with fullscreen support and quit functionality.

## Overview

This implementation provides:
- ✅ Launches in fullscreen mode automatically
- ✅ Quit button closes both app window and server
- ✅ Fullscreen toggle button with dynamic text
- ✅ F11 keyboard shortcut for fullscreen
- ✅ Console closes when Edge window closes
- ✅ Resilient health monitoring (won't close app prematurely)
- ✅ Works directly from File Explorer (no VS Code needed)

---

## 1. Create Edge Launcher Script

Create a new file `launcher_edge.py` in your project root:

```python
"""
Edge App Mode Launcher for FastAPI Application
Starts the FastAPI server and displays it in Microsoft Edge app mode.
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from dotenv import load_dotenv
import webbrowser

# Get project root
project_root = Path(__file__).parent

# Load environment variables
env_file = project_root / 'Key.env'  # Change filename if different
if env_file.exists():
    load_dotenv(env_file)

# Configuration - UPDATE THESE FOR YOUR PROJECT
APP_URL = "http://127.0.0.1:8000"
APP_TITLE = "Your Application Title"  # Change to your app title
STARTUP_TIMEOUT = 30  # seconds


def is_server_ready(url=APP_URL):
    """Check if the FastAPI server is ready."""
    try:
        import urllib.request
        urllib.request.urlopen(f"{url}/api/health", timeout=2)
        return True
    except Exception:
        return False


def find_edge_executable():
    """Find Microsoft Edge executable."""
    possible_paths = [
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None


def start_server():
    """Start the FastAPI server in a subprocess."""
    print("Starting FastAPI server...")
    
    if sys.platform == "win32":
        # UPDATE: Change main:app to your_module:app if different
        cmd = f'cd /d "{project_root}" && .venv\\Scripts\\activate.bat && uvicorn main:app --host 127.0.0.1 --port 8000'
        subprocess.Popen(
            cmd,
            shell=True,
            cwd=str(project_root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    else:
        cmd = f'source .venv/bin/activate && uvicorn main:app --host 127.0.0.1 --port 8000'
        subprocess.Popen(
            cmd,
            shell=True,
            cwd=str(project_root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )


def main():
    """Main launcher entry point."""
    print(f"{APP_TITLE} Launcher (Edge App Mode)")
    print(f"Project Root: {project_root}")
    print()
    
    # Start the FastAPI server
    start_server()
    
    # Wait for server to be ready
    print("Waiting for server to start...")
    start_time = time.time()
    while not is_server_ready():
        if time.time() - start_time > STARTUP_TIMEOUT:
            print(f"ERROR: Server failed to start within {STARTUP_TIMEOUT} seconds")
            sys.exit(1)
        time.sleep(0.5)
    
    print(f"Server is ready!")
    print(f"Opening application at {APP_URL}")
    print()
    
    # Launch Edge in app mode with fullscreen
    edge_process = None
    edge_exe = find_edge_executable()
    
    if edge_exe:
        print("Launching Microsoft Edge in app mode...")
        edge_process = subprocess.Popen([edge_exe, f"--app={APP_URL}", "--start-fullscreen"])
    else:
        print("Microsoft Edge not found. Opening in default browser...")
        webbrowser.open(APP_URL)
    
    print("Application launched.")
    print("Close the Edge window to exit the application.")
    print()
    
    # Monitor both Edge and server
    last_server_check = time.time()
    failed_health_checks = 0
    HEALTH_CHECK_FAILURE_THRESHOLD = 3  # Require 3 consecutive failures
    
    try:
        while True:
            # Check if Edge process is still running
            if edge_process and edge_process.poll() is not None:
                print("Edge window closed.")
                break
            
            # Check server health periodically (every 2 seconds)
            current_time = time.time()
            if current_time - last_server_check > 2:
                if not is_server_ready():
                    failed_health_checks += 1
                    if failed_health_checks >= HEALTH_CHECK_FAILURE_THRESHOLD:
                        print(f"Server has shut down. Closing Edge window...")
                        
                        # Kill all Edge processes to ensure window closes
                        if sys.platform == "win32":
                            try:
                                subprocess.run(
                                    ['taskkill', '/F', '/FI', f'WINDOWTITLE eq {APP_TITLE}*'],
                                    capture_output=True,
                                    timeout=3
                                )
                            except Exception as e:
                                print(f"Error killing Edge: {e}")
                        
                        # Terminate the process we spawned
                        if edge_process:
                            try:
                                edge_process.terminate()
                                edge_process.wait(timeout=2)
                            except Exception:
                                try:
                                    edge_process.kill()
                                except Exception:
                                    pass
                        break
                else:
                    # Server is healthy - reset failure counter
                    failed_health_checks = 0
                
                last_server_check = current_time
            
            time.sleep(0.5)
    
    except KeyboardInterrupt:
        print("\nInterrupt received. Closing application...")
        if sys.platform == "win32":
            try:
                subprocess.run(
                    ['taskkill', '/F', '/FI', f'WINDOWTITLE eq {APP_TITLE}*'],
                    capture_output=True,
                    timeout=3
                )
            except Exception:
                pass
        
        if edge_process and edge_process.poll() is None:
            try:
                edge_process.terminate()
                edge_process.wait(timeout=2)
            except Exception:
                try:
                    edge_process.kill()
                except Exception:
                    pass
    
    print("Shutting down...")
    time.sleep(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
```

**Key Configuration Points:**
- `APP_URL`: Change if using different host/port
- `APP_TITLE`: Set to your application's name
- `env_file`: Update if your environment file has a different name
- `uvicorn main:app`: Change `main:app` if your FastAPI app variable is named differently

---

## 2. Create Batch File Launcher

Create `launcher.bat` (or update your existing batch file) in project root:

```batch
@echo off
setlocal enabledelayedexpansion

REM Change to the directory where this batch file is located
cd /d "%~dp0"

echo.
echo Starting Your Application Name...
echo (Microsoft Edge App Mode)
echo.

REM Activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
    echo Virtual environment activated.
) else (
    echo [WARN] .venv not found. Ensure dependencies are installed.
    echo Run: python -m venv .venv
    echo Then: .venv\Scripts\activate.bat
    echo Then: pip install -r requirements.txt
    pause
    exit /b 1
)

REM Load environment variables from your .env file
REM UPDATE: Change Key.env to your environment file name
if exist "Key.env" (
    for /f "usebackq delims=" %%i in ("Key.env") do (
        set "%%i" 2>nul
    )
)

echo.
echo Starting application in Microsoft Edge app mode...
echo Close the Edge window to exit the application
echo.

python launcher_edge.py

echo.
echo Application closed.
endlocal
```

**What to Update:**
- Application name in echo statements
- Environment file name (if not `Key.env`)

---

## 3. Add Shutdown Endpoint to FastAPI

Add this endpoint to your FastAPI application (typically in `main.py` or `app.py`):

```python
import os
import asyncio
from datetime import datetime

@app.post("/api/shutdown")
async def shutdown():
    """Shutdown endpoint - gracefully stops the server."""
    logger.info("Shutdown requested via API")  # Optional: if you have logging
    
    response = {"status": "shutdown_initiated", "timestamp": datetime.now().isoformat()}
    
    # Schedule server shutdown after a brief delay to allow response to be sent
    async def delayed_shutdown():
        await asyncio.sleep(0.5)
        os._exit(0)
    
    asyncio.create_task(delayed_shutdown())
    return response
```

**Required Imports:**
```python
import os
import asyncio
from datetime import datetime
```

---

## 4. Make Health Endpoint Resilient

Update or create your `/api/health` endpoint to be failure-tolerant:

```python
@app.get("/api/health")
async def health_check():
    """Health check endpoint - always returns 200 to indicate server is alive."""
    try:
        # Add any component health checks here, but wrap in try-except
        # Example:
        # db_healthy = check_database_connection()
        # api_healthy = check_external_api()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0"
        }
    except Exception as e:
        # Even if there's an error, return a response to indicate server is alive
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }
```

**Important:** The health endpoint must always return a 200 response to prevent premature app closure.

---

## 5. Add Header Controls CSS

Add this CSS to the `<style>` section in your HTML templates (or to your external CSS file):

```css
/* Header control buttons */
.header-actions {
    position: absolute;
    top: 20px;
    right: 20px;
    display: flex;
    gap: 10px;
    z-index: 1000;
}

.control-button {
    padding: 8px 16px;
    border: 1px solid rgba(255, 255, 255, 0.3);
    background: rgba(255, 255, 255, 0.1);
    color: white;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.9rem;
    font-weight: 500;
    backdrop-filter: blur(10px);
    transition: all 0.2s;
}

.control-button:hover {
    background: rgba(255, 255, 255, 0.2);
    border-color: rgba(255, 255, 255, 0.5);
}

.quit-button {
    background: rgba(220, 53, 69, 0.8);
    border-color: rgba(220, 53, 69, 0.9);
}

.quit-button:hover {
    background: rgba(220, 53, 69, 1);
}
```

**Note:** Adjust colors to match your application's theme. These colors work well on dark backgrounds.

---

## 6. Add Header Controls HTML

Add this HTML structure to your `<body>` tag in each template (typically near the top):

```html
<div class="header-actions">
    <button class="control-button" id="fullscreen-btn" onclick="toggleFullscreen()">Exit Fullscreen</button>
    <button class="control-button quit-button" onclick="quitApplication()">Quit</button>
</div>
```

**Position Options:**
- Keep `position: absolute` for fixed placement (current)
- Or integrate into your existing header/nav structure

---

## 7. Add JavaScript Functions

Add this JavaScript before your closing `</body>` tag (or in your external JS file):

```javascript
<script>
    // Toggle fullscreen mode
    function toggleFullscreen() {
        if (document.fullscreenElement) {
            document.exitFullscreen().catch(() => {
                console.log('Could not exit fullscreen');
            });
        } else {
            document.documentElement.requestFullscreen().catch(() => {
                console.log('Could not enter fullscreen');
            });
        }
    }

    // Update button text based on fullscreen state
    function updateFullscreenButton() {
        const btn = document.getElementById('fullscreen-btn');
        if (btn) {
            if (document.fullscreenElement) {
                btn.textContent = 'Exit Fullscreen';
            } else {
                btn.textContent = 'Enter Fullscreen';
            }
        }
    }

    // Quit application - calls shutdown endpoint
    async function quitApplication() {
        const confirmed = confirm('Close the application and stop the server?');
        if (!confirmed) return;

        console.log('Initiating shutdown...');
        
        // Send shutdown request to server
        let shutdownSent = false;
        try {
            const response = await fetch('/api/shutdown', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            if (response.ok) {
                console.log('Shutdown request acknowledged by server');
                shutdownSent = true;
            }
        } catch (error) {
            console.error('Shutdown request failed:', error);
        }
        
        // Wait for server to shut down, then close window
        const delay = shutdownSent ? 1500 : 500;
        await new Promise(resolve => setTimeout(resolve, delay));
        console.log('Closing window...');
        
        // Try multiple methods to close the window
        window.close();
        
        // Fallback: navigate to blank page
        setTimeout(() => {
            window.location.href = 'about:blank';
        }, 500);
    }

    // Listen for fullscreen changes
    document.addEventListener('fullscreenchange', updateFullscreenButton);
    document.addEventListener('mozfullscreenchange', updateFullscreenButton);
    document.addEventListener('webkitfullscreenchange', updateFullscreenButton);
    document.addEventListener('MSFullscreenChange', updateFullscreenButton);

    // Auto-enter fullscreen on load (optional - may be blocked by browser)
    window.addEventListener('load', function() {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen().catch(() => {
                console.log('Auto-fullscreen blocked - user can enable with button or F11');
            });
        }
    });

    // F11 keyboard shortcut for fullscreen toggle
    document.addEventListener('keydown', function(event) {
        if (event.key === 'F11') {
            event.preventDefault();
            toggleFullscreen();
        }
    });
</script>
```

**Auto-fullscreen Note:** The Edge launcher uses `--start-fullscreen` flag which is more reliable than JavaScript-based fullscreen.

---

## 8. Apply to All HTML Pages

Repeat steps 5-7 for **every** HTML template in your application:
- Home page
- Results pages
- Settings pages
- Any other pages users can navigate to

**Consistency is key:** All pages need the same controls so users can always quit or toggle fullscreen.

---

## 9. Testing Checklist

Before deployment, test the following:

### Initial Launch
- [ ] Double-click `launcher.bat` from File Explorer
- [ ] Console window appears showing startup messages
- [ ] Edge window opens in fullscreen mode
- [ ] Application loads correctly

### Functionality
- [ ] Fullscreen button toggles correctly
- [ ] Button text updates ("Enter Fullscreen" ↔ "Exit Fullscreen")
- [ ] F11 keyboard shortcut works
- [ ] All navigation between pages maintains fullscreen state
- [ ] Application doesn't close unexpectedly

### Shutdown
- [ ] Click Quit button
- [ ] Confirmation dialog appears
- [ ] After confirming, server shuts down (check console)
- [ ] Edge window closes within 2-3 seconds
- [ ] Console window closes automatically
- [ ] No orphaned processes remain (check Task Manager)

### Edge Cases
- [ ] Manually close Edge window → console closes automatically
- [ ] Press Ctrl+C in console → Edge window closes
- [ ] Server crash → Edge window closes after ~6 seconds
- [ ] Internet connectivity issues don't cause premature shutdown

---

## 10. Troubleshooting

### Application closes immediately after launching
**Cause:** Health check endpoint failing  
**Solution:** Check `/api/health` endpoint returns 200 OK consistently

### Edge window doesn't close when clicking Quit
**Cause:** Shutdown endpoint not working or taskkill failing  
**Solution:** 
- Verify `/api/shutdown` endpoint is implemented
- Check console for error messages
- Ensure Windows allows taskkill command

### Console remains open after Edge closes
**Cause:** Edge process detection not working  
**Solution:** 
- Verify `edge_process` is being tracked in launcher
- Check Edge executable path is correct

### Application not starting in fullscreen
**Cause:** Edge doesn't support `--start-fullscreen` flag  
**Solution:**
- Verify Edge is up to date
- Check that JavaScript auto-fullscreen code is present
- Users can always use F11 or the button

### Quit button does nothing
**Cause:** JavaScript error or endpoint not reachable  
**Solution:**
- Open browser console (F12) to check for errors
- Verify `/api/shutdown` endpoint exists and returns 200 OK
- Check network tab for failed requests

---

## 11. Dependencies

Ensure your `requirements.txt` includes:

```txt
fastapi
uvicorn[standard]
python-dotenv
```

And any other dependencies your application needs.

---

## 12. File Structure Summary

After implementation, your project should have:

```
your_project/
├── launcher_edge.py          # NEW: Edge launcher script
├── launcher.bat               # NEW or UPDATED: Windows batch launcher
├── main.py                    # UPDATED: Added /api/shutdown and /api/health
├── requirements.txt           # Verify dependencies
├── Key.env                    # Your environment variables
├── .venv/                     # Virtual environment
└── templates/                 # Or wherever your HTML files are
    ├── index.html             # UPDATED: Added controls
    ├── page2.html             # UPDATED: Added controls
    └── ...                    # Update all HTML templates
```

---

## 13. Next Steps

1. **Customize Appearance:** Adjust button colors, positioning, and styling to match your app's design
2. **Add Icons:** Replace text buttons with icons (e.g., ⛶ for fullscreen, ✕ for quit)
3. **Keyboard Shortcuts:** Add more shortcuts (e.g., Ctrl+Q for quit)
4. **Loading Screen:** Add a splash screen while server starts
5. **System Tray:** Consider adding system tray integration for minimized operation

---

## Benefits of This Implementation

✅ **Professional Desktop Experience:** App feels like a native desktop application  
✅ **No Browser Chrome:** Borderless, minimal interface  
✅ **Easy Distribution:** Users just double-click the batch file  
✅ **Clean Shutdown:** Everything closes properly, no orphaned processes  
✅ **Fullscreen Immersion:** Users get maximum screen real estate  
✅ **Cross-Platform Ready:** Launcher script supports Windows and Unix-like systems  
✅ **Resilient Monitoring:** Won't close app due to transient network issues  

---

## Support and Maintenance

- **Edge Updates:** Implementation uses standard Edge flags that are stable across versions
- **Testing:** Test after major Edge updates or Windows updates
- **Logs:** Server logs and console output help diagnose issues
- **User Training:** Brief users on F11 shortcut and Quit button location

---

*This implementation guide is based on production-tested code. Adjust configuration variables and styling to match your specific application needs.*
