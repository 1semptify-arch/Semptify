#!/usr/bin/env python3
"""
Legal Intel Engine - Tkinter GUI
Simple interface for crawling attorneys, entities, and viewing patterns.
"""

import tkinter as tk
from tkinter import scrolledtext, messagebox
import asyncio
import threading
import httpx
import json
from datetime import datetime

API_BASE = "http://localhost:8000"

def run_async(coro):
    """Run async function in a separate thread."""
    threading.Thread(target=lambda: asyncio.run(coro), daemon=True).start()

def log(msg, log_box):
    """Add message to log box with timestamp."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_box.insert(tk.END, f"[{timestamp}] {msg}\n")
    log_box.see(tk.END)

def clear_log(log_box):
    """Clear the log box."""
    log_box.delete(1.0, tk.END)

async def crawl_attorney(bar_number, log_box):
    """Crawl attorney by bar number."""
    try:
        log(f"Starting crawl for attorney #{bar_number}", log_box)
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{API_BASE}/crawl/attorney/{bar_number}")
            
            if resp.status_code == 200:
                data = resp.json()
                log(f"✓ Crawl started: Status={data.get('status')}, Bar={data.get('bar_number')}", log_box)
            else:
                try:
                    detail = resp.json().get('detail', resp.text)
                except Exception:
                    detail = resp.text
                log(f"✗ Error {resp.status_code}: {detail}", log_box)
                
    except Exception as e:
        log(f"✗ Exception: {e}", log_box)

async def crawl_entity(entity_name, log_box, state="MN"):
    """Crawl entity by name."""
    try:
        log(f"Starting crawl for entity '{entity_name}' ({state})", log_box)
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{API_BASE}/crawl/entity/{entity_name}?state={state}")
            
            if resp.status_code == 200:
                data = resp.json()
                log(f"✓ Entity found: {data.get('entity_name')} ({data.get('entity_type')})", log_box)
                log(f"  Status: {data.get('business_status')} | Filed: {data.get('filing_date')}", log_box)
                log(f"  Address: {data.get('address')}", log_box)
                log(f"  Registered Agent: {data.get('registered_agent')}", log_box)
                log(f"  Entity ID: {data.get('entity_id')}", log_box)
            elif resp.status_code == 503:
                try:
                    detail = resp.json().get('detail', resp.text)
                except Exception:
                    detail = resp.text
                log(f"✗ SOS site unreachable: {detail}", log_box)
            else:
                try:
                    detail = resp.json().get('detail', resp.text)
                except Exception:
                    detail = resp.text
                log(f"✗ Error {resp.status_code}: {detail}", log_box)
                
    except Exception as e:
        log(f"✗ Exception: {e}", log_box)

async def show_attorney_patterns(bar_number, log_box):
    """Show patterns for attorney by bar number."""
    try:
        log(f"Fetching attorney ID for bar #{bar_number}", log_box)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First get attorney ID
            resp = await client.get(f"{API_BASE}/intel/attorney/by-bar/{bar_number}")
            
            if resp.status_code != 200:
                log(f"✗ Attorney not found: {resp.status_code}", log_box)
                return
            
            attorney_data = resp.json()
            attorney_id = attorney_data.get('id')
            log(f"✓ Attorney found: {attorney_data.get('name')} (ID: {attorney_id})", log_box)
            
            # Get patterns
            log(f"Fetching patterns for attorney ID {attorney_id}", log_box)
            resp = await client.get(f"{API_BASE}/intel/patterns/attorney/{attorney_id}")
            
            if resp.status_code == 200:
                patterns = resp.json()
                log(f"✓ Patterns retrieved:", log_box)
                log(f"  Total Cases: {patterns.get('total_cases')}", log_box)
                log(f"  Default Rate: {patterns.get('default_rate', 0):.2%}", log_box)
                log(f"  Settlement Rate: {patterns.get('settlement_rate', 0):.2%}", log_box)
                log(f"  Avg Time to First Motion: {patterns.get('avg_time_to_first_motion_days')} days", log_box)
                log(f"  Top Entities: {', '.join(patterns.get('top_entities', []))}", log_box)
                log(f"  Court Distribution: {json.dumps(patterns.get('court_distribution', {}), indent=2)}", log_box)
            else:
                log(f"✗ Error fetching patterns: {resp.status_code}", log_box)
                
    except Exception as e:
        log(f"✗ Exception: {e}", log_box)

async def show_entity_patterns(entity_name, log_box):
    """Show patterns for entity by name."""
    try:
        log(f"Fetching entity ID for '{entity_name}'", log_box)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First get entity ID
            resp = await client.get(f"{API_BASE}/intel/entity/by-name/{entity_name}")
            
            if resp.status_code != 200:
                log(f"✗ Entity not found: {resp.status_code}", log_box)
                return
            
            entity_data = resp.json()
            entity_id = entity_data.get('id')
            log(f"✓ Entity found: {entity_data.get('name')} (ID: {entity_id})", log_box)
            
            # Get patterns
            log(f"Fetching patterns for entity ID {entity_id}", log_box)
            resp = await client.get(f"{API_BASE}/intel/patterns/entity/{entity_id}")
            
            if resp.status_code == 200:
                patterns = resp.json()
                log(f"✓ Patterns retrieved:", log_box)
                log(f"  Total Cases: {patterns.get('total_cases')}", log_box)
                log(f"  Top Attorneys: {', '.join(patterns.get('top_attorneys', []))}", log_box)
                log(f"  Attorney Counts: {json.dumps(patterns.get('attorney_counts', {}), indent=2)}", log_box)
                log(f"  Court Distribution: {json.dumps(patterns.get('court_distribution', {}), indent=2)}", log_box)
            else:
                log(f"✗ Error fetching patterns: {resp.status_code}", log_box)
                
    except Exception as e:
        log(f"✗ Exception: {e}", log_box)

async def show_shell_llc_clusters(log_box):
    """Show shell LLC clusters."""
    try:
        log(f"Fetching shell LLC clusters", log_box)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{API_BASE}/intel/clusters/shell-llcs")
            
            if resp.status_code == 200:
                clusters = resp.json()
                log(f"✓ Clusters retrieved:", log_box)
                
                agent_clusters = clusters.get('agent_clusters', [])
                log(f"  Agent Clusters: {len(agent_clusters)}", log_box)
                for cluster in agent_clusters[:5]:  # Show first 5
                    log(f"    - {cluster.get('agent')}: {len(cluster.get('entities', []))} entities", log_box)
                
                address_clusters = clusters.get('address_clusters', [])
                log(f"  Address Clusters: {len(address_clusters)}", log_box)
                for cluster in address_clusters[:5]:  # Show first 5
                    log(f"    - {cluster.get('address')[:50]}...: {len(cluster.get('entities', []))} entities", log_box)
            else:
                log(f"✗ Error fetching clusters: {resp.status_code}", log_box)
                
    except Exception as e:
        log(f"✗ Exception: {e}", log_box)

def build_gui():
    """Build the main GUI window."""
    root = tk.Tk()
    root.title("Legal Intel Engine")
    root.geometry("700x700")
    
    # Configure style
    root.configure(bg="#f0f0f0")
    
    # Title
    title_label = tk.Label(
        root, 
        text="Legal Intelligence Engine", 
        font=("Arial", 16, "bold"),
        bg="#f0f0f0"
    )
    title_label.pack(pady=10)
    
    # Attorney Section
    attorney_frame = tk.LabelFrame(root, text="Attorney Crawl", bg="#f0f0f0", padx=10, pady=10)
    attorney_frame.pack(fill="x", padx=10, pady=5)
    
    tk.Label(attorney_frame, text="Bar Number:", bg="#f0f0f0").grid(row=0, column=0, sticky="w")
    bar_entry = tk.Entry(attorney_frame, width=30)
    bar_entry.grid(row=0, column=1, padx=5, pady=5)
    
    crawl_attorney_btn = tk.Button(
        attorney_frame,
        text="Crawl Attorney",
        command=lambda: run_async(crawl_attorney(bar_entry.get(), log_box)),
        bg="#4CAF50",
        fg="white",
        width=20
    )
    crawl_attorney_btn.grid(row=0, column=2, padx=5)
    
    patterns_attorney_btn = tk.Button(
        attorney_frame,
        text="Show Patterns",
        command=lambda: run_async(show_attorney_patterns(bar_entry.get(), log_box)),
        bg="#2196F3",
        fg="white",
        width=20
    )
    patterns_attorney_btn.grid(row=1, column=1, columnspan=2, pady=5)
    
    # Entity Section
    entity_frame = tk.LabelFrame(root, text="Entity Crawl", bg="#f0f0f0", padx=10, pady=10)
    entity_frame.pack(fill="x", padx=10, pady=5)
    
    tk.Label(entity_frame, text="Entity Name:", bg="#f0f0f0").grid(row=0, column=0, sticky="w")
    entity_entry = tk.Entry(entity_frame, width=30)
    entity_entry.grid(row=0, column=1, padx=5, pady=5)
    
    tk.Label(entity_frame, text="State:", bg="#f0f0f0").grid(row=1, column=0, sticky="w")
    state_var = tk.StringVar(value="MN")
    state_entry = tk.Entry(entity_frame, textvariable=state_var, width=10)
    state_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")
    
    crawl_entity_btn = tk.Button(
        entity_frame,
        text="Crawl Entity",
        command=lambda: run_async(crawl_entity(entity_entry.get(), log_box, state_var.get())),
        bg="#4CAF50",
        fg="white",
        width=20
    )
    crawl_entity_btn.grid(row=0, column=2, padx=5)
    
    patterns_entity_btn = tk.Button(
        entity_frame,
        text="Show Patterns",
        command=lambda: run_async(show_entity_patterns(entity_entry.get(), log_box)),
        bg="#2196F3",
        fg="white",
        width=20
    )
    patterns_entity_btn.grid(row=1, column=2, padx=5)
    
    # Intel Section
    intel_frame = tk.LabelFrame(root, text="Intelligence", bg="#f0f0f0", padx=10, pady=10)
    intel_frame.pack(fill="x", padx=10, pady=5)
    
    clusters_btn = tk.Button(
        intel_frame,
        text="Show Shell LLC Clusters",
        command=lambda: run_async(show_shell_llc_clusters(log_box)),
        bg="#FF9800",
        fg="white",
        width=30
    )
    clusters_btn.pack(pady=5)
    
    # Log Section
    log_frame = tk.LabelFrame(root, text="Activity Log", bg="#f0f0f0", padx=10, pady=10)
    log_frame.pack(fill="both", expand=True, padx=10, pady=5)
    
    log_box = scrolledtext.ScrolledText(log_frame, width=80, height=20, font=("Consolas", 9))
    log_box.pack(fill="both", expand=True)
    
    # Clear log button
    clear_btn = tk.Button(
        log_frame,
        text="Clear Log",
        command=lambda: clear_log(log_box),
        bg="#f44336",
        fg="white",
        width=15
    )
    clear_btn.pack(pady=5)
    
    # Initial message
    log("Legal Intel Engine GUI started", log_box)
    log(f"API Base: {API_BASE}", log_box)
    log("Ready to crawl attorneys and entities.", log_box)
    
    root.mainloop()

if __name__ == "__main__":
    build_gui()
