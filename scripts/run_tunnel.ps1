# Cloudflare quick tunnel -> local Mini App on :8080
# Prefer http2: quic often times out behind VPN/proxy on Windows.
#
# Run elevated (Admin):
#   cd D:\NULLXES\NULLXES_HUB_BOT
#   .\scripts\run_tunnel.ps1

$ErrorActionPreference = "Continue"
$Gateway = "192.168.5.1"

$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).
    IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Нужен Admin PowerShell — иначе route add не сработает, а Happ снова заберёт edge." -ForegroundColor Yellow
    Write-Host "Правой кнопкой по PowerShell -> Запуск от имени администратора, затем:"
    Write-Host "  cd D:\NULLXES\NULLXES_HUB_BOT"
    Write-Host "  .\scripts\run_tunnel.ps1"
    exit 1
}

# Bypass Happ (10.6.7.x) for Cloudflare Tunnel edge
$routes = @(
    @{ Net = "198.41.192.0"; Mask = "255.255.255.0" },
    @{ Net = "198.41.200.0"; Mask = "255.255.255.0" },
    @{ Net = "197.234.240.0"; Mask = "255.255.252.0" }
)

foreach ($r in $routes) {
    # delete may fail if route missing — ignore
    cmd /c "route delete $($r.Net) >nul 2>&1"
    $out = cmd /c "route add $($r.Net) mask $($r.Mask) $Gateway metric 1"
    Write-Host "route $($r.Net) mask $($r.Mask) via $Gateway -> $out"
}

Write-Host ""
Write-Host "Starting cloudflared (http2) -> http://127.0.0.1:8080 ..."
cloudflared tunnel --protocol http2 --url http://127.0.0.1:8080
