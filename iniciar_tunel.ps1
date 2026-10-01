$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
$env:Path = "$userPath;$machinePath"
$cloudflared = Get-Command cloudflared -ErrorAction SilentlyContinue

if (-not $cloudflared) {
    Write-Host "cloudflared esta instalado, pero esta terminal no lo encuentra." -ForegroundColor Yellow
    Write-Host "Cierra esta PowerShell, abre una nueva y vuelve a ejecutar .\iniciar_tunel.ps1"
    Write-Host "Si sigue ocurriendo, ejecuta: winget install --id Cloudflare.cloudflared --exact"
    exit 1
}

if (-not (Test-NetConnection -ComputerName 127.0.0.1 -Port 8000 -InformationLevel Quiet)) {
    $pythonCandidates = @(
        (Join-Path $projectRoot "venv\Scripts\python.exe"),
        (Join-Path (Split-Path $projectRoot -Parent) ".venv\Scripts\python.exe")
    )
    $python = $pythonCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    if ($python) {
        Start-Process -FilePath $python -ArgumentList "-m uvicorn main:app --host 0.0.0.0 --port 8000" -WorkingDirectory $projectRoot
    } else {
        Write-Host "No encontre venv ni .venv. Activa tu entorno o inicia uvicorn manualmente antes del tunel." -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "Uvicorn ya esta activo en el puerto 8000; reutilizando esa instancia." -ForegroundColor Green
}

Write-Host "Abriendo tunel publico hacia http://127.0.0.1:8000 ..." -ForegroundColor Cyan
Write-Host "Copia la URL https://...trycloudflare.com que aparezca y abre /login desde tu celular."
& $cloudflared.Source tunnel --url http://127.0.0.1:8000
