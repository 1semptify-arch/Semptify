"""
Semptify Server Runner - Windows 11 Compatible
==============================================
Run this directly: python run_server.py
This keeps the server alive and handles Windows properly.
"""
import os
import sys
import subprocess
import time
import signal

def main():
    # Set environment
    os.environ["SECURITY_MODE"] = "open"
    os.environ["DEBUG"] = "false"
    
    print()
    print("=" * 60)
    print("  🚀 SEMPTIFY SERVER - Windows 11")
    print("=" * 60)
    print()
    print("  🌐 Command Center: http://localhost:8000/static/command_center.html")
    print("  📊 Dashboard:      http://localhost:8000/static/dashboard.html")
    print("  📚 API Docs:       http://localhost:8000/docs")
    print("  ⚖️  Eviction:       http://localhost:8000/eviction/")
    print()
    print("  Press Ctrl+C to stop")
    print("=" * 60)
    print()
    
    # Open browser after 3 seconds
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
