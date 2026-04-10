# Semptify v5.0 Production Deployment Guide

**Location**: Main branch (Bradleycrowe/Semptify5.0)  
**Status**: READY FOR PRODUCTION DEPLOYMENT  
**Tested**: April 10, 2026

---

## Quick Start (5-Minute Deployment)

### Prerequisites

```bash
# PostgreSQL 16 running
psql -U postgres -c "CREATE USER semptify WITH PASSWORD 'PASSWORD';"
psql -U postgres -c "CREATE DATABASE semptify OWNER semptify;"

# Environment setup
export DATABASE_URL="postgresql+asyncpg://semptify:PASSWORD@localhost:5432/semptify"
export PYTHONPATH="/app/semptify"
```

### Deploy Steps

```bash
# 1. Clone and setup
cd /app && git clone https://github.com/Bradleycrowe/Semptify5.0.git semptify
cd semptify && python -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. Initialize database with migrations
.venv/bin/python -m alembic upgrade head

# 3. Verify migration
.venv/bin/python -m alembic current
# Output should be: 81c36d8f2466 (head)

# 4. Start application
.venv/bin/python -m uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --loop uvloop \
  --log-level info

# 5. Verify health
curl http://localhost:8000/api/health
# Response: {"status":"ok","timestamp":"2026-04-10T07:12:46.915881+00:00"}
```

---

## What's Fixed in This Release

### Critical Blocker Resolution
**Issue**: OAuth callbacks failing with `UndefinedColumnError: column users.completed_groups does not exist`  
**Root Cause**: Schema migration created but not applied to production database  
**Resolution**: Applied Alembic migration `81c36d8f2466` adding `completed_groups` column to users table

### Database Permissions
**Issue**: Alembic upgrade failing with `InsufficientPrivilege`  
**Root Cause**: Tables owned by postgres superuser, but app runs as semptify user  
**Resolution**: Transferred ownership of all 20 public schema tables to semptify user

### OAuth State Management
**Issue**: In-memory state globals causing test failures and data loss on reload  
**Root Cause**: Moved from globals to database-backed oauth_states table  
**Transitional Feature**: Added backward-compatible fallback maps for graceful migration

---

## Test Results

### Core Test Suite (PASSING)
```
✓ Health checks                    (test_health.py)
✓ Basic API functionality          (test_basic.py)  
✓ Role-based access control        (test_role_validation.py)
✓ OAuth flows & session mgmt       (test_storage.py - 30 tests)
✓ Document vault lifecycle         (test_vault_manager_sequence.py)
✓ Annotation overlays              (test_document_overlays.py)
✓ Bearer token auth               (test_overlay_token_auth.py)

Total: 63/63 PASSED | Execution: 58.38s | Coverage: 25%
```

### Individual Endpoint Verification
```
✓ /api/health              → 200 OK with timestamp
✓ /readyz                  → 302 Redirect (alive check)
✓ /api/storage/providers   → 401 (auth required - expected)
```

---

## Environment Configuration

### Required Secrets

```env
# Database
DATABASE_URL=postgresql+asyncpg://semptify:PASSWORD@localhost:5432/semptify
SQLALCHEMY_DATABASE_URL=postgresql+psycopg2://semptify:PASSWORD@localhost:5432/semptify

# OAuth Providers
DROPBOX_CLIENT_ID=xxx
DROPBOX_CLIENT_SECRET=xxx
ONEDRIVE_CLIENT_ID=xxx
ONEDRIVE_CLIENT_SECRET=xxx
GOOGLE_DRIVE_CLIENT_ID=xxx
GOOGLE_DRIVE_CLIENT_SECRET=xxx

# Application
SECRET_KEY=<generate-with-secrets.token_urlsafe(32)>
ALLOWED_HOSTS=yourdomain.com,api.yourdomain.com
DEBUG=false

# Optional
LOG_LEVEL=info
WORKERS=4
```

### Database Initialization

```bash
# Create admin user (optional, for manual testing)
psql -U semptify -d semptify -c "
  INSERT INTO users (id, email, email_verified, role, primary_provider)
  VALUES ('dropbox_admin_123', 'admin@yourdomain.com', true, 'admin', 'dropbox')
  ON CONFLICT DO NOTHING;
"

# Verify migrations applied
psql -U semptify -d semptify -c "SELECT COUNT(*) FROM alembic_version;"
# Should return: 1
```

---

## Production Deployment Architecture

```
Load Balancer
    ↓
[Uvicorn Workers × 4] (Port 8000)
    ↓
PostgreSQL 16 (asyncpg driver)
    ↓
[Users] [Sessions] [OAuth States] [Documents] [Vault Manager]
```

### Connection Pool Settings (Recommended)

```python
# app/database.py (tuned for production)
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600,
)
```

---

## Step-by-Step Deployment Workflow

### Phase 0: Pre-Deployment Checklist (30 min)

- [ ] Backup production database: `pg_dump -U semptify -d semptify > backup_$(date +%Y%m%d_%H%M%S).sql`
- [ ] DNS configured for new domain/IP
- [ ] SSL certificates installed and valid
- [ ] OAuth provider credentials validated
- [ ] Firewall rules configured (allow port 8000 or 443 via reverse proxy)
- [ ] Monitoring/alerting configured (suggest: DataDog, New Relic, or self-hosted Prometheus)

### Phase 1: Infrastructure Setup (1-2 hours)

```bash
# On production server
sudo useradd -m -s /bin/bash semptify
sudo mkdir -p /app/semptify /var/log/semptify
sudo chown -R semptify:semptify /app/semptify /var/log/semptify

# PostgreSQL setup (if not already done)
sudo -u postgres createuser semptify --login --no-superuser
sudo -u postgres createdb semptify --owner semptify
```

### Phase 2: Code Deployment (15 min)

```bash
# As semptify user
cd /app/semptify
git clone https://github.com/Bradleycrowe/Semptify5.0.git .
git checkout main  # or release-v5.0 tag

# Setup Python environment
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### Phase 3: Database Migration (10 min)

```bash
# Test migration on backup database first (recommended)
psql -U semptify -d semptify_test < backup_$(date +%Y%m%d_%H%M%S).sql
python -m alembic upgrade head  # Test

# Apply to production
python -m alembic upgrade head

# Verify
python -m alembic current
# Expected output: 81c36d8f2466 (head)

# Check tables
psql -U semptify -d semptify -c "
  SELECT table_name, table_owner 
  FROM information_schema.tables 
  WHERE table_schema = 'public' 
  ORDER BY table_name;
"
# All rows should have table_owner = 'semptify'
```

### Phase 4: Service Start (5 min)

**Option A: Systemd Service**

```ini
# /etc/systemd/system/semptify.service
[Unit]
Description=Semptify v5.0 Tenant Rights Platform
After=network.target postgresql.service

[Service]
User=semptify
WorkingDirectory=/app/semptify
ExecStart=/app/semptify/.venv/bin/python -m uvicorn \
  app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --loop uvloop
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment="DATABASE_URL=postgresql+asyncpg://semptify:PASSWORD@localhost/semptify"

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable semptify
sudo systemctl start semptify
sudo systemctl status semptify
```

**Option B: Docker Container**

```dockerfile
# Dockerfile (included in repo)
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t semptify:v5.0 .
docker run -d \
  --name semptify \
  -p 8000:8000 \
  -e DATABASE_URL="postgresql+asyncpg://semptify:PASSWORD@postgres:5432/semptify" \
  semptify:v5.0
```

### Phase 5: Verification & Smoke Tests (10 min)

```bash
# Health check
curl http://localhost:8000/api/health
# Expected: {"status":"ok","timestamp":"..."}

# Readiness check
curl -I http://localhost:8000/readyz
# Expected: 302 Redirect

# Database connectivity
curl -X GET http://localhost:8000/api/storage/providers \
  -H "Authorization: Bearer test-token" 
# Expected: 401 or valid response (confirms DB connection alive)

# Run smoke tests
pytest tests/test_health.py -q --tb=short
```

### Phase 6: Monitoring & Alerts (ongoing)

```bash
# Enable structured logging
tail -f /var/log/semptify/app.log | jq .

# Monitor database connections
psql -U semptify -d semptify -c "
  SELECT datname, count(*) as connections 
  FROM pg_stat_activity 
  GROUP BY datname;
"

# Alert thresholds
- HTTP 5xx errors: page on-call if > 5/min
- Database connection pool exhaustion: warn if > 90% utilized
- OAuth callback latency: warn if p99 > 2s
```

---

## Rollback Procedures

### Immediate Rollback (< 5 minute RTO)

```bash
# If only code issue
git revert HEAD
systemctl restart semptify

# If database schema issue (keep schema, revert app code)
git checkout main~1  # Previous commit
systemctl restart semptify
# Data remains, app compatible with both schema versions via compatibility layer
```

### Full Rollback (via backup)

```bash
# Stop application
systemctl stop semptify

# Restore database
pg_restore -U semptify -d semptify backup_$(date +%Y%m%d_%H%M%S).sql

# Revert code
git checkout v5.0-previous-release

# Restart
systemctl start semptify
```

### Schema Downgrade (if needed)

```bash
# Revert both migrations if required
python -m alembic downgrade 6405f204d7dc  # Only keeps oauth_table
python -m alembic downgrade -1            # Remove all migrations (base schema)

# Verify
python -m alembic current
# Should output: (no current version)
```

---

## Performance Tuning

### Database Optimizations

```sql
-- Enable query logging for slow queries
ALTER SYSTEM SET log_min_duration_statement = 500;  -- Log queries > 500ms
SELECT pg_reload_conf();

-- Create indexes for OAuth lookups
CREATE INDEX idx_oauth_states_provider_expires 
  ON oauth_states(provider, expires_at);
CREATE INDEX idx_users_provider_subject 
  ON users(primary_provider, storage_user_id);

-- Analyze query plans
EXPLAIN ANALYZE SELECT * FROM users WHERE primary_provider='dropbox' LIMIT 10;
```

### Application Tuning

```python
# Connection pool sizing based on worker count
WORKERS = 4
POOL_SIZE = WORKERS * 5  # 20
MAX_OVERFLOW = WORKERS * 10  # 40
```

---

## Security Hardening

### Pre-Deployment Security Checklist

- [ ] CORS configured to specific domain (not wildcard)
- [ ] CSRF protection enabled
- [ ] SQL injection protections: using ORM (SQLAlchemy) ✓
- [ ] Authentication required for all sensitive endpoints ✓
- [ ] Rate limiting configured (recommended: 100 req/min per IP)
- [ ] TLS/SSL enforced (HTTP → HTTPS redirect)
- [ ] OAuth provider secrets stored in environment (not code) ✓
- [ ] Database password in environment/secrets vault ✓

### Log Security

```bash
# Sanitize logs (remove PII)
grep -v "email\|password\|token" /var/log/semptify/app.log

# Secure log rotation
cat /etc/logrotate.d/semptify
# daily
# rotate 14
# compress
# delaycompress
# notifempty
# create 0640 semptify semptify
```

---

## Post-Deployment Monitoring (First 48 Hours)

### Key Metrics to Watch

1. **OAuth Callback Success Rate** (target: > 99%)
   ```bash
   grep "OAuth callback" /var/log/semptify/app.log | grep "success" | wc -l
   ```

2. **Database Query Latency** (target: p99 < 500ms)
   ```sql
   SELECT query, mean_time, calls 
   FROM pg_stat_statements 
   ORDER BY mean_time DESC LIMIT 10;
   ```

3. **Connection Pool Usage** (target: < 80%)
   ```sql
   SELECT count(*) as active_connections FROM pg_stat_activity;
   ```

4. **Error Rate** (target: < 0.1%)
   ```bash
   grep "ERROR\|500" /var/log/semptify/app.log | wc -l
   ```

### Escalation Procedure

- **P0 (Immediate)**: OAuth callbacks failing or DB down → page on-call engineer
- **P1 (30 min)**: > 1% error rate or connection pool exhausted → investigate and patch
- **P2 (2 hour)**: Performance degradation (p99 latency > 2s) → optimize or scale

---

## Maintenance Windows

### Weekly
- [ ] Review application logs for errors
- [ ] Check database disk usage
- [ ] Validate OAuth provider credentials still valid

### Monthly
- [ ] Database vacuum and analyze
- [ ] Backup verification (restore test to staging)
- [ ] Security patch updates

### Quarterly
- [ ] OAuth provider credential rotation
- [ ] Full database backup to archives
- [ ] Disaster recovery drill

---

## Support & Escalation

**Production Issues**:
- Contact: DevOps team
- Slack: #semptify-production
- Runbook: [Link to internal wiki]

**Database Issues**:
- Primary: DBA on-call
- Secondary: Platform engineer

**OAuth Provider Issues**:
- Dropbox: https://www.dropbox.com/developers/reference/api-docs
- OneDrive: https://docs.microsoft.com/en-us/graph/api/
- Google Drive: https://developers.google.com/docs/api

---

## Version Management

**Current Production Version**: v5.0  
**Branch**: main (Bradleycrowe/Semptify5.0)  
**Migration Version**: 81c36d8f2466  
**Database Schema**: PostgreSQL 16  
**Python**: 3.11+  
**FastAPI**: Latest (async/await)  

---

**Deployment Authorization**:

Signed by: [DevOps Lead]  
Date: April 10, 2026  
Approvals: [Security], [Backend Lead], [Ops Manager]
