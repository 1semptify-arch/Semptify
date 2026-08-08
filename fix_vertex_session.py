#!/usr/bin/env python
"""
Fix Vertex AI session ID collision by adding timestamp to session IDs
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def find_vertex_session_usage():
    """Find where Vertex AI sessions are being created"""

    # Search for common patterns

    import subprocess

    try:
        result = subprocess.run(
            ["grep", "-r", "--include=*.py", "reasoningEngines", "app/"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        print("=== reasoningEngines usage ===")
        print(result.stdout)
        print(result.stderr)
    except Exception as e:
        print(f"Search failed: {e}")

    # Look for session ID generation patterns
    try:
        result = subprocess.run(
            ["grep", "-r", "--include=*.py", "019e1341", "app/"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        print("=== Session ID pattern ===")
        print(result.stdout)
        print(result.stderr)
    except Exception as e:
        print(f"Search failed: {e}")


if __name__ == "__main__":
    find_vertex_session_usage()
