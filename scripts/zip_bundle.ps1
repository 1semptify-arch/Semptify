Write-Host 'Zipping Semptify bundle...'
Compress-Archive -Path 'E:\master-repo\sources\app-semptify-fastapi\*' -DestinationPath 'E:\master-repo\sources\app-semptify-fastapi\SemptifyBundle.zip' -Force
