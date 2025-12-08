"""
Semptify Server Runner - Windows 10/11/22 Compatible
=====================================================
Run this directly: python run_server.py
This keeps the server alive and handles Windows properly.
"""
import os
import sys
import subprocess
import time
import signal

# Fix console encoding for Windows (handles emojis in frozen exe)
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, OSError):
        pass  # Older Python or redirected output

def main():
    # Load from .env if not already set (don't override environment variables)
    if "SECURITY_MODE" not in os.environ:
        os.environ["SECURITY_MODE"] = "enforced"  # Default to enforced/production
    if "DEBUG" not in os.environ:
        os.environ["DEBUG"] = "false"

    security_mode = os.environ.get("SECURITY_MODE", "enforced")

    print()
    print("=" * 60)
    print("  SEMPTIFY SERVER - Production Mode")
    print("=" * 60)
    print()
    print(f"  Security:       {security_mode.upper()}")
    print("  Command Center: http://localhost:8000/static/command_center.html")
    print("  Dashboard:      http://localhost:8000/static/dashboard.html")
    print("  API Docs:       http://localhost:8000/docs")
    print("  Eviction:       http://localhost:8000/eviction/")
    print()
    print("  Press Ctrl+C to stop")
    print("=" * 60)
    print()    # Open browser after 3 seconds
    import threading
    import webbrowser
    def open_browser():
        time.sleep(3)
        webbrowser.open("http://localhost:8000/static/command_center.html")
    
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Run uvicorn directly (not as subprocess)
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # No reload = more stable on Windows
        workers=1,
        log_level="info"
    )

if __name__ == "__main__":
    main()
