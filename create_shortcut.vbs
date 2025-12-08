Set WshShell = WScript.CreateObject("WScript.Shell")
strDesktop = WshShell.SpecialFolders("Desktop")
Set oShortcut = WshShell.CreateShortcut(strDesktop & "\Semptify.lnk")
oShortcut.TargetPath = "C:\Semptify\Semptify-FastAPI\START-SEMPTIFY.bat"
oShortcut.WorkingDirectory = "C:\Semptify\Semptify-FastAPI"
oShortcut.Description = "Start Semptify Tenant Rights System"
oShortcut.Save
WScript.Echo "Desktop shortcut created!"
