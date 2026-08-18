$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv")) {
    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if (-not $launcher) {
        throw "Python 3.11+ was not found. Install Python from https://www.python.org/downloads/windows/ and enable the Python launcher."
    }
    try {
        & py -3 -m venv .venv
    }
    catch {
        throw "Python could not start. Finish the Python 3.11+ installation, reopen PowerShell, and run this script again."
    }
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    throw "The .venv folder is incomplete. Remove only this project's .venv folder and run .\run.ps1 again."
}

& .\.venv\Scripts\python.exe -c "import sys; assert sys.version_info >= (3, 11), 'Python 3.11 or newer is required'"
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe main.py @args
