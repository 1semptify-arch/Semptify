; ============================================================
; SEMPTIFY WINDOWS INSTALLER - Inno Setup Script
; Version 5.0.0 - Windows 10/11/22 Compatible
; ============================================================
;
; This creates a proper Windows installer with:
; - Start Menu shortcuts
; - Desktop icon (optional)
; - Uninstaller
; - Registry entries
;
; Requirements:
; 1. Build with PyInstaller first: .\installer\build_installer.ps1
; 2. Install Inno Setup: https://jrsoftware.org/isinfo.php
; 3. Compile this script with Inno Setup Compiler
;
; ============================================================

#define MyAppName "Semptify"
#define MyAppVersion "5.0.0"
#define MyAppPublisher "Semptify - Pro Se Legal Assistant"
#define MyAppURL "https://github.com/1semptify-arch/Semptify-FastAPI"
#define MyAppExeName "Semptify.exe"
#define MyAppDescription "AI-Powered Legal Self-Help for Tenants"

[Setup]
; NOTE: AppId uniquely identifies this app. Do not use the same AppId in other installers.
AppId={{A7B8C9D0-E1F2-3456-7890-ABCDEF123456}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
; Allow user to choose install location
AllowNoIcons=yes
; License and info files
LicenseFile=..\LICENSE
InfoBeforeFile=..\README.md
; Output settings
OutputDir=..\dist\installer
OutputBaseFilename=Semptify-Setup-v{#MyAppVersion}
; Compression
Compression=lzma2/ultra64
SolidCompression=yes
; Windows version requirements
MinVersion=10.0
; Installer appearance
WizardStyle=modern
; Privileges - per-user install doesn't require admin
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
; Uninstall settings
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Main application files (from PyInstaller build)
Source: "..\dist\Semptify\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Comment: "{#MyAppDescription}"
Name: "{group}\{#MyAppName} - API Docs"; Filename: "http://localhost:8000/docs"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; Comment: "{#MyAppDescription}"
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// Custom code for additional installation logic

function InitializeSetup(): Boolean;
begin
  Result := True;
  // Check if port 8000 is available (optional)
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Post-installation tasks
    // Create data directories if needed
  end;
end;

[UninstallDelete]
; Clean up data directories on uninstall (optional - uncomment to enable)
; Type: filesandordirs; Name: "{app}\data"
; Type: filesandordirs; Name: "{app}\logs"
