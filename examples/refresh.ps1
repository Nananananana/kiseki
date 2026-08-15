# Runs one refresh: records -> ingest -> build -> models -> profile.
# Personal paths are parameters; nothing here is machine-specific.
param(
    [Parameter(Mandatory = $true)][string]$Source,
    [Parameter(Mandatory = $true)][string]$RunDir,
    [Parameter(Mandatory = $true)][string]$Owner,
    [string]$Offset = "+09:00",
    [switch]$SkipModels
)
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

uv run kiseki-ingest $Source $RunDir `
    --owner $Owner --platform ios --default-offset $Offset `
    --time-fallback-mtime
if ($LASTEXITCODE -ne 0) { throw "kiseki-ingest failed" }

uv run kiseki ingest (Join-Path $RunDir "photo-records.json")
if ($LASTEXITCODE -ne 0) { throw "ingest failed" }
uv run kiseki build
if ($LASTEXITCODE -ne 0) { throw "build failed" }

if (-not $SkipModels) {
    uv run kiseki caption
    uv run kiseki subjects
    uv run kiseki themes
}

uv run kiseki profile
uv run kiseki report
