#requires -RunAsAdministrator

param(
    [string]$ServiceName = 'postgresql-x64-16',
    [string]$PgBinPath = 'C:\Program Files\PostgreSQL\16\bin',
    [string]$PgDataPath = 'C:\Program Files\PostgreSQL\16\data',
    [string]$PostgresUser = 'postgres',
    [string]$PostgresPassword = 'postgres',
    [string]$SemptifyUser = 'semptify',
    [string]$SemptifyPassword = 'semptify',
    [string]$SemptifyDatabase = 'semptify',
    [int]$Port = 5432
)

$ErrorActionPreference = 'Stop'

function Write-Info($message) {
    Write-Host "[INFO] $message" -ForegroundColor Cyan
}

function Write-Ok($message) {
    Write-Host "[OK]   $message" -ForegroundColor Green
}

function Write-Warn($message) {
    Write-Host "[WARN] $message" -ForegroundColor Yellow
}

function Set-LocalAuthMethod {
    param(
        [string[]]$Lines,
        [string]$Method
    )

    $updated = New-Object System.Collections.Generic.List[string]
    foreach ($line in $Lines) {
        if ($line -match '^local\s+all\s+all\s+') {
            $updated.Add('local   all             all                                     ' + $Method)
            continue
        }

        if ($line -match '^host\s+all\s+all\s+127\.0\.0\.1/32\s+') {
            $updated.Add('host    all             all             127.0.0.1/32            ' + $Method)
            continue
        }

        if ($line -match '^host\s+all\s+all\s+::1/128\s+') {
            $updated.Add('host    all             all             ::1/128                 ' + $Method)
            continue
        }

        $updated.Add($line)
    }

    return $updated
}

function Invoke-Psql {
    param(
        [string]$Database,
        [string]$Sql,
        [string]$User = $PostgresUser
    )

    $psqlPath = Join-Path $PgBinPath 'psql.exe'
    $output = & $psqlPath -h 127.0.0.1 -p $Port -U $User -d $Database -v ON_ERROR_STOP=1 -c $Sql 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw ("psql failed for user '{0}' on database '{1}': {2}" -f $User, $Database, ($output -join "`n"))
    }

    return $output
}

function Invoke-PsqlScalar {
    param(
        [string]$Database,
        [string]$Sql,
        [string]$User = $PostgresUser
    )

    $psqlPath = Join-Path $PgBinPath 'psql.exe'
    $output = & $psqlPath -h 127.0.0.1 -p $Port -U $User -d $Database -tAc $Sql 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw ("psql scalar query failed for user '{0}' on database '{1}': {2}" -f $User, $Database, ($output -join "`n"))
    }

    return ($output | Out-String).Trim()
}

$psqlPath = Join-Path $PgBinPath 'psql.exe'
$pgHbaPath = Join-Path $PgDataPath 'pg_hba.conf'

if (-not (Test-Path $psqlPath)) {
    throw "psql.exe not found at $psqlPath"
}

if (-not (Test-Path $pgHbaPath)) {
    throw "pg_hba.conf not found at $pgHbaPath"
}

$originalPgHbaLines = Get-Content $pgHbaPath
$originalPgHba = $originalPgHbaLines -join [Environment]::NewLine

$temporaryPgHbaLines = Set-LocalAuthMethod -Lines $originalPgHbaLines -Method 'trust'
$temporaryPgHba = $temporaryPgHbaLines -join [Environment]::NewLine

if ($temporaryPgHba -eq $originalPgHba) {
    Write-Warn 'pg_hba.conf did not change. Check localhost auth lines if reset fails.'
}

Write-Info 'Temporarily allowing trusted localhost auth...'
Set-Content -Path $pgHbaPath -Value $temporaryPgHbaLines -Encoding ascii
Restart-Service -Name $ServiceName -Force
Write-Ok 'PostgreSQL restarted with temporary localhost trust auth'

try {
    Write-Info 'Resetting postgres superuser password...'
    Invoke-Psql -Database 'postgres' -Sql "ALTER USER $PostgresUser WITH PASSWORD '$PostgresPassword';"
    Write-Ok 'postgres password updated'

    Write-Info 'Creating or updating semptify role...'
    $roleExists = Invoke-PsqlScalar -Database 'postgres' -Sql "SELECT 1 FROM pg_roles WHERE rolname = '$SemptifyUser'"
    if ($roleExists -eq '1') {
        Invoke-Psql -Database 'postgres' -Sql "ALTER ROLE $SemptifyUser WITH LOGIN PASSWORD '$SemptifyPassword' CREATEDB;"
    }
    else {
        Invoke-Psql -Database 'postgres' -Sql "CREATE ROLE $SemptifyUser LOGIN PASSWORD '$SemptifyPassword' CREATEDB;"
    }
    Write-Ok 'semptify role is ready'

    Write-Info 'Ensuring semptify database exists...'
    $dbExists = Invoke-PsqlScalar -Database 'postgres' -Sql "SELECT 1 FROM pg_database WHERE datname = '$SemptifyDatabase'"
    if ($dbExists -ne '1') {
        Invoke-Psql -Database 'postgres' -Sql "CREATE DATABASE $SemptifyDatabase OWNER $SemptifyUser;"
        Write-Ok 'semptify database created'
    } else {
        Write-Ok 'semptify database already exists'
    }

    Write-Info 'Ensuring semptify owns database and public schema...'
    Invoke-Psql -Database 'postgres' -Sql "ALTER DATABASE $SemptifyDatabase OWNER TO $SemptifyUser;"
    Invoke-Psql -Database $SemptifyDatabase -Sql "ALTER SCHEMA public OWNER TO $SemptifyUser;"
    Write-Ok 'Ownership aligned'

    Write-Info 'Granting schema permissions required for table creation...'
    Invoke-Psql -Database $SemptifyDatabase -Sql "GRANT USAGE, CREATE ON SCHEMA public TO $SemptifyUser;"
    Write-Ok 'Schema permissions granted'

    Invoke-Psql -Database 'postgres' -Sql "GRANT ALL PRIVILEGES ON DATABASE $SemptifyDatabase TO $SemptifyUser;"
    Write-Ok 'Privileges granted'
}
finally {
    Write-Info 'Restoring secure localhost auth...'
    Set-Content -Path $pgHbaPath -Value $originalPgHbaLines -Encoding ascii
    Restart-Service -Name $ServiceName -Force
    Write-Ok 'Secure auth restored'
}

Write-Info 'Testing semptify login on localhost:5432...'
$env:PGPASSWORD = $SemptifyPassword
try {
    $testOutput = & $psqlPath -h 127.0.0.1 -p $Port -U $SemptifyUser -d $SemptifyDatabase -c 'SELECT current_user, current_database();' 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw ("semptify login test failed: {0}" -f ($testOutput -join "`n"))
    }

    $testOutput
}
finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}

Write-Host ''
Write-Ok "Local PostgreSQL is configured for Semptify on localhost:$Port"
$databaseUrl = "postgresql+asyncpg://${SemptifyUser}:${SemptifyPassword}@localhost:${Port}/${SemptifyDatabase}"
Write-Host "DATABASE_URL=$databaseUrl" -ForegroundColor White