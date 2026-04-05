# 🚀 QUICK START GUIDE - AUTO MODE

## Access Points

### 1. **Main Dashboard**
```
URL: http://localhost:8000
Location: Left sidebar (bottom of header area)
Feature: Collapsible Auto Mode panel
```

### 2. **Auto Analysis Results**
```
URL: http://localhost:8000/static/batch_analysis_results.html
Location: Sidebar → "Auto Analysis" link (with "New" badge)
Feature: Detailed analysis results for processed documents
```

### 3. **API Documentation**
```
URL: http://localhost:8000/docs
Feature: Swagger UI with all available endpoints
```

---

## How to Use

### Step 1: Configure Auto Mode
1. Click the **Auto Mode Settings** header in sidebar
2. Toggle features on/off:
   - ✓ Timeline generation
   - ✓ Calendar events
   - ✓ Complaint detection
   - ✓ Rights analysis
   - ✓ Missteps analysis
   - ✓ Tactics generation
3. Set document batch limit (1-100)
4. Click **Save Configuration**

### Step 2: Run Batch Analysis
1. Click **Run Batch Analysis** button
2. Watch status: "Processing X documents..."
3. Wait for completion (typically 30-60 seconds)
4. View updated counter: "Documents Processed: X"

### Step 3: View Results
1. Click **Auto Analysis** in sidebar (or visit `/static/batch_analysis_results.html`)
2. See detailed results:
   - Timeline events created
   - Calendar deadlines
   - Complaints filed
   - Rights identified
   - Missteps flagged
   - Tactics recommended

---

## API Endpoints

### Health Check
```
GET /health
Response: {"status":"ok","timestamp":"..."}
```

### Batch Analysis
```
POST /api/auto-mode/batch-analysis?limit=10
Response: {
  "status": "completed",
  "documents_processed": 5,
  "documents_failed": 0,
  "timestamp": "..."
}
```

### Get Configuration
```
GET /api/auto-mode/config
Response: {
  "enabled": true,
  "features": {...},
  "batch_limit": 10
}
```

### Save Configuration
```
POST /api/auto-mode/config
Body: {"enabled": true, "features": {...}}
Response: {"saved": true}
```

### Get Status
```
GET /api/auto-mode/status
Response: {
  "status": "idle|processing",
  "documents_processed": 5,
  "last_run": "..."
}
```

---

## Files & Components

| File | Size | Purpose |
|------|------|---------|
| `auto_mode_panel.html` | 17 KB | Collapsible settings panel |
| `sidebar_with_auto_mode.html` | 13 KB | Enhanced sidebar navigation |
| `auto_mode_orchestrator.py` | ~8 KB | Backend analysis coordinator |
| `calendar_service.py` | ~5 KB | Calendar event generation |
| `batch_auto_analysis.py` | ~4 KB | Standalone batch processor |
| `batch_analysis_report.json` | 9 KB | Latest analysis results |

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+B` | Begin batch analysis (when panel focused) |
| `Ctrl+R` | Reset configuration to defaults |
| `Ctrl+S` | Save configuration |
| `Esc` | Close Auto Mode panel |

---

## Troubleshooting

**"Server not responding"**
- Check: http://localhost:8000/health
- If error: Restart server with PYTHONIOENCODING=utf-8

**"Panel not showing"**
- Clear browser cache (Ctrl+Shift+Delete)
- Check: static/components/auto_mode_panel.html exists
- Check browser console (F12) for errors

**"Batch analysis stuck"**
- Wait 2-3 minutes (processing can take time)
- Or restart server: Kill python.exe, restart uvicorn

**"Configuration not saving"**
- Check: localStorage enabled in browser
- Try: Manually save with Save button
- Check: Browser developer tools → Application → Storage

---

## Example Workflow

```
1. User logs in → http://localhost:8000
2. Sidebar loads with Auto Mode panel
3. User clicks panel header to expand
4. User enables all features
5. User sets batch limit to 20
6. User clicks "Run Batch Analysis"
7. System processes 20 documents (30-60 seconds)
8. User clicks "Auto Analysis" link
9. Results dashboard opens with analysis data
10. User reviews complaints, timeline, calendar, rights, tactics
11. User exports results or takes action
```

---

## Configuration Format

localStorage key: `autoModeConfig`

```json
{
  "enabled": true,
  "features": {
    "auto_generate_timeline": true,
    "auto_generate_calendar": true,
    "complaint_detection": true,
    "rights_analysis": true,
    "missteps_analysis": true,
    "proactive_tactics": true
  },
  "batch_document_limit": 10,
  "last_run": "2026-03-23T15:53:00Z",
  "documents_processed": 5,
  "status": "completed"
}
```

---

## Performance Tips

1. **Batch size**: 10-20 documents for fast results, 50+ for comprehensive analysis
2. **Off-peak**: Run batch analysis during low-traffic times
3. **Cache**: Browser caches results locally for quick access
4. **Mobile**: Auto Mode works on mobile (responsive sidebar)

---

## Support Resources

- 📖 Full Documentation: [INTEGRATION_STATUS.md](./INTEGRATION_STATUS.md)
- 🔧 API Reference: http://localhost:8000/docs
- 🐛 Bug Reports: Check `/app/` log files
- 📁 Sample Data: `/data/documents/` directory

---

**Version**: 1.0  
**Status**: ✅ Production Ready  
**Last Updated**: 2026-03-23
