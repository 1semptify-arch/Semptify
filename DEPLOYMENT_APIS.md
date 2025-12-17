# Semptify API & Environment Configuration

## 🔑 Required APIs with OAuth Callbacks

### 1. Google Drive (Storage Provider)
**Purpose:** User data storage & authentication

| Setting | Environment Variable | Value |
|---------|---------------------|-------|
| Client ID | `GOOGLE_DRIVE_CLIENT_ID` | From Google Cloud Console |
| Client Secret | `GOOGLE_DRIVE_CLIENT_SECRET` | From Google Cloud Console |

**OAuth Callback URLs:**
```
# Local Development
http://localhost:8000/storage/callback/google_drive

# Render.com Production
https://semptify-api.onrender.com/storage/callback/google_drive

# Custom Domain
https://yourdomain.com/storage/callback/google_drive
```

**Setup:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create project → APIs & Services → Credentials
3. Create OAuth 2.0 Client ID (Web Application)
4. Add authorized redirect URIs (all callback URLs above)
5. Enable Google Drive API

---

### 2. Dropbox (Storage Provider)
**Purpose:** Alternative user data storage

| Setting | Environment Variable | Value |
|---------|---------------------|-------|
| App Key | `DROPBOX_APP_KEY` | From Dropbox App Console |
| App Secret | `DROPBOX_APP_SECRET` | From Dropbox App Console |

**OAuth Callback URLs:**
```
# Local Development
http://localhost:8000/storage/callback/dropbox

# Render.com Production
https://semptify-api.onrender.com/storage/callback/dropbox

# Custom Domain
https://yourdomain.com/storage/callback/dropbox
```

**Setup:**
1. Go to [Dropbox App Console](https://www.dropbox.com/developers/apps)
2. Create App → Scoped access → Full Dropbox or App folder
3. Add redirect URIs in Settings tab
4. Copy App key & App secret

---

### 3. OneDrive / Microsoft (Storage Provider)
**Purpose:** Alternative user data storage

| Setting | Environment Variable | Value |
|---------|---------------------|-------|
| Client ID | `ONEDRIVE_CLIENT_ID` | From Azure Portal |
| Client Secret | `ONEDRIVE_CLIENT_SECRET` | From Azure Portal |

**OAuth Callback URLs:**
```
# Local Development
http://localhost:8000/storage/callback/onedrive

# Render.com Production
https://semptify-api.onrender.com/storage/callback/onedrive

# Custom Domain
https://yourdomain.com/storage/callback/onedrive
```

**Setup:**
1. Go to [Azure Portal](https://portal.azure.com/) → App registrations
2. New registration → Web application
3. Add redirect URIs under Authentication
4. Create client secret under Certificates & secrets
5. API permissions: Files.ReadWrite.AppFolder, User.Read, offline_access

---

## 🤖 AI Provider APIs (Choose ONE)

### Option A: Anthropic Claude (Recommended - Best Accuracy)
| Setting | Environment Variable | Value |
|---------|---------------------|-------|
| API Key | `ANTHROPIC_API_KEY` | From Anthropic Console |
| Model | `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` |
| Provider | `AI_PROVIDER` | `anthropic` |

**Get Key:** [console.anthropic.com](https://console.anthropic.com/)

---

### Option B: OpenAI GPT-4
| Setting | Environment Variable | Value |
|---------|---------------------|-------|
| API Key | `OPENAI_API_KEY` | From OpenAI Platform |
| Model | `OPENAI_MODEL` | `gpt-4o-mini` |
| Provider | `AI_PROVIDER` | `openai` |

**Get Key:** [platform.openai.com](https://platform.openai.com/)

---

### Option C: Groq (FREE Tier Available)
| Setting | Environment Variable | Value |
|---------|---------------------|-------|
| API Key | `GROQ_API_KEY` | From Groq Console |
| Model | `GROQ_MODEL` | `llama-3.3-70b-versatile` |
| Provider | `AI_PROVIDER` | `groq` |

**Get Key:** [console.groq.com](https://console.groq.com/) (FREE tier: 14,400 requests/day)

---

### Option D: Google Gemini (FREE Tier Available)
| Setting | Environment Variable | Value |
|---------|---------------------|-------|
| API Key | `GEMINI_API_KEY` | From Google AI Studio |
| Model | `GEMINI_MODEL` | `gemini-1.5-flash` |
| Provider | `AI_PROVIDER` | `gemini` |

**Get Key:** [aistudio.google.com](https://aistudio.google.com/) (FREE tier: 1,500 requests/day)

---

### Option E: Azure OpenAI
| Setting | Environment Variable | Value |
|---------|---------------------|-------|
| API Key | `AZURE_OPENAI_API_KEY` | From Azure Portal |
| Endpoint | `AZURE_OPENAI_ENDPOINT` | Your deployment endpoint |
| Deployment | `AZURE_OPENAI_DEPLOYMENT` | Deployment name |
| API Version | `AZURE_OPENAI_API_VERSION` | `2024-02-15-preview` |
| Provider | `AI_PROVIDER` | `azure` |

---

## 📄 Azure AI Document Intelligence (Optional)
**Purpose:** Advanced document OCR & extraction

| Setting | Environment Variable | Value |
|---------|---------------------|-------|
| Endpoint | `AZURE_AI_ENDPOINT` | From Azure Portal |
| Key | `AZURE_AI_KEY1` | Primary key |
| Backup Key | `AZURE_AI_KEY2` | Secondary key |
| Region | `AZURE_AI_REGION` | `eastus` |

**Setup:**
1. Go to [Azure Portal](https://portal.azure.com/)
2. Create "Document Intelligence" resource
3. Copy endpoint and keys

---

## ⚙️ Core Environment Variables

```bash
# ===========================================
# REQUIRED - Core Settings
# ===========================================
SECRET_KEY=<generate-secure-random-string>
SECURITY_MODE=enforced
DEBUG=false
LOG_LEVEL=INFO

# ===========================================
# DATABASE (Render provides this automatically)
# ===========================================
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname

# ===========================================
# STORAGE PROVIDERS (At least ONE required)
# ===========================================
# Google Drive
GOOGLE_DRIVE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_DRIVE_CLIENT_SECRET=your-client-secret

# Dropbox (optional)
DROPBOX_APP_KEY=your-app-key
DROPBOX_APP_SECRET=your-app-secret

# OneDrive (optional)
ONEDRIVE_CLIENT_ID=your-client-id
ONEDRIVE_CLIENT_SECRET=your-client-secret

# ===========================================
# AI PROVIDER (Choose ONE)
# ===========================================
AI_PROVIDER=anthropic

# Anthropic (recommended)
ANTHROPIC_API_KEY=sk-ant-...

# OR OpenAI
# OPENAI_API_KEY=sk-...

# OR Groq (FREE)
# GROQ_API_KEY=gsk_...

# OR Gemini (FREE)
# GEMINI_API_KEY=...

# ===========================================
# AZURE AI (Optional - Document Intelligence)
# ===========================================
AZURE_AI_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_AI_KEY1=your-key
AZURE_AI_REGION=eastus
```

---

## 🌐 Render.com Environment Setup

In your Render dashboard, add these environment variables:

### Required
| Variable | Value | Notes |
|----------|-------|-------|
| `SECRET_KEY` | Auto-generate | Use "Generate" button |
| `SECURITY_MODE` | `enforced` | Production security |
| `DEBUG` | `false` | Disable debug mode |
| `DATABASE_URL` | Auto from DB | Link PostgreSQL DB |

### Storage (At least one)
| Variable | Value |
|----------|-------|
| `GOOGLE_DRIVE_CLIENT_ID` | Your Google OAuth Client ID |
| `GOOGLE_DRIVE_CLIENT_SECRET` | Your Google OAuth Secret |

### AI Provider
| Variable | Value |
|----------|-------|
| `AI_PROVIDER` | `anthropic` or `groq` or `gemini` |
| `ANTHROPIC_API_KEY` | Your API key (if using Anthropic) |

---

## 🔗 Callback URL Summary

| Provider | Local | Production (Render) |
|----------|-------|---------------------|
| Google Drive | `http://localhost:8000/storage/callback/google_drive` | `https://semptify-api.onrender.com/storage/callback/google_drive` |
| Dropbox | `http://localhost:8000/storage/callback/dropbox` | `https://semptify-api.onrender.com/storage/callback/dropbox` |
| OneDrive | `http://localhost:8000/storage/callback/onedrive` | `https://semptify-api.onrender.com/storage/callback/onedrive` |

---

## ✅ Minimum Viable Deployment

For the simplest deployment, you need:

1. **Google Drive OAuth** (for user authentication/storage)
2. **Groq API Key** (FREE AI provider)
3. **Render PostgreSQL** (auto-provisioned)

That's it! Total cost: **$0/month** on Render free tier with Groq free tier.
