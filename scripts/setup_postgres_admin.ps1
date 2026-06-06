# Запустите от имени администратора (ПКМ -> Запуск от имени администратора)
$pgData = "D:\Program Files\PostGRESQL\data"
$pgBin  = "D:\Program Files\PostGRESQL\bin"
$hba    = Join-Path $pgData "pg_hba.conf"
$trust  = "host    all             all             127.0.0.1/32            trust"
$pwd    = "123456789"
$db     = "cow_tracking_db"

$lines = [System.IO.File]::ReadAllLines($hba)
$newLines = New-Object System.Collections.Generic.List[string]
$inserted = $false
foreach ($line in $lines) {
    if (-not $inserted -and $line -match '^# TYPE\s+DATABASE') {
        $newLines.Add($line)
        $newLines.Add($trust)
        $inserted = $true
    } else {
        $newLines.Add($line)
    }
}
if (-not $inserted) { $newLines.Insert(0, $trust) }
[System.IO.File]::WriteAllLines($hba, $newLines)

& "$pgBin\pg_ctl.exe" reload -D $pgData
Start-Sleep -Seconds 1

& "$pgBin\psql.exe" -U postgres -h 127.0.0.1 -d postgres -c "SELECT 1 FROM pg_database WHERE datname='$db'" | Out-Null
if ($LASTEXITCODE -ne 0) { throw "psql failed" }
$check = & "$pgBin\psql.exe" -U postgres -h 127.0.0.1 -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$db'"
if ($check -ne "1") {
    & "$pgBin\psql.exe" -U postgres -h 127.0.0.1 -d postgres -c "CREATE DATABASE $db ENCODING 'UTF8';"
}
& "$pgBin\psql.exe" -U postgres -h 127.0.0.1 -d postgres -c "ALTER USER postgres WITH PASSWORD '$pwd';"

# Удалить строку trust
$lines2 = [System.IO.File]::ReadAllLines($hba) | Where-Object { $_ -ne $trust }
[System.IO.File]::WriteAllLines($hba, $lines2)
& "$pgBin\pg_ctl.exe" reload -D $pgData

Write-Host "Готово. DB=$db  пароль postgres=$pwd"
