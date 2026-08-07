#!/usr/bin/env python
"""
Semptify Admin Console Module Generator
Creates /modules/admin_console/ with router, UI panel, and SDK registration
"""

import os

SEMPtIFY_PATH = r"C:\Semptify\Semptify-FastAPI"
MODULES_PATH = os.path.join(SEMPtIFY_PATH, "modules")
ADMIN_PATH = os.path.join(MODULES_PATH, "admin_console")


def create_directory(path):
    """Create directory if it doesn't exist"""
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"✓ Created: {path}")
    else:
        print(f"✓ Exists: {path}")


def write_file(path, content):
    """Write content to file"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✓ Created: {path}")


def main():
    print("=" * 60)
    print("Semptify Admin Console Module Generator")
    print("=" * 60)
    print()

    # Create directory structure
    create_directory(ADMIN_PATH)
    create_directory(os.path.join(ADMIN_PATH, "templates"))
    create_directory(os.path.join(ADMIN_PATH, "static"))

    # 1. Create module manifest (__init__.py)
    manifest_content = '''"""
Admin Console Module for Semptify
Local AI bridge for tenant advocacy
"""
from app.core.semptify_internal_sdk import (
    register_module, ModuleManifest, ProductTier,
    ModuleCapability, MODULE_REGISTRY
)
from fastapi import APIRouter
import requests
import logging

logger = logging.getLogger(__name__)

# Module metadata
__module_name__ = "admin_console"
__version__ = "1.0.0"
__description__ = "Remote admin console for local AI integration"

# Create router
router = APIRouter(prefix="/admin", tags=["admin"])

# Local AI connection settings
LOCAL_AI_URL = "http://localhost:8001"  # Your local FastAPI backend

def check_local_ai() -> dict:
    """Check if local AI is connected"""
    try:
        resp = requests.get(f"{LOCAL_AI_URL}/", timeout=2)
        return {"connected": True, "status": resp.json()}
    except Exception:
        return {"connected": False, "status": "Local AI offline"}

@router.get("/status")
def admin_status():
    """Get admin console status"""
    return {
        "module": "admin_console",
        "local_ai": check_local_ai(),
        "capabilities": ["file_ops", "ai_chat", "maintenance"]
    }

@router.post("/ai/chat")
def proxy_ai_chat(model: str, message: str):
    """Proxy chat request to local AI"""
    try:
        resp = requests.post(
            f"{LOCAL_AI_URL}/ai/chat",
            json={"model": model, "message": message},
            timeout=120
        )
        return resp.json()
    except Exception as e:
        return {"error": str(e), "connected": False}

@router.get("/tools")
def proxy_tools_list():
    """Get local tools list"""
    try:
        resp = requests.get(f"{LOCAL_AI_URL}/tools/list", timeout=5)
        return resp.json()
    except Exception:
        return {"tools": [], "error": "Local AI offline"}

@router.post("/tools/execute")
def proxy_tool_execute(tool: str, args: dict):
    """Execute tool on local machine"""
    try:
        resp = requests.post(
            f"{LOCAL_AI_URL}/tools/execute",
            json={"tool": tool, "args": args},
            timeout=30
        )
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

def register():
    """Register this module with Semptify SDK"""
    manifest = ModuleManifest(
        name=__module_name__,
        version=__version__,
        description=__description__,
        tier=ProductTier.ADMIN,
        capabilities=[ModuleCapability.ROUTER, ModuleCapability.WIDGET],
        router=router,
        optional=True  # Module can be disabled without breaking core
    )
    register_module(manifest)
    logger.info(f"✓ Admin Console module registered")

# Auto-register on import
register()
'''

    write_file(os.path.join(ADMIN_PATH, "__init__.py"), manifest_content)

    # 2. Create admin panel UI template
    ui_content = """<!DOCTYPE html>
<html>
<head>
    <title>Admin Console - Local AI Bridge</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eee;
            min-height: 100vh;
        }
        .header {
            background: rgba(22, 33, 62, 0.95);
            padding: 20px 40px;
            border-bottom: 2px solid #e94560;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        h1 { color: #e94560; font-size: 1.5rem; }
        .status {
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
        }
        .status.online { background: #4ecca3; color: #1a1a2e; }
        .status.offline { background: #e94560; color: white; }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            display: grid;
            grid-template-columns: 250px 1fr;
            gap: 20px;
        }

        .sidebar {
            background: rgba(15, 52, 96, 0.6);
            border-radius: 12px;
            padding: 20px;
        }
        .sidebar h3 {
            color: #4ecca3;
            margin-bottom: 15px;
            font-size: 0.8rem;
            text-transform: uppercase;
        }

        .tool-btn {
            display: block;
            width: 100%;
            padding: 12px;
            margin: 8px 0;
            background: rgba(233, 69, 96, 0.2);
            border: 1px solid rgba(233, 69, 96, 0.3);
            color: #fff;
            border-radius: 8px;
            cursor: pointer;
            text-align: left;
            transition: all 0.2s;
        }
        .tool-btn:hover {
            background: rgba(233, 69, 96, 0.4);
        }

        .main-panel {
            background: rgba(22, 33, 62, 0.6);
            border-radius: 12px;
            padding: 20px;
        }

        .panel-section {
            margin-bottom: 30px;
        }
        .panel-section h2 {
            color: #e94560;
            margin-bottom: 15px;
            font-size: 1.1rem;
        }

        .info-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
        }
        .info-card {
            background: rgba(15, 52, 96, 0.5);
            padding: 15px;
            border-radius: 8px;
        }
        .info-card h4 {
            color: #4ecca3;
            font-size: 0.8rem;
            margin-bottom: 8px;
        }
        .info-card p {
            color: #fff;
            font-size: 1.1rem;
        }

        .connect-btn {
            background: linear-gradient(135deg, #e94560 0%, #c73e54 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            width: 100%;
        }
        .connect-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(233, 69, 96, 0.4);
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🏛️ Admin Console - Local AI Bridge</h1>
        <div class="status offline" id="statusBadge">● Disconnected</div>
    </div>

    <div class="container">
        <div class="sidebar">
            <h3>Quick Actions</h3>
            <button class="tool-btn" onclick="checkConnection()">Check Connection</button>
            <button class="tool-btn" onclick="listTools()">List Local Tools</button>
            <button class="tool-btn" onclick="viewLogs()">View Logs</button>
            <button class="tool-btn" onclick="runMaintenance()">Run Maintenance</button>

            <h3 style="margin-top: 20px;">Local AI</h3>
            <button class="connect-btn" onclick="connectLocalAI()">Connect to Local AI</button>
        </div>

        <div class="main-panel">
            <div class="panel-section">
                <h2>System Status</h2>
                <div class="info-grid">
                    <div class="info-card">
                        <h4>Local AI Status</h4>
                        <p id="aiStatus">Checking...</p>
                    </div>
                    <div class="info-card">
                        <h4>Available Tools</h4>
                        <p id="toolsCount">-</p>
                    </div>
                    <div class="info-card">
                        <h4>Last Connected</h4>
                        <p id="lastConnected">Never</p>
                    </div>
                </div>
            </div>

            <div class="panel-section">
                <h2>Available Tools</h2>
                <div id="toolsList">Click "List Local Tools" to see available tools</div>
            </div>

            <div class="panel-section">
                <h2>Documentation</h2>
                <p>This admin console connects to your local AI backend running at <code>http://localhost:8001</code></p>
                <p>When connected, you can:</p>
                <ul style="margin-left: 20px; line-height: 2;">
                    <li>Run local file operations</li>
                    <li>Chat with DeepSeek, Qwen, or Mistral</li>
                    <li>Perform maintenance tasks</li>
                    <li>Generate reports locally</li>
                </ul>
            </div>
        </div>
    </div>

    <script>
        const LOCAL_AI_URL = "http://localhost:8001";

        async function checkConnection() {
            try {
                const resp = await fetch(`${LOCAL_AI_URL}/`, { method: 'GET', mode: 'no-cors' });
                document.getElementById('statusBadge').className = 'status online';
                document.getElementById('statusBadge').textContent = '● Connected';
                document.getElementById('aiStatus').textContent = 'Online';
                document.getElementById('lastConnected').textContent = new Date().toLocaleTimeString();
            } catch (e) {
                document.getElementById('statusBadge').className = 'status offline';
                document.getElementById('statusBadge').textContent = '● Disconnected';
                document.getElementById('aiStatus').textContent = 'Offline';
            }
        }

        async function listTools() {
            try {
                const resp = await fetch('/admin/tools');
                const data = await resp.json();
                document.getElementById('toolsCount').textContent = data.tools?.length || 0;
                document.getElementById('toolsList').innerHTML =
                    '<ul>' + (data.tools || []).map(t => `<li>${t}</li>`).join('') + '</ul>';
            } catch (e) {
                document.getElementById('toolsList').textContent = 'Error: ' + e.message;
            }
        }

        function connectLocalAI() {
            window.open(LOCAL_AI_URL, '_blank');
        }

        function viewLogs() {
            alert('View logs functionality coming soon');
        }

        function runMaintenance() {
            alert('Maintenance functionality coming soon');
        }

        // Check on load
        checkConnection();
    </script>
</body>
</html>
"""

    write_file(os.path.join(ADMIN_PATH, "templates", "admin_panel.html"), ui_content)

    print()
    print("=" * 60)
    print("Admin Console Module Created Successfully!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Add to Semptify main.py:")
    print("   from modules.admin_console import router as admin_router")
    print("   app.include_router(admin_router)")
    print()
    print("2. Access admin panel at:")
    print("   http://your-semptify-server/admin/")
    print()


if __name__ == "__main__":
    main()
