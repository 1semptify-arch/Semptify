# Semptify Desktop Launcher
# This creates a standalone Windows executable

import os
import socket
import threading
import time
import webbrowser
from contextlib import closing


def find_free_port():
    """Find an available port."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def open_browser(port):
    """Open browser after server starts."""
    time.sleep(2)  # Wait for server to start
    webbrowser.open(f"http://localhost:{port}/static/welcome.html")


def main():
    # Set up environment - security always enforced
    os.environ.setdefault("SECURITY_MODE", "enforced")
    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./semptify.db")

    # Find available port
    port = find_free_port()
    os.environ["PORT"] = str(port)

    print(f"""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   ███████╗███████╗███╗   ███╗██████╗ ████████╗██╗███████╗ ║
    ║   ██╔════╝██╔════╝████╗ ████║██╔══██╗╚══██╔══╝██║██╔════╝ ║
    ║   ███████╗█████╗  ██╔████╔██║██████╔╝   ██║   ██║█████╗   ║
    ║   ╚════██║██╔══╝  ██║╚██╔╝██║██╔═══╝    ██║   ██║██╔══╝   ║
    ║   ███████║███████╗██║ ╚═╝ ██║██║        ██║   ██║██║      ║
    ║   ╚══════╝╚══════╝╚═╝     ╚═╝╚═╝        ╚═╝   ╚═╝╚═╝      ║
    ║                                                           ║
    ║              Tenant Defense System v5.0                   ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝

    🚀 Starting Semptify on port {port}...
    🌐 Browser will open automatically

    Press Ctrl+C to stop the server
    """)

    # Open browser in background thread
    browser_thread = threading.Thread(target=open_browser, args=(port,), daemon=True)
    browser_thread.start()

    # Start the server
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()
