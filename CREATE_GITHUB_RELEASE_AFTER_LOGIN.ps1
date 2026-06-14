$ErrorActionPreference = "Stop"

$repo = "a1553189184-stack/SCI"
$tag = "v1.0-reviewer-package"
$title = "CXR public-subset validation reviewer package v1.0"
$notes = "RELEASE_NOTES_v1.0-reviewer-package.md"

$machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$env:Path = "$machinePath;$userPath"

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI is not available. Install it with: winget install --id GitHub.cli -e"
}

try {
    gh auth status
} catch {
    gh auth login --hostname github.com --git-protocol https --web
}

gh release create $tag --repo $repo --title $title --notes-file $notes --verify-tag

Write-Host "Release created: https://github.com/$repo/releases/tag/$tag"

