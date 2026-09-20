---
mode: agent
description: Enable Cloudflare Development Mode and purge cache to bypass CDN caching
---

# Cloudflare Dev Mode Prompt

<!-- Mirrors .devin/skills/cloudflare-dev-mode/SKILL.md — keep both in sync when editing. -->

## /cloudflare-dev-mode — Cloudflare Cache Bypass

Run this when you need to bypass Cloudflare CDN caching during development or after deploying critical fixes.

**Zone:** `semptify.org` → zone ID `3afd2a548023104ce9d29c4e65848209`.

> The `.env`-based credential path is gone — use the **`cloudflare` MCP server** (already authenticated). Its `execute` tool runs:

```js
async () => {
  const zone = '3afd2a548023104ce9d29c4e65848209';
  const dev = await cloudflare.request({method:'PATCH', path:`/zones/${zone}/settings/development_mode`, body:{value:'on'}});
  const purge = await cloudflare.request({method:'POST', path:`/zones/${zone}/purge_cache`, body:{purge_everything:true}});
  return {dev_mode:{success:dev.success}, purge:{success:purge.success}};
}
```

Both should return `success: true`. Dev Mode lasts 3 hours; to disable early, PATCH `value:'off'`.
