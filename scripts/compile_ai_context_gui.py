#!/usr/bin/env python3
"""
Semptify — AI Context Kit (user-friendly GUI)
Standalone tkinter app — no server, no external deps.

Save at: scripts/compile_ai_context_gui.py
Run:       python scripts/compile_ai_context_gui.py
           (or double-click the desktop launcher)
"""

import importlib
import os
import sys
import tkinter as tk
from datetime import UTC, datetime
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT_DEFAULT = SCRIPT_DIR.parent


def _plain(path):
    return path.replace("\\", "/")


class ContextKitGUI:
    def __init__(self, root):
        self.root = root
        root.title("Semptify — AI Context Kit")
        root.geometry("1000x780")
        root.minsize(760, 580)

        self.project_root = tk.StringVar(value=str(PROJECT_ROOT_DEFAULT))
        self.docs = []  # list of path strings
        self.status_vars = {}  # path -> StringVar
        self.packet_text = tk.StringVar(value="")
        self.packet_path = None

        self._build_ui()
        self._load_default_docs()
        self._refresh_status()

    # ---------- UI construction ----------

    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        # Title + one-line explainer
        header = ttk.Frame(self.root)
        header.pack(fill="x", **pad)
        ttk.Label(
            header,
            text="Semptify AI Context Kit",
            font=("Segoe UI", 16, "bold"),
        ).pack(side="left")
        ttk.Label(
            header,
            text="  Makes one file you can copy into any AI so it knows your project.",
            font=("Segoe UI", 10),
            foreground="#555",
        ).pack(side="left", padx=(4, 0))

        # 1. Where are your files?
        loc = ttk.LabelFrame(self.root, text="Step 1: Find your Semptify folder")
        loc.pack(fill="x", **pad)
        row = ttk.Frame(loc)
        row.pack(fill="x", padx=10, pady=8)
        ttk.Label(row, text="Folder:").pack(side="left")
        ttk.Entry(row, textvariable=self.project_root).pack(
            side="left", fill="x", expand=True, padx=(6, 6)
        )
        ttk.Button(row, text="Browse…", command=self._browse_root).pack(side="left")
        ttk.Button(row, text="Check files", command=self._refresh_status).pack(
            side="left", padx=(4, 0)
        )

        # 2. Which files?
        files_frame = ttk.LabelFrame(
            self.root, text="Step 2: Files to include"
        )
        files_frame.pack(fill="both", expand=False, **pad)

        list_row = ttk.Frame(files_frame)
        list_row.pack(fill="both", expand=True, padx=10, pady=8)

        self.docs_listbox = tk.Listbox(list_row, height=7, selectmode="extended")
        self.docs_listbox.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(list_row, orient="vertical", command=self.docs_listbox.yview)
        sb.pack(side="left", fill="y")
        self.docs_listbox.config(yscrollcommand=sb.set)

        btn_col = ttk.Frame(files_frame)
        btn_col.pack(side="right", fill="y", padx=(0, 10))
        ttk.Button(btn_col, text="Add by name…", command=self._add_doc).pack(fill="x", pady=2)
        ttk.Button(btn_col, text="Pick a file…", command=self._add_doc_file).pack(fill="x", pady=2)
        ttk.Button(btn_col, text="Remove", command=self._remove_doc).pack(fill="x", pady=2)

        # Status line (green/red counts)
        self.status_label = ttk.Label(self.root, text="", font=("Segoe UI", 10, "bold"))
        self.status_label.pack(fill="x", **pad)

        # Big friendly action buttons
        actions = ttk.Frame(self.root)
        actions.pack(fill="x", **pad)
        self.compile_btn = ttk.Button(
            actions,
            text="Make the AI file",
            command=self._compile,
        )
        self.compile_btn.pack(side="left", ipadx=10, ipady=4)
        ttk.Button(actions, text="Open the file", command=self._open_packet).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(actions, text="Copy to clipboard", command=self._copy_packet).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(actions, text="Clear log", command=self._clear_log).pack(side="right")

        # Notebook: What happened + What's inside
        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, **pad)

        log_frame = ttk.Frame(nb)
        nb.add(log_frame, text="What happened")
        self.log = scrolledtext.ScrolledText(log_frame, height=10, wrap="word")
        self.log.pack(fill="both", expand=True)

        preview_frame = ttk.Frame(nb)
        nb.add(preview_frame, text="What's in the file")
        self.preview = scrolledtext.ScrolledText(preview_frame, wrap="word")
        self.preview.pack(fill="both", expand=True)

        # Footer help line
        help_text = (
            "How to use:  1) Pick your folder.  2) Click 'Make the AI file'.  "
            "3) Click 'Copy to clipboard'.  4) Paste it into your AI."
        )
        ttk.Label(
            self.root,
            text=help_text,
            relief="flat",
            anchor="w",
            foreground="#444",
            font=("Segoe UI", 9),
        ).pack(fill="x", side="bottom", padx=10, pady=6)

    # ---------- Docs list management ----------

    def _load_default_docs(self):
        # Mirror the defaults from compile_ai_context.py
        defaults = [
            "Semptify_AI_Orchestration_Blueprint.md",
            "docs/admin/Semptify_Site_GUI_Framework.md",
            ".devin/workflows/preflight.md",
            "ACTIVE_CONTEXT.md",
            "BUILD_STATE.md",
        ]
        self.docs = list(defaults)
        self._render_docs()

    def _render_docs(self):
        self.docs_listbox.delete(0, "end")
        for d in self.docs:
            self.docs_listbox.insert("end", d)

    def _selected_indices(self):
        return list(self.docs_listbox.curselection())

    def _add_doc(self):
        path = simpledialog.askstring(
            "Add a file",
            "Type the file name (like: README.md or docs/help.md):",
            parent=self.root,
        )
        if path:
            path = _plain(path.strip())
            if path and path not in self.docs:
                self.docs.append(path)
                self._refresh_status()

    def _add_doc_file(self):
        root_dir = self.project_root.get()
        path = filedialog.askopenfilename(
            initialdir=root_dir, title="Pick a file to include"
        )
        if path:
            try:
                rel = _plain(os.path.relpath(path, root_dir))
            except ValueError:
                rel = _plain(path)
            if rel not in self.docs:
                self.docs.append(rel)
                self._refresh_status()

    def _remove_doc(self):
        for i in reversed(self._selected_indices()):
            del self.docs[i]
        self._render_docs()
        self._refresh_status()

    def _move_doc(self, delta):
        idxs = self._selected_indices()
        if not idxs:
            return
        i = idxs[0]
        j = i + delta
        if 0 <= j < len(self.docs):
            self.docs[i], self.docs[j] = self.docs[j], self.docs[i]
            self._render_docs()
            self.docs_listbox.selection_set(j)

    # ---------- Status ----------

    def _refresh_status(self):
        root_dir = self.project_root.get()
        found = 0
        missing = 0
        self.docs_listbox.delete(0, "end")
        for d in self.docs:
            full = os.path.join(root_dir, d)
            ok = os.path.isfile(full)
            prefix = "✓  " if ok else "✗  "
            self.docs_listbox.insert("end", prefix + d)
            if ok:
                found += 1
            else:
                missing += 1
        total = len(self.docs)
        if missing == 0:
            self.status_label.config(
                text=f"All {total} files found — ready!",
                foreground="green",
            )
        else:
            self.status_label.config(
                text=f"{missing} file(s) missing — look for the red ✗ below.",
                foreground="#b00",
            )

    # ---------- Compile ----------

    def _compile(self):
        root_dir = self.project_root.get()
        if not os.path.isdir(root_dir):
            messagebox.showerror("Folder not found", f"This folder doesn't exist:\n{root_dir}")
            return
        self._log(f"--- Build started {datetime.now(UTC).isoformat(timespec='seconds')} ---")
        self._log(f"Looking in: {root_dir}")

        # Chdir so the script's relative paths resolve correctly
        prev_cwd = os.getcwd()
        try:
            os.chdir(root_dir)

            # Load the compiler module fresh from scripts/
            sys.path.insert(0, str(SCRIPT_DIR))
            try:
                if "compile_ai_context" in sys.modules:
                    importlib.reload(sys.modules["compile_ai_context"])
                cac = importlib.import_module("compile_ai_context")
            except Exception as e:
                self._log(f"ERROR loading the builder: {e}")
                return

            # Override TARGET_DOCS with the GUI's current list
            cac.TARGET_DOCS = list(self.docs)

            # Capture prints
            import contextlib
            import io
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                cac.compile_handoff_packet()
            self._log(buf.getvalue())

            self.packet_path = os.path.join(root_dir, cac.OUTPUT_FILE)
            self._log(f"Saved: {self.packet_path}")
            self._load_preview(self.packet_path)
            messagebox.showinfo(
                "Done",
                "The file is ready.\n\nClick 'Copy to clipboard', then paste it into your AI.",
            )
        except Exception as e:
            self._log(f"ERROR: {e}")
            messagebox.showerror("Something went wrong", str(e))
        finally:
            os.chdir(prev_cwd)

    # ---------- Packet output ----------

    def _load_preview(self, path):
        self.preview.delete("1.0", "end")
        try:
            with open(path, encoding="utf-8") as f:
                self.preview.insert("1.0", f.read())
        except FileNotFoundError:
            self.preview.insert("1.0", "(No file yet — click 'Make the AI file' first.)")

    def _open_packet(self):
        if not self.packet_path or not os.path.isfile(self.packet_path):
            messagebox.showinfo("No file yet", "Click 'Make the AI file' first.")
            return
        try:
            os.startfile(self.packet_path)
        except AttributeError:
            import subprocess
            opener = "open" if sys.platform == "darwin" else "xdg-open"
            subprocess.Popen([opener, self.packet_path])

    def _copy_packet(self):
        content = self.preview.get("1.0", "end-1c")
        if not content.strip() or content.startswith("(No file yet"):
            messagebox.showinfo("No file yet", "Click 'Make the AI file' first.")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        self._log("Copied — now paste it into your AI (Ctrl+V).")

    # ---------- Log ----------

    def _log(self, msg):
        self.log.insert("end", str(msg) + "\n")
        self.log.see("end")

    def _clear_log(self):
        self.log.delete("1.0", "end")

    # ---------- Misc ----------

    def _browse_root(self):
        d = filedialog.askdirectory(
            initialdir=self.project_root.get(),
            title="Pick your Semptify folder",
        )
        if d:
            self.project_root.set(d)
            self._refresh_status()


def main():
    root = tk.Tk()
    try:
        ttk.Style().theme_use("clam")
    except tk.TclError:
        pass
    ContextKitGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
