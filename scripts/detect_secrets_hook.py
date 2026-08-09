#!/usr/bin/env python
"""Wrapper for detect-secrets pre-commit hook that strips the -w flag.

The pre-commit framework passes -w (write mode) to all hooks on newer
versions. The detect-secrets pre_commit_hook.py doesn't support -w,
so we strip it before forwarding the arguments.
"""
import sys
from detect_secrets.pre_commit_hook import main


if __name__ == "__main__":
    # Strip -w flag that pre-commit framework passes to all hooks
    args = [a for a in sys.argv[1:] if a != "-w"]
    sys.exit(main(args))
