param(
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw ".venv is missing. Run .\run.ps1 once before building."
}

& $python -m pip install -r requirements-build.txt
& $python -m pytest -q

& $python -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name otp_autofill `
    --hidden-import win32timezone `
    --collect-submodules pywinauto `
    main.py

& $python -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name chrome_watcher `
    chrome_watcher.py

& $python -m PyInstaller --noconfirm --clean --onefile --console `
    --name otp_diagnostics `
    --hidden-import win32timezone `
    --collect-submodules pywinauto `
    main.py

if ($SkipInstaller) {
    Write-Host "Portable executables were created in .\dist."
    exit 0
}

$isccCandidates = @(
    (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
    (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe")
)
$iscc = $isccCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $iscc) {
    throw "Inno Setup 6 was not found. Install it, then run .\build_exe.ps1 again. Portable EXEs are already available in .\dist."
}

& $iscc (Join-Path $PSScriptRoot "installer\OutlookOtpAutofill.iss")
Write-Host "Installer created under .\installer\Output."
