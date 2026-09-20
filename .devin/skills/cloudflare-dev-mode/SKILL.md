# Skill

## /cloudflare-dev-mode — Cloudflare Cache Bypass

Run this when you need to bypass Cloudflare CDN caching during development or after deploying critical fixes.

**Zone:** `semptify.org` → zone ID `3afd2a548023104ce9d29c4e65848209` (account: 1semptify@gmail.com).

> **2026-09-20 fix:** the old version loaded `CLOUDFLARE_API_TOKEN` / `CLOUDFLARE_ZONE_ID` from `.env` — those vars do not exist in any current `.env` (`sec.txt` is empty). The working path is the **`cloudflare` MCP server**, which is already authenticated.

---

### Step 1 — Enable Development Mode + purge (one call)

Use the `cloudflare` MCP server's `execute` tool:

```js
async () => {
  const zone = '3afd2a548023104ce9d29c4e65848209';
  const dev = await cloudflare.request({method:'PATCH', path:`/zones/${zone}/settings/development_mode`, body:{value:'on'}});
  const purge = await cloudflare.request({method:'POST', path:`/zones/${zone}/purge_cache`, body:{purge_everything:true}});
  return {dev_mode:{success:dev.success, value:dev.result?.value}, purge:{success:purge.success}};
}
```

Both should return `success: true`. Dev Mode bypasses cache for 3 hours.

### Step 2 — Confirm

Tell the user:
"Cloudflare Development Mode is now enabled for 3 hours and cache has been purged. Your changes will be visible immediately at <https://semptify.org>"

---

### Fallback — raw API (only if the MCP server is unavailable)

If `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ZONE_ID` ever get restored to an `.env`, the PowerShell one-liners still work:

```powershell
# dev mode on
Invoke-RestMethod -Uri "https://api.cloudflare.com/client/v4/zones/$env:CLOUDFLARE_ZONE_ID/settings/development_mode" -Method PATCH -Headers @{"Authorization"="Bearer $env:CLOUDFLARE_API_TOKEN";"Content-Type"="application/json"} -Body '{"value":"on"}'
# purge all
Invoke-RestMethod -Uri "https://api.cloudflare.com/client/v4/zones/$env:CLOUDFLARE_ZONE_ID/purge_cache" -Method POST -Headers @{"Authorization"="Bearer $env:CLOUDFLARE_API_TOKEN";"Content-Type"="application/json"} -Body '{"purge_everything":true}'
```

---

### Notes

- Development Mode automatically expires after 3 hours — re-run to extend.
- For production use, disable Development Mode to restore CDN performance.
- To disable early: same call with `body:{value:'off'}`.
