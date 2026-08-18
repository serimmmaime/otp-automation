param(
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot
$watcher = Join-Path $projectRoot "chrome_watcher.py"
$startupFolder = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startupFolder "Outlook OTP Autofill.lnk"

if ($Uninstall) {
    if (Test-Path -LiteralPath $shortcutPath) {
        Remove-Item -LiteralPath $shortcutPath -Force
    }
    Write-Host "Chrome automatic startup was removed."
    exit 0
}

$pythonw = Join-Path $projectRoot ".venv\Scripts\pythonw.exe"
if (-not (Test-Path -LiteralPath $pythonw)) {
    throw ".venv is missing. Run .\run.ps1 once before installing automatic startup."
}
if (-not (Test-Path -LiteralPath $watcher)) {
    throw "chrome_watcher.py is missing."
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $pythonw
$shortcut.Arguments = "`"$watcher`""
$shortcut.WorkingDirectory = $projectRoot
$shortcut.Description = "Start Outlook OTP Autofill while Chrome is running"
$shortcut.Save()

Write-Host "Chrome automatic startup was installed."
Write-Host "It will take effect at the next Windows sign-in."
