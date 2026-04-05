# Storage Configuration - IMPORTANT NOTES

## ⚠️ LOCAL STORAGE NOT AVAILABLE

**Semptify 5.0 does NOT support local-only storage.**

All documents must be stored with one of these cloud providers:

| Provider | Type | Recommended For |
|----------|------|-----------------|
| 🔵 Google Drive | Personal/Team Storage | Development, Small Teams |
| 📦 Dropbox | Personal/Team Storage | Teams with existing Dropbox |
| 🟦 OneDrive | Microsoft Ecosystem | Organizations using Microsoft 365 |
| ☁️ Cloudflare R2 | System/Admin Only | Server-side system storage |

## Temporary Local Storage

The `uploads/` directory exists **ONLY** for:
- Temporary file processing
- In-flight document handling
- Staging before cloud upload

**These files are NOT persistent** and will be cleared:
- After restart
- During cleanup cycles
- When disk space is needed

## Configuration

### Environment Variables

```bash
# ❌ NO LOCAL STORAGE PROVIDER ENV VAR - NOT SUPPORTED

# ✅ REQUIRED: Choose ONE cloud provider and configure:

# Option 1: Google Drive (Recommended)
GOOGLE_DRIVE_CLIENT_ID=your-client-id
GOOGLE_DRIVE_CLIENT_SECRET=your-client-secret

# Option 2: Dropbox
DROPBOX_APP_KEY=your-app-key
DROPBOX_APP_SECRET=your-app-secret

# Option 3: OneDrive (Microsoft)
ONEDRIVE_CLIENT_ID=your-client-id
ONEDRIVE_CLIENT_SECRET=your-client-secret

# Option 4: Cloudflare R2 (System/Admin only)
R2_ACCOUNT_ID=xxx
R2_ACCESS_KEY_ID=xxx
R2_SECRET_ACCESS_KEY=xxx
R2_BUCKET_NAME=semptify-system
```

## Available Storage Providers

### 1. Google Drive
- **Best For:** Development, small teams, easy setup
- **Setup Time:** ~5 minutes
- **Free Tier:** 15GB
- **Status:** ✅ **RECOMMENDED FOR TESTING**

### 2. Dropbox
- **Best For:** Teams, integrations
- **Setup Time:** ~5 minutes
- **Free Tier:** 2GB
- **Status:** ✅ Available

### 3. OneDrive
- **Best For:** Microsoft ecosystem, enterprise
- **Setup Time:** ~5 minutes
- **Free Tier:** 5GB (personal) / depends on license
- **Status:** ✅ Available

### 4. Cloudflare R2
- **Best For:** System/administrator storage only
- **Setup Time:** ~10 minutes
- **Pricing:** Pay-as-you-go, no egress fees
- **Status:** ✅ Available (Admin only)

## Quick Start

### To use Semptify, you MUST:

1. **Choose a cloud provider** from above
2. **Create OAuth credentials** (see OAUTH_SETUP.md)
3. **Add credentials to .env**
4. **Restart the server**
5. **Connect your storage** at `/storage/providers`

## Migration Path

If you're currently relying on local `uploads/` folder:

```bash
# DON'T DO THIS - uploads folder is temporary:
# cp uploads/* /backup/  ❌ Not persistent

# DO THIS INSTEAD:
# 1. Connect cloud storage via /storage/providers
# 2. Upload documents to cloud
# 3. Access from cloud provider dashboard
```

## API Endpoints

All storage operations require a connected cloud provider:

```python
# Connect storage (OAuth flow)
GET /storage/auth/{provider}
GET /storage/callback/{provider}

# List connected providers
GET /storage/providers

# Upload document (requires connected storage)
POST /vault/upload

# List files in cloud storage
GET /api/vault/list

# Download from cloud storage
GET /api/vault/download/{file_id}

# Delete from cloud storage
DELETE /api/vault/delete/{file_id}
```

## Error Messages

If you see these errors:

| Error | Cause | Solution |
|-------|-------|----------|
| "No storage provider connected" | Cloud storage not configured | Run `/storage/auth/google_drive` |
| "Invalid credentials" | Wrong API keys | Re-check .env file |
| "Storage not available" | Provider not enabled | Configure one provider in .env |

## Production Deployment

### Render.com / Heroku / Cloud Hosting

❌ **Do NOT rely on `/uploads/` directory** - it's ephemeral:
- ☁️ Container restarts clear files
- 🗑️ Different instances have different files
- ⚠️ No data persistence guarantee

✅ **Always use cloud storage:**
- Files survive container restarts
- Accessible from all instances/replicas
- Automatic backups
- No local disk dependency

## Testing Without Cloud Setup

If you want to test without configuring cloud storage:

1. Use the **Easy Mode Selector**: `/static/admin/easy_mode_selector.html`
2. Configure other settings (theme, UI, etc.)
3. **Skip document upload features**
4. Set up cloud storage before production use

## Support

To add local storage support or change configuration:

**Contact:** Bradley Crowe / Development Team  
**Issue:** [No local storage provider available]  
**Workaround:** Use Google Drive (easiest setup)

---

**Last Updated:** March 23, 2026  
**Status:** ✅ Cloud-only storage (by design)
