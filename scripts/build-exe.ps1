param(
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend"
$VenvPython = Join-Path $Root "venv\Scripts\python.exe"
$SpecFile = Join-Path $Root "GLF Scheduler.spec"
$ExeFile = Join-Path $Root "dist\GLF Assessment Scheduler.exe"

function Test-CommandAvailable {
    param([string]$CommandName)
    return $null -ne (Get-Command $CommandName -ErrorAction SilentlyContinue)
}

function Invoke-Native {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$Command,
        [string]$FailureMessage = "Command failed."
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw $FailureMessage
    }
}

if (-not (Test-Path $VenvPython)) {
    if (-not (Test-CommandAvailable "python")) {
        throw "Python is required on the build computer to create the .exe."
    }

    Push-Location $Root
    try {
        python -m venv venv
    }
    finally {
        Pop-Location
    }
}

if (-not (Test-CommandAvailable "npm")) {
    throw "Node.js/npm is required on the build computer to compile the frontend."
}

if (-not $SkipInstall) {
    Push-Location $BackendDir
    try {
        Invoke-Native { & $VenvPython -m pip install -r requirements.txt } "Failed to install backend dependencies."
        Invoke-Native { & $VenvPython -m pip install pyinstaller } "Failed to install PyInstaller."
    }
    finally {
        Pop-Location
    }

    Push-Location $FrontendDir
    try {
        Invoke-Native { npm install } "Failed to install frontend dependencies."
    }
    finally {
        Pop-Location
    }
}

Push-Location $FrontendDir
try {
    Invoke-Native { npm run build } "Failed to build the frontend."
}
finally {
    Pop-Location
}

Push-Location $Root
try {
    Invoke-Native { & $VenvPython -m PyInstaller --clean $SpecFile } "Failed to build the executable."
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "Created standalone application:" -ForegroundColor Green
Write-Host $ExeFile -ForegroundColor Cyan
Write-Host ""
Write-Host "Copy this .exe to another Windows computer and run it there."
