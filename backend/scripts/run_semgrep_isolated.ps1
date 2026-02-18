param(
    [string]$Output = "audit42_static/semgrep_results_isolated.json"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repoRoot

$semgrepVenv = Join-Path $repoRoot ".venv-semgrep"
$venvPython = Join-Path $semgrepVenv "Scripts\python.exe"
$semgrepExe = Join-Path $semgrepVenv "Scripts\semgrep.exe"

if (-not (Test-Path $venvPython)) {
    py -3 -m venv $semgrepVenv
}

& $venvPython -m pip install --upgrade pip | Out-Null
& $venvPython -m pip install "semgrep==1.152.0" | Out-Null

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$semgrepArgs = @(
    "--config",
    ".semgrep/",
    "backend/app/",
    "frontend/src/",
    "docker-compose*.yml",
    ".github/workflows/",
    "--json",
    "--output",
    $Output
)

& $semgrepExe @semgrepArgs

Write-Host "Semgrep completed with isolated environment: $Output"
