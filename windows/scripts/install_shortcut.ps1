# Creates "Dictado.lnk" on Desktop + Start Menu so the app can be pinned to taskbar.
# Run from windows/ folder:  .\scripts\install_shortcut.ps1

$ErrorActionPreference = "Stop"

# Resolve paths relative to repo
$repoWin = (Get-Item -Path "$PSScriptRoot\..").FullName
$python = Join-Path $repoWin ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Error "Python venv not found at $python — run 'python -m venv .venv' and install deps first."
    exit 1
}

$desktop = [Environment]::GetFolderPath('Desktop')
$startMenu = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs"

$targets = @(
    (Join-Path $desktop "Dictado.lnk"),
    (Join-Path $startMenu "Dictado.lnk")
)

$ws = New-Object -ComObject WScript.Shell
foreach ($p in $targets) {
    $s = $ws.CreateShortcut($p)
    $s.TargetPath = $python
    $s.Arguments = "-m dictado.main"
    $s.WorkingDirectory = $repoWin
    $s.WindowStyle = 7  # 7 = minimized
    $s.IconLocation = "$python,0"
    $s.Description = "Dictado - push-to-talk dictation"
    $s.Save()
    Write-Output "created: $p"
}

Write-Output ""
Write-Output "To pin to taskbar (Windows 11):"
Write-Output "  1. Double-click 'Dictado' on Desktop — app launches minimized"
Write-Output "  2. Right-click the taskbar icon → Pin to taskbar"
