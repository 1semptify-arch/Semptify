# Semptify Windows Installer

Build a Windows executable (.exe) installer for Semptify.

## Quick Build

```powershell
# From project root
.\installer\build_installer.ps1
```

Or use batch file:
```cmd
installer\build_installer.bat
```

## Build Options

| Option | Description |
|--------|-------------|
| `-Clean` | Remove previous build first |
| `-OneFile` | Single EXE (slower startup, easier to share) |
| `-NoConsole` | Hide console window |
| `-Debug` | Verbose debug output |

### Examples

```powershell
# Standard folder build (recommended)
.\installer\build_installer.ps1

# Single EXE for easy sharing
.\installer\build_installer.ps1 -OneFile

# Clean rebuild
.\installer\build_installer.ps1 -Clean

# All options
.\installer\build_installer.ps1 -Clean -OneFile -Debug
```

## Output

After building, you'll find:

| Path | Description |
|------|-------------|
| `dist\Semptify\Semptify.exe` | Main executable (folder mode) |
| `dist\Semptify.exe` | Main executable (onefile mode) |
| `dist\Semptify-Windows-v5.0.0.zip` | Distribution package |

## Creating Windows Installer (Optional)

For a proper Windows installer with Start Menu shortcuts:

1. Install [Inno Setup](https://jrsoftware.org/isinfo.php)
2. Build with PyInstaller first (see above)
3. Open `installer\semptify_setup.iss` in Inno Setup Compiler
4. Click Build → Compile
5. Find installer at `dist\installer\Semptify-Setup-v5.0.0.exe`

## Requirements

- Windows 10/11/22 (Server 2022)
- Python 3.10+ with venv
- PyInstaller (auto-installed by build script)

## Troubleshooting

### "DLL not found" errors
Run with `-Debug` to see which DLLs are missing, then add them to the spec file.

### Large file size
The single-file mode creates a larger EXE. Use folder mode (`-OneFile` off) for smaller distribution.

### Antivirus false positives
PyInstaller executables may trigger antivirus. Sign the executable or add to whitelist.

## Files

| File | Purpose |
|------|---------|
| `semptify.spec` | PyInstaller configuration |
| `build_installer.ps1` | PowerShell build script |
| `build_installer.bat` | Batch build script |
| `semptify_setup.iss` | Inno Setup installer script |
| `version_info.txt` | Windows version metadata |
