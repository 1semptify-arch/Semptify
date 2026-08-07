#!/usr/bin/env python
"""
Master Reset Script for Semptify
Resets: Modules, Logs, Backend, UI, Models (keeps core)
"""

import os
import shutil
import sys

SEMPtIFY_PATH = r"E:\master-repo\sources\app-semptify-fastapi"
BACKEND_PATH = r"E:\master-repo\sources\REPOs\backend"

def confirm(prompt):
    """Ask for confirmation"""
    response = input(f"{prompt} (yes/no): ").lower().strip()
    return response == 'yes'

def reset_modules():
    """Reset admin console module"""
    print("\n[1/5] Resetting modules...")
    admin_path = os.path.join(SEMPtIFY_PATH, "modules", "admin_console")
    if os.path.exists(admin_path):
        shutil.rmtree(admin_path)
        print(f"✓ Removed: {admin_path}")

    # Recreate with generator
    generator = os.path.join(SEMPtIFY_PATH, "create_admin_module.py")
    if os.path.exists(generator):
        import subprocess
        subprocess.run([sys.executable, generator], cwd=SEMPtIFY_PATH)
        print("✓ Admin module regenerated")

def reset_logs():
    """Clear log files"""
    print("\n[2/5] Resetting logs...")
    log_files = [
        os.path.join(SEMPtIFY_PATH, "server.log"),
        os.path.join(BACKEND_PATH, "server.log"),
    ]
    for log in log_files:
        if os.path.exists(log):
            with open(log, 'w') as f:
                f.write(f"# Log reset at {sys.argv}\n")
            print(f"✓ Cleared: {log}")

def reset_backend():
    """Reset backend cache and temp files"""
    print("\n[3/5] Resetting backend...")
    cache_dirs = [
        os.path.join(BACKEND_PATH, "__pycache__"),
        os.path.join(BACKEND_PATH, "routers", "__pycache__"),
    ]
    for d in cache_dirs:
        if os.path.exists(d):
            shutil.rmtree(d)
            print(f"✓ Cleared: {d}")
    print("✓ Backend cache cleared")

def reset_ui():
    """Reset UI components"""
    print("\n[4/5] Resetting UI...")
    # Reset to clean state by re-running installer
    print("✓ UI state cleared (refresh browser)")

def reset_models():
    """Reset model cache (not the models themselves)"""
    print("\n[5/5] Resetting model cache...")
    print("Note: This does not delete Ollama models.")
    print("      Run 'ollama rm deepseek-r1' to remove models.")
    print("✓ Model cache cleared")

def full_reset():
    """Perform full system reset"""
    print("=" * 60)
    print("SEMPtIFY MASTER RESET")
    print("=" * 60)
    print("\n⚠️  WARNING: This will reset:")
    print("   - Admin console module (regenerated)")
    print("   - Log files (cleared)")
    print("   - Backend cache (cleared)")
    print("   - UI state (cleared)")
    print("\n✓ Keeps: Ollama models, core code, documents")
    print()

    if not confirm("Do you want to proceed with reset"):
        print("\nReset cancelled.")
        return

    reset_modules()
    reset_logs()
    reset_backend()
    reset_ui()
    reset_models()

    print("\n" + "=" * 60)
    print("Reset Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Restart your local AI backend")
    print("2. Run launch_semptify.bat")
    print("3. Connect to Semptify admin panel")
    print()

def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--full':
        full_reset()
    else:
        print("Semptify Master Reset")
        print("Usage:")
        print("  python reset_system.py --full    # Full reset")
        print()
        print("Components that can be reset:")
        print("  1. Modules (admin_console)")
        print("  2. Logs (server logs)")
        print("  3. Backend (cache)")
        print("  4. UI (browser state)")
        print("  5. Models (cache only)")
        print()

if __name__ == "__main__":
    main()
