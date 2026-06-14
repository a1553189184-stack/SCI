# GitHub Upload Instructions

This repository is the GitHub-safe public/reviewer subset of the CXR generalizability, calibration, and explainability project.

## Recommended repository

- Owner: `a1553189184-stack`
- Repository name: `cxr-public-subset-chest-radiograph-validation`
- Recommended visibility before submission: private

## What is included

- Modular Python source code and scripts.
- YAML/environment configuration.
- De-identified metadata, split files, prediction CSVs, metric tables, figure source data, logs, and manuscript-ready figures.
- Final manuscript/supporting document artifacts.

## What is intentionally omitted

- Raw NIH ChestX-ray14 and VinDr-CXR images.
- Model checkpoints and other large binary artifacts.
- The large reproducibility zip package.
- Local absolute workstation paths.

These items should be distributed through the original public dataset portals, a controlled repository, a release asset, or an institutional data-sharing route as appropriate.

## Upload with GitHub CLI

If GitHub CLI is installed and authenticated:

```powershell
cd <LOCAL_REPO>
gh auth login
gh repo create a1553189184-stack/cxr-public-subset-chest-radiograph-validation --private --source . --remote origin --push
```

## Upload after creating the GitHub repository manually

1. Create an empty repository at:

   `https://github.com/a1553189184-stack/cxr-public-subset-chest-radiograph-validation`

2. Push this local repository:

```powershell
cd <LOCAL_REPO>
git remote set-url origin https://github.com/a1553189184-stack/cxr-public-subset-chest-radiograph-validation.git
git push -u origin main
```

## If Git asks for credentials

Use a GitHub personal access token with repository permissions, or install GitHub CLI:

```powershell
winget install --id GitHub.cli
gh auth login
git push -u origin main
```
