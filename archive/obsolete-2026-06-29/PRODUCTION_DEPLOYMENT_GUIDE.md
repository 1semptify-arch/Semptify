# 🔒 PRODUCTION DEPLOYMENT GUIDE
## Semptify 5.0 - Enforced Security Mode

**Status**: ✅ Production Ready  
**Date**: March 23, 2026  
**Version**: 1.0 Secure

---

## 🚀 Quick Start - Production Deployment

### Step 1: Prepare Environment

```bash
# Copy production environment template
cp .env.production.example .env.production

# Edit with your production values
nano .env.production
```

### Step 2: Configure Required Values

**CRITICAL - Must change before deployment:**

```env
# Change these immediately!
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=your-actual-secret-key-here
API_KEY=your-actual-api-key-here

# Configure CORS for your domain
ALLOWED_ORIGINS=["https://yourdomain.com","https://api.yourdomain.com"]

# Configure SSL certificates
SSL_CERT_PATH=/etc/ssl/certs/your-cert.crt
SSL_KEY_PATH=/etc/ssl/private/your-key.key

# Database
DATABASE_URL=postgresql+asyncpg://user:password@prod-db:5432/semptify?ssl=require
```

### Step 3: Generate SSL Certificates

```bash
# Using OpenSSL (for self-signed - use CA-signed in production)
openssl req -x509 -newkey rsa:4096 -nodes \
  -out /etc/ssl/certs/semptify.crt \
  -keyout /etc/ssl/private/semptify.key \
  -days 365
```

### Step 4: Set File Permissions

```bash
# Secure sensitive files
chmod 600 .env.production
chmod 600 /etc/ssl/private/semptify.key
chmod 644 /etc/ssl/certs/semptify.crt

# Create log directory
mkdir -p logs
chmod 750 logs
```

### Step 5: Start Server with Production Security

```bash
# Load production env
export $(cat .env.production | xargs)

# Start with enforced security
python -m uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8443 \
  --ssl-keyfile=/etc/ssl/private/semptify.key \
  --ssl-certfile=/etc/ssl/certs/semptify.crt \
  --log-level info
```

---

## 🔐 Security Features Enabled

### 1. **Enforced HTTPS**
- ✅ SSL/TLS certificate required
- ✅ HTTP redirects to HTTPS
- ✅ HSTS header (1 year)
- ✅ Strict Transport Security

### 2. **Authentication & Authorization**
- ✅ API key required for all endpoints
- ✅ JWT tokens with expiration (1 hour)
- ✅ User session management
- ✅ Role-based access control

### 3. **Rate Limiting**
- ✅ 100 requests per 60 seconds per IP
- ✅ Automatic throttling on excess
- ✅ 429 Too Many Requests response

### 4. **CORS Protection**
- ✅ Whitelist allowed origins only
- ✅ Credentials required
- ✅ Specific HTTP methods allowed
- ✅ Custom headers allowed

### 5. **Input Validation**
- ✅ Request size limits (10 MB)
- ✅ Batch document limits (1-100)
- ✅ Type validation on all inputs
- ✅ SQL injection prevention

### 6. **Security Headers**
- ✅ X-Content-Type-Options: nosniff
- ✅ X-Frame-Options: DENY
- ✅ X-XSS-Protection: 1; mode=block
- ✅ Content-Security-Policy: default-src 'self'
- ✅ Referrer-Policy: strict-origin-when-cross-origin
- ✅ Permissions-Policy: disable geolocation, camera, microphone

### 7. **Database Security**
- ✅ SSL/TLS enforced connections
- ✅ Connection pooling (20 connections)
- ✅ Query timeout (10 seconds)
- ✅ No connection overflow allowed

### 8. **Cookie Security**
- ✅ Secure flag (HTTPS only)
- ✅ HttpOnly flag (no JavaScript access)
- ✅ SameSite: Strict (CSRF protection)
- ✅ 30-minute session timeout

### 9. **Logging & Monitoring**
- ✅ All requests logged with timestamps
- ✅ Error stack traces sanitized
- ✅ No sensitive data in logs
- ✅ Optional Sentry integration for error tracking

### 10. **IP Whitelisting (Optional)**
- ✅ Can be enabled for additional security
- ✅ Only specified IPs can access API
- ✅ Ideal for internal deployments

---

## 📋 Security Checklist

Before production deployment, verify:

### Infrastructure
- [ ] SSL/TLS certificates installed
- [ ] Firewall configured (only 8443/TCP)
- [ ] Load balancer configured (if used)
- [ ] Database in private network
- [ ] Log files in secure location

### Configuration
- [ ] `.env.production` created from template
- [ ] All required values configured
- [ ] SECRET_KEY changed (not default)
- [ ] API_KEY changed (not default)
- [ ] ALLOWED_ORIGINS set correctly
- [ ] Database connection uses SSL

### Application
- [ ] DEBUG=false
- [ ] ENVIRONMENT=production
- [ ] HTTPS_ONLY=true
- [ ] AUTH_REQUIRED=true
- [ ] RATE_LIMIT_ENABLED=true
- [ ] SECURE_COOKIES=true

### Monitoring
- [ ] Logging configured
- [ ] Log rotation set up
- [ ] Error alerts configured
- [ ] Uptime monitoring enabled
- [ ] Performance metrics collected

### Access Control
- [ ] Only production team has keys
- [ ] IP whitelist configured (if enabled)
- [ ] VPN access required (recommended)
- [ ] Audit logging enabled

---

## 🚨 Security Failures & Responses

### If Any Security Check Fails:

**1. DEBUG Mode Enabled**
```
ERROR: DEBUG mode is ENABLED in production!
Solution: Set DEBUG=false in .env.production
```

**2. SECRET_KEY Not Changed**
```
ERROR: SECRET_KEY not changed from default!
Solution: Generate new SECRET_KEY: python -c 'import secrets; print(secrets.token_hex(32))'
```

**3. HTTPS Not Enforced**
```
ERROR: HTTPS NOT enforced!
Solution: Set HTTPS_ONLY=true and provide SSL certificates
```

**4. Authentication Not Required**
```
ERROR: Authentication NOT required!
Solution: Set AUTH_REQUIRED=true
```

**5. Rate Limiting Disabled**
```
ERROR: Rate limiting NOT enabled!
Solution: Set RATE_LIMIT_ENABLED=true
```

---

## 🔄 Monitoring & Maintenance

### Daily Checks

```bash
# Check server health
curl -k https://your-server:8443/health

# Monitor logs
tail -f logs/production.log

# Check for errors
grep ERROR logs/production.log | tail -20
```

### Weekly Tasks

- [ ] Review security logs
- [ ] Check certificate expiration date
- [ ] Verify backup integrity
- [ ] Test failover procedures
- [ ] Review rate limit statistics

### Monthly Tasks

- [ ] Security audit
- [ ] Dependency updates
- [ ] Performance review
- [ ] Capacity planning
- [ ] Disaster recovery drill

---

## 📊 Production Endpoints

| Endpoint | Method | Auth Required | Rate Limit |
|----------|--------|---------------|-----------|
| `/health` | GET | No | Yes |
| `/api/auto-mode/config` | GET/POST | Yes | Yes |
| `/api/auto-mode/status` | GET | Yes | Yes |
| `/api/auto-mode/batch-analysis` | POST | Yes | Yes |
| `/api/docs` | GET | No | Yes |

---

## 🔑 API Authentication

### Using API Key

```bash
curl -X POST https://your-server:8443/api/auto-mode/batch-analysis \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"limit": 10}'
```

### Using JWT Token

```bash
# Get token
TOKEN=$(curl -X POST https://your-server:8443/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"user","password":"pass"}' | jq -r '.token')

# Use token
curl -X POST https://your-server:8443/api/auto-mode/batch-analysis \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"limit": 10}'
```

---

## 🆘 Troubleshooting

### Server Won't Start

**Check:**
1. SSL certificates exist and are readable
2. Port 8443 is not already in use
3. `.env.production` exists and is valid
4. All required environment variables set

**Debug:**
```bash
# Check certificate
openssl x509 -in /etc/ssl/certs/semptify.crt -text -noout

# Check port
lsof -i :8443

# Test connection
openssl s_client -connect localhost:8443
```

### Requests Being Rate Limited

**Check:**
1. Rate limit settings in `.env.production`
2. Number of requests being made
3. Client IP address

**Debug:**
```bash
# Check logs
grep "Rate limit" logs/production.log

# Adjust if needed
RATE_LIMIT_REQUESTS=200
RATE_LIMIT_PERIOD=60
```

### SSL Certificate Errors

**Check:**
1. Certificate not expired
2. Certificate path correct
3. Private key accessible
4. Certificate signed by trusted CA

**Renew certificate:**
```bash
# Using Let's Encrypt + Certbot
sudo certbot renew --force-renewal
```

---

## 📞 Support & Escalation

**Issues** → Check logs at `logs/production.log`  
**Security Concerns** → Review `.env.production` settings  
**Performance** → Check rate limits and database connection pool  
**Certificates** → Verify `/etc/ssl/` permissions and expiration

---

## ✅ Deployment Summary

Your system is now:

```
✅ HTTPS/TLS Enforced
✅ Authentication Required
✅ Rate Limiting Active
✅ CORS Protected
✅ Input Validated
✅ Headers Secured
✅ Database SSL Enforced
✅ Cookies Secured
✅ Logging Configured
✅ Production Ready
```

**Status**: 🟢 **PRODUCTION SECURE**

---

**Last Updated**: March 23, 2026  
**Version**: 1.0  
**Security Level**: ⭐⭐⭐⭐⭐ (Maximum)
