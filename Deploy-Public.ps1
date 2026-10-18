#Requires -RunAsAdministrator

$ErrorActionPreference = "Stop"
$port = 8681
$ruleName = "Yealink Phonebook TCP $port"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker is not installed or is not available in PATH."
}

Push-Location $PSScriptRoot
try {
    docker compose up -d --build
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose deployment failed."
    }
}
finally {
    Pop-Location
}

Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue |
    Remove-NetFirewallRule

New-NetFirewallRule `
    -DisplayName $ruleName `
    -Direction Inbound `
    -Action Allow `
    -Protocol TCP `
    -LocalPort $port `
    -Profile Any `
    -RemoteAddress Any | Out-Null

$healthy = $false
for ($attempt = 1; $attempt -le 15 -and -not $healthy; $attempt++) {
    try {
        $response = Invoke-RestMethod "http://127.0.0.1:$port/api" -TimeoutSec 2
        $healthy = $response.status -eq "ok"
    }
    catch {
        Start-Sleep -Seconds 2
    }
}

if (-not $healthy) {
    throw "Port $port is allowed, but the application health check failed. Run 'docker compose logs phonebook'."
}

$lanAddresses = Get-NetIPConfiguration |
    Where-Object { $_.IPv4DefaultGateway -ne $null } |
    ForEach-Object { $_.IPv4Address.IPAddress }

Write-Host "Phonebook is running and Windows Firewall allows TCP $port from any address." -ForegroundColor Green
$lanAddresses | ForEach-Object { Write-Host "LAN URL: http://${_}:$port" }

try {
    $publicAddress = (Invoke-RestMethod "https://api.ipify.org" -TimeoutSec 5).Trim()
    Write-Host "Candidate public URL: http://${publicAddress}:$port"
}
catch {
    Write-Warning "The public IP address could not be detected."
}

Write-Warning "If this PC is behind a router, forward TCP $port to this PC's LAN IP on port $port. PowerShell cannot configure every router or bypass ISP CGNAT."
Write-Warning "This application has no authentication or TLS; public visitors can view and change the phonebook."
