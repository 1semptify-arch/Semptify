Write-Host 'Deploying Semptify locally...'
Start-Process powershell -ArgumentList 'uvicorn main:app --port 3001'
Start-Process powershell -ArgumentList 'npm run dev'
