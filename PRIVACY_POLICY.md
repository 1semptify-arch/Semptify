# Semptify Privacy Policy

**Effective Date:** December 7, 2025  
**Last Updated:** December 7, 2025  
**Version:** 1.0

---

## Our Privacy Commitment

**Semptify does not store user logs, personal information, or track user activity.** We are designed with privacy-first architecture where your data remains under YOUR control.

### 100% Free

**Semptify is completely free to use.** There are:

- No subscription fees
- No premium tiers
- No hidden costs
- No paywalls
- No ads

**Donations are welcome** to help support development and server costs, but are never required.

### No User Registration

**Semptify has NO user registration process.** We don't ask you to:

- Create an account
- Choose a username
- Set a password
- Provide an email address
- Enter any personal details

You simply authenticate with your existing cloud storage provider (Google Drive, Dropbox, or OneDrive). That's it. No forms. No signups. No personal data collection.

---

## 1. Information We DO NOT Collect

Semptify explicitly **does not** collect or store:

- ❌ **User activity logs** - We don't track what you click, view, or do
- ❌ **IP addresses** - We don't log your IP address
- ❌ **Device fingerprints** - We don't uniquely identify your device
- ❌ **Browser history** - We don't track pages visited
- ❌ **Location data** - We don't track your physical location
- ❌ **Usage analytics** - We don't use third-party analytics services
- ❌ **Advertising** - We have NO ads, NO ad networks, NO ad tracking
- ❌ **Behavioral tracking** - We don't profile user behavior
- ❌ **Personal information** - No names, emails, or contact info stored

---

## 2. Technical Information We MAY Process

For compatibility purposes only, we may process (but do not log or store):

- ✅ **Browser version** - To ensure compatibility (e.g., "Chrome 120")
- ✅ **Operating system** - To ensure compatibility (e.g., "Windows 11")
- ✅ **Screen DPI/resolution** - For proper UI rendering

**This is NOT tracked, logged, or stored.** It's only used in-memory during your session for proper application rendering.

The following information is processed temporarily during your session but **never stored in our databases**:

### 2.1 Authentication Tokens

- OAuth tokens from your cloud storage provider (Google Drive, Dropbox, OneDrive)
- These are **encrypted** using AES-256-GCM with a key derived from your user ID
- Tokens are stored **only in your browser session** and encrypted session storage
- When you log out, tokens are deleted

### 2.2 Session Identifiers

- A randomly generated user ID stored in a browser cookie (`semptify_uid`)
- This ID does **not** contain any personal information
- Used only to maintain your session during use

---

## 3. Information Stored in YOUR Cloud Storage

All persistent data is stored in **your own cloud storage account** (Google Drive, Dropbox, or OneDrive), not on Semptify servers:

- Documents you upload
- Timeline events you create
- Case information you enter
- Any evidence or records you generate

### You own this data. You control this data. You can delete this data at any time

---

## 4. Minimal Database Records

We store minimal functional records in our database that are **necessary for the application to work**:

### No User Registration

There is **no registration process**. No username, no password, no email forms. You authenticate directly through your cloud storage provider's OAuth system.

### What we store:

| Data | Purpose | Retention |
| ------ | --------- | ----------- |
| User ID (random string) | Session management | Until logout |
| Cloud provider name | Know which OAuth to use | Session duration |
| Encrypted access tokens | Authenticate with your cloud | Session duration only |
| User-created case data | Your eviction case records | User-controlled deletion |

### What we DON'T store:

- Your name (we never ask for it)
- Your email (OAuth only, not stored by us)
- Your address (only if you add it to legal documents YOU create)
- Your phone number
- Your password (we use OAuth - no passwords ever)
- Your browsing behavior
- Your device information
- Any registration data (there is no registration)

---

## 5. Third-Party Services

### 5.1 Cloud Storage Providers

Semptify integrates with:

- **Google Drive** - Subject to [Google's Privacy Policy](https://policies.google.com/privacy)
- **Dropbox** - Subject to [Dropbox's Privacy Policy](https://www.dropbox.com/privacy)
- **OneDrive** - Subject to [Microsoft's Privacy Statement](https://privacy.microsoft.com/privacystatement)

We only request the **minimum permissions necessary**:

- Read/write access to the Semptify folder in your cloud storage
- Email address for OAuth identification (not stored by us)

### 5.2 No Analytics Services

We do **not** use:

- Google Analytics
- Facebook Pixel
- Mixpanel
- Amplitude
- Any other tracking service

### 5.3 No Advertising - 100% Free

**Semptify is completely free and ad-free.** We do **not**:

- Display any advertisements
- Charge subscription fees
- Have premium/paid tiers
- Participate in ad networks
- Sell data to advertisers
- Use ad tracking pixels
- Partner with data brokers
- Monetize user data in any way

**Donations accepted** but never required.

---

## 6. Data Security

### 6.1 Encryption

- All OAuth tokens are encrypted using **AES-256-GCM**
- Encryption keys are derived per-user using **PBKDF2** with 100,000 iterations
- Keys are derived from your user ID (not stored separately)

### 6.2 Secure Transmission

- All data transmitted over **HTTPS/TLS**
- OAuth flows use industry-standard **OAuth 2.0** protocol
- No data transmitted to third parties

### 6.3 Session Security

- Sessions expire after inactivity
- Logout immediately destroys session data
- No persistent cookies beyond session management

---

## 7. Your Rights

### 7.1 Access Your Data

- All your data is in YOUR cloud storage account
- You can access it directly through Google Drive, Dropbox, or OneDrive
- No need to request data from us - you already have it

### 7.2 Delete Your Data

- Delete files directly from your cloud storage
- Use the Semptify logout function to clear session data
- Delete your Semptify folder from cloud storage for complete removal

### 7.3 Export Your Data

- Your data is already in standard formats in your cloud storage
- PDF documents, JSON data files - all portable
- No lock-in, no proprietary formats

### 7.4 Revoke Access

- Revoke Semptify's access through your cloud provider's app settings
- Google: [Security Settings](https://myaccount.google.com/permissions)
- Dropbox: [Connected Apps](https://www.dropbox.com/account/connected_apps)
- OneDrive: [App Permissions](https://account.live.com/consent/Manage)

---

## 8. Children's Privacy

Semptify is not intended for users under 18 years of age. We do not knowingly collect information from children. If you are under 18, please do not use this service.

---

## 9. Legal Basis for Processing (GDPR)

For users in the European Economic Area (EEA):

| Processing Activity | Legal Basis |
| --------------------- | ------------- |
| OAuth authentication | Legitimate interest (service functionality) |
| Session management | Legitimate interest (service functionality) |
| Cloud storage access | Contract (you authorize access) |

We do **not** process personal data for marketing, profiling, or automated decision-making.

---

## 10. Data Retention

| Data Type | Retention Period |
| ----------- | ------------------ |
| Session tokens | Until logout or 7 days inactive |
| User ID | Until account deletion |
| Case data | Until you delete it |
| Cloud storage files | Under your control |

---

## 11. California Privacy Rights (CCPA)

California residents have additional rights:

- **Right to Know**: What personal information we collect (see Sections 2-4)
- **Right to Delete**: Request deletion of any stored data
- **Right to Opt-Out**: We don't sell personal information
- **Right to Non-Discrimination**: We don't discriminate based on privacy choices

### We do NOT sell your personal information

---

## 12. Changes to This Policy

We may update this Privacy Policy from time to time. Changes will be:

- Posted on this page with a new effective date
- Announced in the application if material changes occur

---

## 13. Contact Us

If you have questions about this Privacy Policy:

- **Email**: [privacy@semptify.com]
- **GitHub**: [https://github.com/1semptify-arch/Semptify]

---

## 14. Summary

| Question | Answer |
| ---------- | -------- |
| Do you log my activity? | **No** |
| Do you store my personal info? | **No** (only functional data you create) |
| Do you sell my data? | **No** |
| Do you share my data? | **No** |
| Do you show ads? | **No - completely ad-free** |
| Is it free? | **Yes - 100% free, donations accepted** |
| Where is my data stored? | **Your cloud storage account** |
| Can I delete everything? | **Yes, anytime** |
| Do you use analytics? | **No** |
| Do you show ads? | **No** |

---

### Semptify is built for privacy. Your case data is YOUR data

### 100% Free. No Ads. No Tracking. Donations Welcome
