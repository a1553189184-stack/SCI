param(
    [string]$CheckpointZip,
    [string]$Repository = "a1553189184-stack/SCI",
    [string]$Tag = "v1.0-reviewer-package",
    [string]$Title = "CXR public-subset validation reviewer package v1.0"
)

$ErrorActionPreference = "Stop"

$machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$env:Path = "$machinePath;$userPath"

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI is not available. Install it with: winget install --id GitHub.cli -e"
}

if (-not $CheckpointZip) {
    throw "Pass -CheckpointZip with the checkpoint archive path."
}

if (-not (Test-Path $CheckpointZip)) {
    throw "Checkpoint archive not found: $CheckpointZip"
}

try {
    gh auth status
} catch {
    gh auth login --hostname github.com --git-protocol https --web
}

$releaseExists = $true
try {
    gh release view $Tag --repo $Repository *> $null
} catch {
    $releaseExists = $false
}

if (-not $releaseExists) {
    gh release create $Tag `
        --repo $Repository `
        --title $Title `
        --notes-file RELEASE_NOTES_v1.0-reviewer-package.md `
        --verify-tag
}

gh release upload $Tag `
    $CheckpointZip `
    release_assets/CHECKPOINT_MANIFEST_v1.0-reviewer-package.csv `
    release_assets/SHA256SUMS_checkpoints_v1.0-reviewer-package.txt `
    release_assets/RELEASE_ASSET_MANIFEST_v1.0-reviewer-package.csv `
    --repo $Repository `
    --clobber

Write-Host "Release ready: https://github.com/$Repository/releases/tag/$Tag"
