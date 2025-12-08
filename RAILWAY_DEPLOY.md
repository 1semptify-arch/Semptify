# Semptify FastAPI - Railway Deployment

## Quick Deploy

### Option 1: One-Click Deploy (Easiest)
1. Go to [railway.app](https://railway.app)
2. Click "New Project" → "Deploy from GitHub repo"
3. Select `1semptify-arch/Semptify-FastAPI`
4. Railway auto-detects Python and deploys

### Option 2: Railway CLI
```bash
# Install CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Deploy
railway up
```

## Environment Variables

After deploying, add these in Railway Dashboard → Variables:

### Required
```
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///./semptify.db
```

### Optional (for Research Module real APIs)
```
USE_MOCK_DATA=true
ENABLE_REAL_APIS=false
STORAGE_MODE=memory
NEWS_API_KEY=your-newsapi-key
COURTLISTENER_API_KEY=your-courtlistener-key
```

## Database Setup

Railway provides free PostgreSQL. To use it:
1. Add PostgreSQL service in Railway
2. Railway auto-sets `DATABASE_URL`
3. Update your app to use PostgreSQL (it currently uses SQLite)

## Custom Domain

1. Go to Settings → Domains
2. Add custom domain (e.g., `semptify.yourdomain.com`)
3. Update DNS CNAME to Railway's provided value

## Monitoring

- **Logs:** Railway Dashboard → Deployments → View Logs
- **Metrics:** Built-in CPU/Memory graphs
- **Health:** Auto-checks `/health` endpoint

## Troubleshooting

### Build Fails
- Check `requirements.txt` has all dependencies
- Ensure Python version is specified in `runtime.txt`

### App Won't Start
- Verify `PORT` environment variable (Railway sets this automatically)
- Check logs for import errors

### Database Issues
- SQLite works but resets on redeploy
- Use Railway's PostgreSQL for persistence
