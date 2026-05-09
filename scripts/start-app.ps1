param(
    [switch]$NoOpen
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend"
$VenvPython = Join-Path $Root "venv\Scripts\python.exe"
$AppUrl = "http://127.0.0.1:5173"

function Test-CommandAvailable {
    param([string]$CommandName)
    return $null -ne (Get-Command $CommandName -ErrorAction SilentlyContinue)
}

function Test-PortOpen {
    param([int]$Port)
    return $null -ne (Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
        Where-Object { $_.State -eq "Listen" })
}

Write-Host "Starting GLF Assessment Scheduler..." -ForegroundColor Cyan

if (-not (Test-Path $BackendDir)) {
    throw "Cannot find backend folder: $BackendDir"
}

if (-not (Test-Path $FrontendDir)) {
    throw "Cannot find frontend folder: $FrontendDir"
}

if (-not (Test-Path $VenvPython)) {
    if (-not (Test-CommandAvailable "python")) {
        throw "Python is not installed or is not available in PATH. Install Python, then run this file again."
    }

    Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
    Push-Location $Root
    try {
        python -m venv venv
    }
    finally {
        Pop-Location
    }
}

Write-Host "Checking Python packages..." -ForegroundColor Yellow
Push-Location $BackendDir
try {
    & $VenvPython -m pip install -r requirements.txt
}
finally {
    Pop-Location
}

if (-not (Test-CommandAvailable "npm")) {
    throw "Node.js/npm is not installed or is not available in PATH. Install Node.js, then run this file again."
}

if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
    Write-Host "Installing frontend packages..." -ForegroundColor Yellow
    Push-Location $FrontendDir
    try {
        npm install
    }
    finally {
        Pop-Location
    }
}

if (Test-PortOpen 8000) {
    Write-Host "Backend already appears to be running on port 8000." -ForegroundColor Green
}
else {
    Write-Host "Starting backend on http://127.0.0.1:8000 ..." -ForegroundColor Green
    Start-Process powershell -ArgumentList @(
        "-NoProfile",
        "-NoExit",
        "-Command",
        "Set-Location '$BackendDir'; &'$VenvPython' -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
    )
}

if (Test-PortOpen 5173) {
    Write-Host "Frontend already appears to be running on port 5173." -ForegroundColor Green
}
else {
    Write-Host "Starting frontend on $AppUrl ..." -ForegroundColor Green
    Start-Process powershell -ArgumentList @(
        "-NoProfile",
        "-NoExit",
        "-Command",
        "Set-Location '$FrontendDir'; npm run dev -- --port 5173"
    )
}

if (-not $NoOpen) {
    Start-Sleep -Seconds 3
    Start-Process $AppUrl
}

Write-Host ""
Write-Host "GLF Assessment Scheduler is starting." -ForegroundColor Cyan
Write-Host "Open $AppUrl if the browser does not open automatically."
Write-Host "Keep the backend and frontend windows open while using the app."
