# Storage Credentials Setup Workbook

## Overview

This workbook guides you through setting up storage provider credentials for the Semptify Modular Component System. The system supports Google Drive, Dropbox, and OneDrive for file storage.

## Quick Reference

| Provider | Difficulty | Setup Time | Recommended |
|----------|------------|------------|-------------|
| Google Drive | Easy | 10-15 minutes | **Yes** |
| Dropbox | Medium | 15-20 minutes | No |
| OneDrive | Hard | 20-30 minutes | No |

---

## Option 1: Google Drive (Recommended)

### Step 1: Create Google Cloud Project

1. **Go to Google Cloud Console**
   - URL: https://console.cloud.google.com/
   - Sign in with your Google account

2. **Create New Project**
   - Click project selector (top left)
   - Click "NEW PROJECT"
   - Name: "Semptify Development"
   - Click "CREATE"

### Step 2: Enable Google Drive API

1. **Navigate to APIs**
   - Go to "APIs & Services" > "Library"
   - Search for "Google Drive API"
   - Click on it
   - Click "ENABLE"

### Step 3: Create OAuth Credentials

1. **Configure OAuth Consent Screen**
   - Go to "APIs & Services" > "OAuth consent screen"
   - Select "External" (for testing)
   - Fill in required fields:
     - App name: "Semptify Development"
     - User support email: your-email@gmail.com
     - Developer contact: your-email@gmail.com
   - Click "SAVE AND CONTINUE"
   - Add test users (your email address)
   - Click "SAVE AND CONTINUE" through remaining steps

2. **Create Credentials**
   - Go to "APIs & Services" > "Credentials"
   - Click "+ CREATE CREDENTIALS"
   - Select "OAuth client ID"
   - Application type: "Web application"
   - Name: "Semptify Web Client"
   - Authorized redirect URIs:
     - Click "+ ADD URI"
     - Add: `http://localhost:8000/storage/google_drive/callback`
   - Click "CREATE"

3. **Get Your Credentials**
   - Copy the **Client ID**
   - Copy the **Client Secret**
   - Keep these secure!

### Step 4: Set Environment Variables

**Windows (Command Prompt):**
```cmd
set GOOGLE_DRIVE_CLIENT_ID=your_client_id_here
set GOOGLE_DRIVE_CLIENT_SECRET=your_client_secret_here
```

**Windows (PowerShell):**
```powershell
$env:GOOGLE_DRIVE_CLIENT_ID="your_client_id_here"
$env:GOOGLE_DRIVE_CLIENT_SECRET="your_client_secret_here"
```

**Linux/Mac:**
```bash
export GOOGLE_DRIVE_CLIENT_ID="your_client_id_here"
export GOOGLE_DRIVE_CLIENT_SECRET="your_client_secret_here"
```

### Step 5: Test Integration

1. **Restart Server**
   ```bash
   python -m uvicorn app.main:fastapi_app --reload
   ```

2. **Connect Storage**
   - Visit: http://localhost:8000/storage/providers
   - Click "Google Drive"
   - Complete OAuth flow
   - Grant permissions

3. **Test Upload**
   - Visit: http://localhost:8000/tenant/dashboard
   - Try uploading a file

---

## Option 2: Dropbox

### Step 1: Create Dropbox App

1. **Go to Dropbox Developers**
   - URL: https://www.dropbox.com/developers/apps
   - Sign in with your Dropbox account

2. **Create New App**
   - Click "Create app"
   - Choose "Full Dropbox" (not scoped)
   - App name: "Semptify Development"
   - Click "Create app"

### Step 2: Configure App

1. **Set Permissions**
   - Go to "Permissions" tab
   - Add these permissions:
     - `files.content.write`
     - `files.content.read`
     - `files.metadata.write`
     - `files.metadata.read`
   - Click "Submit"

2. **Set Redirect URI**
   - Go to "Settings" tab
   - Under "Development users", add your email
   - Under "Redirect URIs", add:
     - `http://localhost:8000/storage/dropbox/callback`

### Step 3: Get Credentials

1. **Get App Key and Secret**
   - Go to "Settings" tab
   - Find "App key" and "App secret"
   - Generate access token if needed

### Step 4: Set Environment Variables

```bash
export DROPBOX_APP_KEY="your_app_key_here"
export DROPBOX_APP_SECRET="your_app_secret_here"
```

### Step 5: Test Integration

1. Restart server and test as described in Google Drive steps

---

## Option 3: OneDrive (Microsoft)

### Step 1: Create Azure App

1. **Go to Azure Portal**
   - URL: https://portal.azure.com/
   - Sign in with Microsoft account

2. **Create App Registration**
   - Go to "Azure Active Directory" > "App registrations"
   - Click "New registration"
   - Name: "Semptify Development"
   - Redirect URI: `http://localhost:8000/storage/onedrive/callback`
   - Click "Register"

### Step 2: Configure API Permissions

1. **Add Microsoft Graph Permissions**
   - Go to "API permissions" > "Add a permission"
   - Select "Microsoft Graph"
   - Select "Application permissions"
   - Add these permissions:
     - `Files.ReadWrite.AppFolder`
     - `User.Read`
   - Click "Add permissions"

2. **Grant Admin Consent**
   - Click "Grant admin consent for [your tenant]"

### Step 3: Create Client Secret

1. **Generate Secret**
   - Go to "Certificates & secrets"
   - Click "New client secret"
   - Description: "Semptify Development"
   - Expiration: Choose appropriate duration
   - Click "Add"

2. **Copy Credentials**
   - Copy the **Application (client) ID**
   - Copy the **client secret** (copy immediately, it won't show again)

### Step 4: Set Environment Variables

```bash
export ONEDRIVE_CLIENT_ID="your_client_id_here"
export ONEDRIVE_CLIENT_SECRET="your_client_secret_here"
```

### Step 5: Test Integration

1. Restart server and test as described in Google Drive steps

---

## Troubleshooting

### Common Issues

#### Google Drive
- **"redirect_uri_mismatch"**: Ensure redirect URI exactly matches in Google Console
- **"invalid_client"**: Check Client ID and Secret are correct
- **"access_denied"**: Make sure you're added as a test user

#### Dropbox
- **"invalid_redirect_uri"**: Check redirect URI in Dropbox app settings
- **"app_not_found"**: Ensure app is in development mode

#### OneDrive
- **"invalid_client"**: Check Application ID and Client Secret
- **"consent_required"**: Grant admin consent for API permissions

### Debug Tips

1. **Check Server Logs**
   ```bash
   # Look for OAuth-related errors
   tail -f logs/semptify.log
   ```

2. **Verify Environment Variables**
   ```bash
   # Check if variables are set
   echo $GOOGLE_DRIVE_CLIENT_ID
   echo $GOOGLE_DRIVE_CLIENT_SECRET
   ```

3. **Test OAuth Flow**
   - Visit: http://localhost:8000/storage/providers
   - Check browser console for errors
   - Monitor network requests

### Reset Credentials

If you need to start over:

1. **Revoke Access**
   - Google: https://myaccount.google.com/permissions
   - Dropbox: https://www.dropbox.com/account/connected_apps
   - Microsoft: https://account.microsoft.com/permissions

2. **Clear Browser Data**
   - Clear cookies for localhost
   - Clear browser cache

3. **Delete OAuth States**
   - Clear server OAuth state database
   - Restart server

---

## Security Best Practices

### Development
- Use test accounts, not production credentials
- Set app to "testing" mode when available
- Limit scope to only necessary permissions

### Production
- Use environment variables, not hardcoded credentials
- Rotate credentials regularly
- Monitor API usage and access logs
- Use HTTPS in production

### Credential Management
- Never commit credentials to version control
- Use secure credential storage (vault, secrets manager)
- Share credentials only with authorized team members
- Revoke credentials when no longer needed

---

## Next Steps

After setting up credentials:

1. **Test Complete Upload Flow**
   - Connect storage provider
   - Upload test files
   - Verify files appear in cloud storage

2. **Test Error Handling**
   - Try uploading without storage connected
   - Test large files
   - Test unsupported file types

3. **Test Multiple Providers**
   - Set up multiple providers
   - Test switching between providers
   - Verify provider-specific features

4. **Production Preparation**
   - Set up production credentials
   - Configure proper redirect URIs
   - Test with HTTPS

---

## Support

### Documentation
- Google Drive API: https://developers.google.com/drive/api
- Dropbox API: https://www.dropbox.com/developers/documentation
- Microsoft Graph: https://docs.microsoft.com/en-us/graph/api

### Community
- Semptify GitHub Issues
- Stack Overflow (tag with semptify)
- Developer Discord (if available)

### Debug Resources
- Browser Developer Tools
- Server logs
- API documentation at /docs endpoint

---

## Checklist

- [ ] Choose storage provider
- [ ] Create developer account/app
- [ ] Configure OAuth settings
- [ ] Set environment variables
- [ ] Test OAuth flow
- [ ] Test file upload
- [ ] Test error handling
- [ ] Verify file storage
- [ ] Document credentials for team
- [ ] Set up production credentials

---

**Remember**: Keep your credentials secure and never share them in public repositories!
