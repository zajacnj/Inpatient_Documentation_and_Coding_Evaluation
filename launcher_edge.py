"""
Edge App Mode Launcher for IDCE Application
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
env_file = project_root / 'Key.env'
if env_file.exists():
    load_dotenv(env_file)

# Configuration
APP_URL = "http://127.0.0.1:8000"
APP_TITLE = "Inpatient Documentation and Coding Evaluation"
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
    
    # Fall back to webbrowser (system default)
    return None


def start_server():
    """Start the FastAPI server in a subprocess."""
    print("Starting FastAPI server...")
    
    if sys.platform == "win32":
        # Windows: Use the virtual environment
        cmd = f'cd /d "{project_root}" && .venv\\Scripts\\activate.bat && uvicorn main:app --host 127.0.0.1 --port 8000'
        subprocess.Popen(
            cmd,
            shell=True,
            cwd=str(project_root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    else:
        # Unix-like systems
        cmd = f'source .venv/bin/activate && uvicorn main:app --host 127.0.0.1 --port 8000'
        subprocess.Popen(
            cmd,
            shell=True,
            cwd=str(project_root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )


def launch_edge_app(url):
    """Launch Microsoft Edge in app mode."""
    edge_exe = find_edge_executable()
    
    if edge_exe:
        print(f"Launching Microsoft Edge in app mode...")
        # --app=URL = app mode (borderless, resizable, no tabs/address bar)
        # --start-fullscreen = start in fullscreen mode
        subprocess.Popen([edge_exe, f"--app={url}", "--start-fullscreen"])
    else:
        print("Microsoft Edge not found. Opening in default browser...")
        webbrowser.open(url)


def main():
    """Main launcher entry point."""
    print("IDCE Application Launcher (Edge App Mode)")
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
    
    # Launch Edge in app mode
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
    # Exit when either closes
    last_server_check = time.time()
    failed_health_checks = 0
    HEALTH_CHECK_FAILURE_THRESHOLD = 3  # Require 3 consecutive failures before declaring server dead
    
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
                        print(f"Server has shut down (failed {failed_health_checks} consecutive health checks). Closing Edge window...")
                        
                        # Kill all Edge processes to ensure window closes
                        if sys.platform == "win32":
                            try:
                                # Use taskkill to force close Edge app mode windows
                                subprocess.run(
                                    ['taskkill', '/F', '/FI', f'WINDOWTITLE eq {APP_TITLE}*'],
                                    capture_output=True,
                                    timeout=3
                                )
                                subprocess.run(
                                    ['taskkill', '/F', '/IM', 'msedge.exe', '/FI', 'STATUS eq RUNNING'],
                                    capture_output=True,
                                    timeout=3
                                )
                            except Exception as e:
                                print(f"Error killing Edge: {e}")
                        
                        # Also try to terminate the process we spawned
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
        
        # Kill Edge processes on interrupt
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
