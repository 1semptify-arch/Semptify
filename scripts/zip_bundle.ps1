Write-Host 'Zipping Semptify bundle...'
Compress-Archive -Path 'C:\Semptify\Semptify-FastAPI\*' -DestinationPath 'C:\Semptify\Semptify-FastAPI\SemptifyBundle.zip' -Force
