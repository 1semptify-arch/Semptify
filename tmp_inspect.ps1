$files = @('welcome','tenant_dashboard','documents','timeline','calendar','advocate','admin','legal','law_library','vault','complaints','auto_analysis_summary','home','tenant_help','error')
foreach ($f in $files) {
    $path = "app\templates\pages\$f.html"
    if (Test-Path $path) {
        $content = Get-Content $path -TotalCount 3
        $lines = (Get-Content $path).Count
        $first = $content[0].Trim()
        Write-Host ("{0,-25} {1,5} lines | {2}" -f $f, $lines, $first)
    } else {
        Write-Host ("{0,-25} MISSING" -f $f)
    }
}
