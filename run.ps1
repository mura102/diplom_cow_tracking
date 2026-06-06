Set-Location $PSScriptRoot
if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Creating virtual environment..."
    py -3 -m venv .venv
    .\.venv\Scripts\pip install -r requirements.txt
}
$env:KMP_DUPLICATE_LIB_OK = "TRUE"
& ".\.venv\Scripts\python.exe" main.py
