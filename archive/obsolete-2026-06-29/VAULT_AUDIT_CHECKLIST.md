# Semptify Vault Audit Checklist
**Compare your actual G:\My Drive with expected structure**

## 🔍 **What SHOULD Be There**

### Expected Folder Structure:
```
G:\My Drive\
├── Semptify5.0\                           ✅ SHOULD EXIST
│   ├── README.txt                        ✅ SHOULD EXIST
│   ├── .Semptify5.0\                     ✅ SHOULD EXIST (hidden)
│   │   ├── auth\                         ✅ SHOULD EXIST
│   │   │   ├── token.enc                 ✅ SHOULD EXIST
│   │   │   ├── token.enc.backup          ✅ SHOULD EXIST
│   │   │   ├── device_keys.json          ✅ SHOULD EXIST
│   │   │   ├── provisioning.json          ✅ SHOULD EXIST
│   │   │   └── rehome.json               ✅ SHOULD EXIST
│   │   └── vault\                        ✅ SHOULD EXIST
│   │       ├── README.md                 ✅ SHOULD EXIST
│   │       └── manifest.json             ✅ SHOULD EXIST
│   └── Vault\                            ✅ SHOULD EXIST
│       ├── documents\                    ✅ SHOULD EXIST
│       ├── certificates\                 ✅ SHOULD EXIST
│       ├── timeline\                     ✅ SHOULD EXIST
│       │   └── events.json              ✅ SHOULD EXIST
│       └── overlays\                     ✅ SHOULD EXIST
│           ├── registry.json             ✅ SHOULD EXIST
│           ├── documents\                ✅ SHOULD EXIST
│           ├── queries\                   ✅ SHOULD EXIST
│           ├── forms\                     ✅ SHOULD EXIST
│           ├── redactions\               ✅ SHOULD EXIST
│           ├── evidence\                  ✅ SHOULD EXIST
│           ├── legal\                     ✅ SHOULD EXIST
│           └── timeline\                  ✅ SHOULD EXIST
```

## 📋 **Audit Checklist**

### Step 1: Root Folder Check
- [ ] `Semptify5.0` folder exists in `G:\My Drive`
- [ ] If missing: Vault creation failed completely

### Step 2: Main Contents Check
- [ ] `README.txt` exists in `Semptify5.0`
- [ ] `.Semptify5.0` folder exists (may be hidden)
- [ ] `Vault` folder exists

### Step 3: Authentication System Check
- [ ] `.Semptify5.0/auth` folder exists
- [ ] `token.enc` file exists (encrypted token)
- [ ] `token.enc.backup` file exists
- [ ] `device_keys.json` file exists
- [ ] `provisioning.json` file exists
- [ ] `rehome.json` file exists

### Step 4: Legacy Vault Check
- [ ] `.Semptify5.0/vault` folder exists
- [ ] `README.md` file exists
- [ ] `manifest.json` file exists

### Step 5: Main Vault Check
- [ ] `Vault/documents` folder exists
- [ ] `Vault/certificates` folder exists
- [ ] `Vault/timeline` folder exists
- [ ] `timeline/events.json` file exists
- [ ] `Vault/overlays` folder exists
- [ ] `overlays/registry.json` file exists

### Step 6: Overlay Sub-folders Check
- [ ] `overlays/documents` folder exists
- [ ] `overlays/queries` folder exists
- [ ] `overlays/forms` folder exists
- [ ] `overlays/redactions` folder exists
- [ ] `overlays/evidence` folder exists
- [ ] `overlays/legal` folder exists
- [ ] `overlays/timeline` folder exists

## 🚨 **Common Issues & Solutions**

### Issue: No `Semptify5.0` folder
**Cause:** Vault installation never completed
**Solution:** Re-run onboarding, check OAuth connection

### Issue: Missing `.Semptify5.0` folder
**Cause:** Hidden folder not visible, or auth system failed
**Solution:**
1. Show hidden folders in Windows Explorer
2. Check if OAuth completed successfully
3. Look for error logs in vault creation

### Issue: Missing `token.enc` file
**Cause:** OAuth token backup failed
**Solution:** Reconnect storage provider

### Issue: Missing `Vault/documents` folder
**Cause:** Partial vault creation
**Solution:** Re-run vault initialization

### Issue: Empty folders only
**Cause:** Vault creation started but didn't complete
**Solution:** Check vault installer logs for errors

## 🔧 **How to Check Each Item**

### In Windows Explorer:
1. Navigate to `G:\My Drive`
2. Look for `Semptify5.0` folder
3. Enable "Show hidden folders" (View tab → Hidden items)
4. Check each subfolder systematically

### Check File Properties:
- Right-click each file → Properties
- Check file size (should be > 0 bytes)
- Check creation date (should be recent)

## 📊 **What to Report Back**

Please check and report:
1. **Which folders/files are missing?**
2. **Any error messages you saw during setup?**
3. **File sizes of key files** (token.enc, manifest.json, events.json)
4. **Creation dates** (when were they created?)

## 🎯 **Quick Diagnosis**

Based on what you find:
- **Nothing exists**: Vault creation never started
- **Partial structure**: Vault creation failed midway
- **All folders but no files**: Folder creation worked, file creation failed
- **Everything exists**: Vault creation succeeded, issue is elsewhere

---

**Run this checklist and report back what you actually find in your `G:\My Drive` folder.**
