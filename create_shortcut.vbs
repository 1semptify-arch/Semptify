Set WshShell = WScript.CreateObject("WScript.Shell")
strDesktop = WshShell.SpecialFolders("Desktop")
Set oShortcut = WshShell.CreateShortcut(strDesktop & "\Semptify.lnk")
oShortcut.TargetPath = "E:\master-repo\sources\app-semptify-fastapi\START-SEMPTIFY.bat"
oShortcut.WorkingDirectory = "E:\master-repo\sources\app-semptify-fastapi"
oShortcut.Description = "Start Semptify Tenant Rights System"
oShortcut.Save
WScript.Echo "Desktop shortcut created!"
