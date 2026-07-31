---
description: Enable Cloudflare Development Mode and purge cache to bypass CDN caching
---

## /cloudflare-dev-mode — Cloudflare Cache Bypass

Run this when you need to bypass Cloudflare CDN caching during development or after deploying critical fixes.

---

### Step 1 — Enable Cloudflare Development Mode
// turbo
Run (PowerShell): `Get-Content .env | ForEach-Object { if ($_ -match '^(CLOUDFLARE_[^=]+)=(.+)$') { [System.Environment]::SetEnvironmentVariable($Matches[1], $Matches[2], 'Process') } }; $body = '{"value":"on"}'; Invoke-RestMethod -Uri "https://api.cloudflare.com/client/v4/zones/$env:CLOUDFLARE_ZONE_ID/settings/development_mode" -Method PATCH -Headers @{"Authorization"="Bearer $env:CLOUDFLARE_API_TOKEN";"Content-Type"="application/json"} -Body $body` in cwd `E:\master-repo\sources\app-semptify-fastapi`

Credentials are loaded from `.env` automatically. This bypasses Cloudflare cache for 3 hours.

---

### Step 2 — Purge Cloudflare Cache
// turbo
Run (PowerShell): `Get-Content .env | ForEach-Object { if ($_ -match '^(CLOUDFLARE_[^=]+)=(.+)$') { [System.Environment]::SetEnvironmentVariable($Matches[1], $Matches[2], 'Process') } }; Invoke-RestMethod -Uri "https://api.cloudflare.com/client/v4/zones/$env:CLOUDFLARE_ZONE_ID/purge_cache" -Method POST -Headers @{"Authorization"="Bearer $env:CLOUDFLARE_API_TOKEN";"Content-Type"="application/json"} -Body '{"purge_everything":true}'` in cwd `E:\master-repo\sources\app-semptify-fastapi`

This clears all cached content from Cloudflare's edge servers.

---

### Step 3 — Confirm Success
Both commands should return `{"success":true}`.

Tell the user:
"Cloudflare Development Mode is now enabled for 3 hours and cache has been purged. Your changes will be visible immediately at https://semptify.org"

---

### Notes
- Development Mode automatically expires after 3 hours
- You can re-run this workflow to extend it
- For production use, disable Development Mode to restore CDN performance
