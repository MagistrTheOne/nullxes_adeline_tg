# One-shot start: rebuild miniapp + bot + auto localhost.run tunnel
#
#   cd D:\NULLXES\NULLXES_HUB_BOT
#   .\scripts\start.ps1

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "Stopping old bot / tunnel…"

Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match 'main\.py|NULLXES_HUB_BOT' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

Get-CimInstance Win32_Process -Filter "Name='ssh.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match 'localhost\.run' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

$pids = (Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue).OwningProcess | Select-Object -Unique
foreach ($p in $pids) {
    Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
}

Start-Sleep -Seconds 1

Write-Host "Building miniapp…"
Push-Location .\miniapp
npm run build
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    throw "miniapp build failed"
}
Pop-Location

$env:START_TUNNEL = if ($env:START_TUNNEL) { $env:START_TUNNEL } else { "1" }
$env:PYTHONUNBUFFERED = "1"
Write-Host "Starting bot (START_TUNNEL=$env:START_TUNNEL)."
Write-Host "Дождись в логе: «Туннель готов: https://….lhr.life» → в Telegram /start"
.\venv\Scripts\python.exe main.py
