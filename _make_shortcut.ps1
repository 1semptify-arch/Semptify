$ws = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath('Desktop')
$sc = $ws.CreateShortcut("$desktop\Agent Orchestrator.lnk")
$sc.TargetPath = 'E:\master-repo\sources\app-semptify-fastapi\Agent_Orchestrator.bat'
$sc.WorkingDirectory = 'E:\master-repo\sources\app-semptify-fastapi'
$sc.IconLocation = 'C:\Windows\System32\shell32.dll,13'
$sc.Description = 'Open Semptify Agent Orchestrator standalone UI'
$sc.Save()
Write-Output "Shortcut created: $desktop\Agent Orchestrator.lnk"
