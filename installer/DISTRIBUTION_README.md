# Semptify 5.0 - Windows Distribution Package

## 📦 Distribution Contents

```text
Semptify5.0-Windows/
├── Install-Semptify.bat          # Double-click to install (recommended)
├── install_semptify.ps1          # PowerShell installer script
├── WINDOWS_INSTALL_GUIDE.md      # Detailed installation guide
├── README.md                     # This file
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment template
└── [Full Semptify source code]
```

## 🚀 Quick Install

### Option 1: Automated Install (Recommended)

1. Right-click `Install-Semptify.bat`
2. Select **"Run as administrator"**
3. Follow the prompts

### Option 2: PowerShell Install

```powershell
## Open PowerShell as Administrator
cd path\to\Semptify5.0-Windows
.\install_semptify.ps1
```text

### Install Options

```powershell
## Install with Windows service (auto-start on boot)
.\install_semptify.ps1 -InstallService

## Custom installation path
.\install_semptify.ps1 -InstallPath "D:\Apps\Semptify"

## Skip PostgreSQL (use SQLite instead)
.\install_semptify.ps1 -UsePostgreSQL:$false

## Custom database password
.\install_semptify.ps1 -PostgresPassword "YourSecurePassword"
```

## 📋 System Requirements

| Component | Minimum | Recommended |
| ----------- | --------- | ------------- |
| OS | Windows 10 | Windows 11 |
| RAM | 4 GB | 8 GB |
| Disk | 2 GB | 5 GB |
| Python | 3.11 | 3.11 |

The installer will automatically install:

- Python 3.11 (via winget)
- PostgreSQL 16 (via winget)
- All Python dependencies

## 🔧 Post-Installation

### Starting Semptify

**Desktop Shortcut:** Double-click the "Semptify" shortcut on your desktop

#### Command Line:

```cmd
cd E:\master-repo\sources\app-semptify-fastapi
START.ps1
```text

**Manual:**

```cmd
cd E:\master-repo\sources\app-semptify-fastapi
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Access Points

- **Web Interface:** <http://localhost:8000>
- **API Documentation:** <http://localhost:8000/docs>
- **Alternative API Docs:** <http://localhost:8000/redoc>

## 🗄️ Database Configuration

### PostgreSQL (Default)

```text
Host: localhost
Port: 5432
Database: semptify
User: postgres
Password: Semptify2024! (or your custom password)
```

### SQLite (Alternative)

If PostgreSQL installation fails or is skipped, SQLite is used automatically.
Database file: `semptify.db` in the installation directory.

## 🛠️ Troubleshooting

### "Python not found"

```powershell
## Install Python manually
winget install Python.Python.3.12

## Restart your terminal and try again
```text

### "PostgreSQL connection failed"

```powershell
## Check if PostgreSQL service is running
Get-Service postgresql*

## Start the service
Start-Service postgresql-x64-16
```

### "Port 8000 already in use"

```cmd
## Find what's using port 8000
netstat -ano | findstr :8000

## Use a different port
.venv\Scripts\python.exe -m uvicorn app.main:app --port 8080
```text

### Reset Database Password

```powershell
## Run as Administrator
cd "C:\Program Files\PostgreSQL\16\data"

## Backup and edit pg_hba.conf to trust local connections
## Then run:
psql -U postgres -c "ALTER USER postgres PASSWORD 'NewPassword';"
```

## 📁 Important Files

| File | Purpose |
| ------ | --------- |
| `.env` | Environment configuration |
| `app/main.py` | Application entry point |
| `requirements.txt` | Python dependencies |
| `alembic.ini` | Database migration config |

## 🔒 Security Notes

1. **Change default password** after installation for production use
2. **Configure firewall** if exposing to network
3. **Use HTTPS** in production with a reverse proxy
4. **Backup database** regularly

## 📞 Support

- **Documentation:** See `docs/` folder
- **Issues:** <https://github.com/1semptify-arch/Semptify5.0/issues>
- **Email:** <support@semptify.com>

## 📄 License

See LICENSE file for details.

---

**Semptify 5.0** - Empowering Tenants, Protecting Rights
