# ============================================================================
# Setup PostgreSQL Extensions for Semptify
# Run this once to install required database extensions
# ============================================================================

$psqlPath = 'C:\Program Files\PostgreSQL\16\bin\psql.exe'
$pgHost = 'localhost'
$pgPort = 5432
$pgUser = 'postgres'
$semptifyUser = 'semptify'
$semptifyPassword = 'semptify'
$semptifyDb = 'semptify'

Write-Host ""
Write-Host "========== PostgreSQL Extension Setup for Semptify ==========" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $psqlPath)) {
    Write-Host "ERROR: psql not found at $psqlPath" -ForegroundColor Red
    Write-Host "Please install PostgreSQL 16 or update the path." -ForegroundColor Yellow
    exit 1
}

# Function to run psql query
function Run-PostgresQuery {
    param (
        [string]$Query,
        [string]$Database = 'postgres',
        [string]$User = $pgUser,
        [string]$Host = $pgHost,
        [string]$Port = $pgPort
    )
    
    & $psqlPath -h $Host -p $Port -U $User -d $Database -c $Query 2>&1
    return $LASTEXITCODE -eq 0
}

# Step 1: Create semptify user if it doesn't exist
Write-Host "[1] Checking/creating semptify user..." -ForegroundColor Yellow

$userCheck = & $psqlPath -h $pgHost -p $pgPort -U $pgUser -d postgres -t -c "SELECT 1 FROM pg_user WHERE usename = '$semptifyUser'" 2>$null
if ($userCheck -notmatch '1') {
    Write-Host "    Creating user: $semptifyUser"
    Run-PostgresQuery "CREATE USER $semptifyUser WITH PASSWORD '$semptifyPassword' CREATEDB;" | Out-Null
    Write-Host "    [OK] User created" -ForegroundColor Green
} else {
    Write-Host "    [OK] User already exists" -ForegroundColor Green
}

# Step 2: Create semptify database if it doesn't exist
Write-Host "[2] Checking/creating semptify database..." -ForegroundColor Yellow

$dbCheck = & $psqlPath -h $pgHost -p $pgPort -U $pgUser -d postgres -t -c "SELECT 1 FROM pg_database WHERE datname = '$semptifyDb'" 2>$null
if ($dbCheck -notmatch '1') {
    Write-Host "    Creating database: $semptifyDb"
    Run-PostgresQuery "CREATE DATABASE $semptifyDb OWNER $semptifyUser;" postgres $pgUser | Out-Null
    Write-Host "    [OK] Database created" -ForegroundColor Green
} else {
    Write-Host "    [OK] Database already exists" -ForegroundColor Green
}

# Step 3: Grant privileges
Write-Host "[3] Granting privileges to $semptifyUser..." -ForegroundColor Yellow

Run-PostgresQuery "GRANT ALL PRIVILEGES ON DATABASE $semptifyDb TO $semptifyUser;" postgres $pgUser | Out-Null
Write-Host "    [OK] Privileges granted" -ForegroundColor Green

# Step 4: Install extensions in semptify database
Write-Host "[4] Installing PostgreSQL extensions..." -ForegroundColor Yellow

$extensions = @(
    'uuid-ossp',      # UUID generation
    'pg_trgm',        # Trigram matching for text search
    'pgcrypto',       # Encryption and hashing
    'btree_gin',      # GIN index support
    'btree_gist'      # GIST index support
)

foreach ($ext in $extensions) {
    $extCheck = & $psqlPath -h $pgHost -p $pgPort -U $pgUser -d $semptifyDb -t -c "SELECT 1 FROM pg_extension WHERE extname = '$ext'" 2>$null
    
    if ($extCheck -match '1') {
        Write-Host "    [OK] $ext (already installed)" -ForegroundColor Green
    } else {
        & $psqlPath -h $pgHost -p $pgPort -U $pgUser -d $semptifyDb -c "CREATE EXTENSION IF NOT EXISTS $ext;" 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "    [OK] $ext (installed)" -ForegroundColor Green
        } else {
            Write-Host "    [!] $ext (skipped - may be optional)" -ForegroundColor Yellow
        }
    }
}

# Step 5: Verify connection with semptify user
Write-Host "[5] Testing connection as $semptifyUser..." -ForegroundColor Yellow

$env:PGPASSWORD = $semptifyPassword
$connTest = & $psqlPath -h $pgHost -p $pgPort -U $semptifyUser -d $semptifyDb -c "SELECT version();" 2>&1 | Select-Object -First 1
$env:PGPASSWORD = $null

if ($connTest -match 'PostgreSQL') {
    Write-Host "    [OK] Connection successful" -ForegroundColor Green
    Write-Host "         $connTest" -ForegroundColor DarkGray
} else {
    Write-Host "    [FAIL] Connection failed" -ForegroundColor Red
    Write-Host "           $connTest" -ForegroundColor DarkGray
    exit 1
}

Write-Host ""
Write-Host "========== Setup Complete ==========" -ForegroundColor Green
Write-Host ""
Write-Host "Connection string for Semptify:" -ForegroundColor Cyan
$dbUrl = "postgresql+asyncpg://${semptifyUser}:${semptifyPassword}@${pgHost}:${pgPort}/${semptifyDb}"
Write-Host "  $dbUrl" -ForegroundColor White
Write-Host ""
Write-Host "Add to .env file:" -ForegroundColor Cyan
Write-Host "  DATABASE_URL=$dbUrl" -ForegroundColor White
Write-Host ""
Read-Host "Press Enter to close"
