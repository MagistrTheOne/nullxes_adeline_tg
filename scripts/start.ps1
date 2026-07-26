# One-shot start: bot + auto localhost.run tunnel (START_TUNNEL=1 by default)
#
#   cd D:\NULLXES\NULLXES_HUB_BOT
#   .\scripts\start.ps1

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

# free port 8080
$pids = (Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue).OwningProcess | Select-Object -Unique
foreach ($p in $pids) {
    Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
}

# drop stale localhost.run ssh
Get-CimInstance Win32_Process -Filter "Name='ssh.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match 'localhost\.run' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

if (-not (Test-Path ".\miniapp\dist\index.html")) {
    Write-Host "Building miniapp…"
    Push-Location .\miniapp
    npm run build
    Pop-Location
}

$env:START_TUNNEL = if ($env:START_TUNNEL) { $env:START_TUNNEL } else { "1" }
Write-Host "Starting bot (START_TUNNEL=$env:START_TUNNEL). Tunnel URL появится в логе и в .env"
.\venv\Scripts\python.exe main.py
