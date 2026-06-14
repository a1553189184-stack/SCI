# v1.0-reviewer-package Release Notes

## Contents

This reviewer package contains:

- Modular source code in `src/` and runnable scripts in `scripts/`.
- YAML configuration files and label mapping in `configs/`.
- Derived clean metadata in `metadata_large/`.
- NIH patient-level split files in `splits_large/`.
- Prediction CSVs for DenseNet121, ResNet50, and EfficientNet-B0 in `predictions_large/`.
- Metric tables, bootstrap confidence intervals, calibration outputs, threshold tables, and manuscript-ready source tables in `tables_large/`.
- Main and supplementary figures, including 300 dpi TIFF exports, in `figures_large/`.
- Training logs, environment reports, resolved configs, package versions, and final manuscript/supporting documents in `logs_large/` and `outputs_large/`.
- Reviewer-facing documentation:
  - `REVIEWER_REPRODUCIBILITY_CHECKLIST.md`
  - `DATA_ACCESS_AND_RECONSTRUCTION.md`
  - `REPORTING_CHECKLIST_TRIPOD_AI_CLAIM.md`
  - `DATA_AND_CODE_AVAILABILITY.md`
  - `RELEASE_AND_CHECKPOINT_PLAN.md`
  - `REPOSITORY_FILE_MANIFEST.csv`
- Checkpoint release metadata:
  - `release_assets/RELEASE_ASSET_MANIFEST_v1.0-reviewer-package.csv`
  - `release_assets/CHECKPOINT_MANIFEST_v1.0-reviewer-package.csv`
  - `release_assets/SHA256SUMS_checkpoints_v1.0-reviewer-package.txt`

## Not Included

- Raw NIH ChestX-ray14 and VinDr-CXR images.
- Model checkpoint `.pt` files.
- Large zip archives.
- Python virtual environments and local cache files.

Checkpoint files have been packaged separately as `CXR_model_checkpoints_v1.0-reviewer-package.zip` for upload as a release asset or DOI-linked archive after confirming redistribution requirements.

## Interpretation Guardrails

- This is a selected public-subset validation package, not a full official-cohort benchmark.
- VinDr-CXR was not used for threshold tuning, model selection, retraining, or calibration fitting.
- External discrimination claims are limited to external labels with nonzero positives.
- Grad-CAM++ panels are qualitative failure-mode analysis, not evidence of clinical reasoning.
- The study does not establish clinical readiness.
