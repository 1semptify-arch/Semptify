$ws = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath('Desktop')
$sc = $ws.CreateShortcut("$desktop\Agent Orchestrator.lnk")
$sc.TargetPath = 'C:\Semptify\Semptify-FastAPI\Agent_Orchestrator.bat'
$sc.WorkingDirectory = 'C:\Semptify\Semptify-FastAPI'
$sc.IconLocation = 'C:\Windows\System32\shell32.dll,13'
$sc.Description = 'Open Semptify Agent Orchestrator standalone UI'
$sc.Save()
Write-Output "Shortcut created: $desktop\Agent Orchestrator.lnk"
