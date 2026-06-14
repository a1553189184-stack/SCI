# Zenodo DOI Instructions

This file documents the DOI step for the reviewer package.

## Current Status

- GitHub repository: `https://github.com/a1553189184-stack/SCI`
- Fixed tag: `v1.0-reviewer-package`
- Checkpoint archive prepared locally as: `<DESKTOP>/CXR_model_checkpoints_v1.0-reviewer-package.zip`
- Source/result archive prepared locally as: `<DESKTOP>/CXR_reviewer_source_package_v1.0-reviewer-package.zip`
- Checkpoint archive SHA256: see `release_assets/RELEASE_ASSET_MANIFEST_v1.0-reviewer-package.csv`
- DOI: `10.5281/zenodo.20688290`
- DOI URL: `https://doi.org/10.5281/zenodo.20688290`
- Concept DOI: `10.5281/zenodo.20688289`
- Archived file: `a1553189184-stack/SCI-v1.0-reviewer-package.zip`

## Route A: Zenodo GitHub Integration

1. Log in to Zenodo with the GitHub account that can access `a1553189184-stack/SCI`.
2. Connect the GitHub account to Zenodo.
3. Enable the `SCI` repository in Zenodo's GitHub integration page.
4. Create or confirm the GitHub Release for `v1.0-reviewer-package`.
5. Zenodo should archive the release and issue a DOI.
6. Copy the issued DOI into:
   - `README.md`
   - `DATA_AND_CODE_AVAILABILITY.md`
   - `RELEASE_AND_CHECKPOINT_PLAN.md`
   - manuscript Data/Code Availability

## Route B: Manual Zenodo Upload

Use this route if the GitHub integration does not capture all required files or if checkpoint assets must be deposited as a separate research object.

1. Create a new Zenodo upload.
2. Upload:
   - `CXR_reviewer_source_package_v1.0-reviewer-package.zip` or the source archive from the GitHub release
   - `CXR_model_checkpoints_v1.0-reviewer-package.zip`, if checkpoint sharing is permitted
   - `REPOSITORY_FILE_MANIFEST.csv`
   - `release_assets/RELEASE_ASSET_MANIFEST_v1.0-reviewer-package.csv`
   - `release_assets/CHECKPOINT_MANIFEST_v1.0-reviewer-package.csv`
   - `release_assets/SHA256SUMS_checkpoints_v1.0-reviewer-package.txt`
3. Use `ZENODO_METADATA_TEMPLATE.json` as the metadata guide.
4. Reserve or publish the DOI.
5. Update repository and manuscript availability text with the real DOI.

## Important Rules

- Do not invent a DOI.
- Do not list fake creators or affiliations.
- Do not upload raw NIH ChestX-ray14 or VinDr-CXR images unless the original dataset terms allow redistribution.
- Confirm that model checkpoint sharing is allowed under dataset and institutional requirements before public release.
