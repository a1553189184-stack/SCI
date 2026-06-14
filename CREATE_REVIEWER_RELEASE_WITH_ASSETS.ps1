param(
    [string]$CheckpointZip,
    [string]$SourceZip,
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

if ($SourceZip -and -not (Test-Path $SourceZip)) {
    throw "Source archive not found: $SourceZip"
}

$didSetTemporaryToken = $false
if (-not $env:GH_TOKEN) {
    $credentialInput = "protocol=https`nhost=github.com`n`n"
    $credentialOutput = $credentialInput | git credential fill
    $credentialToken = $null
    foreach ($line in $credentialOutput) {
        if ($line -like "password=*") {
            $credentialToken = $line.Substring(9)
        }
    }
    if ($credentialToken) {
        $env:GH_TOKEN = $credentialToken
        $didSetTemporaryToken = $true
    } else {
        gh auth login --hostname github.com --git-protocol https --web --clipboard
    }
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

$assetFiles = @(
    $CheckpointZip,
    "release_assets/CHECKPOINT_MANIFEST_v1.0-reviewer-package.csv",
    "release_assets/SHA256SUMS_checkpoints_v1.0-reviewer-package.txt",
    "release_assets/RELEASE_ASSET_MANIFEST_v1.0-reviewer-package.csv"
)

if ($SourceZip) {
    $assetFiles = @($SourceZip) + $assetFiles
}

gh release upload $Tag $assetFiles --repo $Repository --clobber

Write-Host "Release ready: https://github.com/$Repository/releases/tag/$Tag"

if ($didSetTemporaryToken) {
    $env:GH_TOKEN = $null
}
