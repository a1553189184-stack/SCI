# Release and Checkpoint Sharing Plan

This plan defines how to turn the GitHub repository into a stronger reviewer-facing reproducibility package.

## Current Status

- GitHub repository: `https://github.com/a1553189184-stack/SCI`
- Current public-subset package commit: see `git log --oneline`
- Git-tracked files: code, configs, derived metadata, splits, predictions, metrics, figures, final manuscript files, logs, and environment reports
- Not tracked in normal Git: raw images, virtual environment files, large zip archives, and model checkpoint `.pt` files

## Checkpoint Files Expected Locally

```text
models_large/hf_large_densenet121/best_densenet121.pt
models_large/hf_large_resnet50/best_resnet50.pt
models_large/hf_large_efficientnet_b0/best_efficientnet_b0.pt
```

## Recommended Checkpoint Distribution Route

1. Confirm dataset and institutional requirements allow sharing trained weights.
2. Package checkpoints with:
   - `configs/hf_large.yaml`
   - `configs/hf_large_resnet50.yaml`
   - `configs/hf_large_efficientnet_b0.yaml`
   - `configs/label_map.yaml`
   - `outputs_large/training/*/resolved_training_config.yaml`
   - `outputs_large/training/*/environment_report.json`
   - `outputs_large/training/*/pip_freeze.txt`
3. Deposit the package through one of these routes:
   - GitHub Release asset if size and policy constraints are acceptable.
   - Zenodo, OSF, Figshare, or an institutional repository if a DOI is desired.
   - Controlled repository or reviewer-only private link if the target journal requests restricted review access.
4. Add the final DOI or release URL to:
   - `README.md`
   - `DATA_ACCESS_AND_RECONSTRUCTION.md`
   - the manuscript Data Availability or Code Availability statement
   - the cover letter, if helpful

## GitHub Release Preparation

Recommended release tag:

```text
v1.0-reviewer-package
```

Recommended release title:

```text
CXR public-subset validation reviewer package v1.0
```

Recommended release notes:

```text
This release contains the code, configuration files, derived metadata, split files, prediction CSVs, metric tables, manuscript-ready figures, training logs, package-version records, and final submission-oriented documents for the selected-public-subset NIH ChestX-ray14 to VinDr-CXR validation study. Raw images and model checkpoints are not included in the Git tree. Raw images should be obtained from the original dataset providers. Checkpoint files may be added as release assets after confirming dataset and institutional requirements.
```

After GitHub CLI authentication, create the release page with:

```powershell
powershell -ExecutionPolicy Bypass -File .\CREATE_GITHUB_RELEASE_AFTER_LOGIN.ps1
```

## DOI Plan

GitHub URLs are useful but are not a substitute for a persistent scholarly identifier. Before final submission, create an archival record through Zenodo, OSF, Figshare, Dryad, or an institutional repository and record the DOI here:

```text
Repository DOI: pending
Checkpoint DOI or release asset URL: pending
```

Do not invent a DOI in the manuscript. Use `pending` until the archive record exists and resolves.
