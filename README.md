# Public-subset Chest Radiograph Validation

This repository contains the code, configuration files, result tables, figures, prediction CSVs, and manuscript materials for:

**Public-subset Cross-dataset Validation and Calibration Transfer of Deep Learning Models for Multi-label Chest Radiograph Classification**

The study is a retrospective public-dataset machine-learning validation experiment. It uses a selected NIH ChestX-ray14 public parquet subset as the development dataset and a selected VinDr-CXR/VinBigData-derived public PNG subset as independent external validation.

## Study Summary

- Development dataset: selected NIH ChestX-ray14 public parquet subset.
- External validation dataset: selected VinDr-CXR/VinBigData-derived public PNG subset.
- NIH development subset: 5,000 images from 3,795 patients.
- VinDr-derived external subset: 1,000 images.
- Main model: DenseNet121.
- Architecture comparators: ResNet50 and EfficientNet-B0.
- NIH splitting: patient-level train, validation, calibration, and internal-test splits.
- Thresholds: selected on the NIH validation split only.
- Calibration: temperature scaling, Platt scaling, and isotonic regression fitted on the NIH calibration split only.
- External validation: no external threshold tuning, model selection, retraining, or calibration fitting.
- Saliency: Grad-CAM++ used only for qualitative failure-mode review.

This is a selected public-subset validation package. It is not a full official-cohort benchmark and does not establish clinical readiness.

## Key Results

DenseNet121:

- Internal all-label macro AUROC/AUPRC: 0.680 / 0.214.
- Internal external-evaluable-label macro AUROC/AUPRC: 0.667 / 0.269.
- External nonzero-prevalence-label macro AUROC/AUPRC: 0.743 / 0.434.
- Internal uncalibrated macro Brier/ECE/MCE/slope/intercept: 0.193 / 0.269 / 0.539 / 0.633 / -2.285.

Architecture comparators:

- ResNet50 external nonzero-prevalence-label macro AUROC/AUPRC: 0.728 / 0.418.
- EfficientNet-B0 external nonzero-prevalence-label macro AUROC/AUPRC: 0.656 / 0.370.

External-evaluable labels:

- Atelectasis
- Cardiomegaly
- Pleural Effusion
- Pneumothorax
- Consolidation
- No Finding

Edema and Pneumonia had zero positive cases in the selected external subset and are not used for external discrimination claims.

## Repository Contents

- `src/`: reusable Python modules for configuration, datasets, models, training, evaluation, calibration, and Grad-CAM.
- `scripts/`: pipeline entry points and manuscript/package generation scripts.
- `configs/`: YAML configuration files and label mapping.
- `environment/`: Python requirements and Windows environment setup commands.
- `metadata_large/`: cleaned metadata files for the analyzed public subsets.
- `splits_large/`: NIH patient-level split CSVs.
- `predictions_large/`: saved prediction CSVs for DenseNet121, ResNet50, and EfficientNet-B0.
- `tables_large/`: manuscript-ready CSV tables and source tables.
- `figures_large/`: main figures, supplementary figures, graphical abstract draft, and 300 dpi TIFF exports.
- `outputs_large/`: final manuscript files, submission package files, QA summaries, manifests, and environment reports.
- `logs_large/`: training logs.
- `data/RAW_DATA_OMITTED.md`: explains why raw images are not redistributed.
- `models_large/MODEL_CHECKPOINTS_OMITTED.md`: explains why large checkpoint files are not tracked in Git.
- `REVIEWER_REPRODUCIBILITY_CHECKLIST.md`: maps manuscript claims, tables, and figures to concrete files.
- `DATA_ACCESS_AND_RECONSTRUCTION.md`: documents public data sources and reconstruction commands.
- `REPORTING_CHECKLIST_TRIPOD_AI_CLAIM.md`: audits TRIPOD+AI/CLAIM-facing reporting completeness.
- `DATA_AND_CODE_AVAILABILITY.md`: provides submission-ready availability wording.
- `RELEASE_AND_CHECKPOINT_PLAN.md`: describes the checkpoint and DOI/release plan.
- `ZENODO_DOI_INSTRUCTIONS.md`: describes the Zenodo DOI workflow.
- `ZENODO_METADATA_TEMPLATE.json`: provides metadata fields for a DOI-linked record.
- `release_assets/`: contains checkpoint archive manifests and SHA256 checksums.
- `REPOSITORY_FILE_MANIFEST.csv`: lists repository files and sizes.

## Reviewer Quick Start

Start with these files:

1. `REVIEWER_REPRODUCIBILITY_CHECKLIST.md`
2. `DATA_ACCESS_AND_RECONSTRUCTION.md`
3. `REPORTING_CHECKLIST_TRIPOD_AI_CLAIM.md`
4. `DATA_AND_CODE_AVAILABILITY.md`

These files map each major manuscript table and figure to the corresponding prediction CSV, metric table, script, and configuration file.

## Final Submission Files

The final submission-oriented files are:

- `outputs_large/CXR_Manuscript_SCI_Submission_Final_15.docx`
- `outputs_large/CXR_Final_Submission_Package_15.docx`
- `outputs_large/CXR_Cover_Letter_Final_15.docx`
- `outputs_large/CXR_Supplementary_Materials_Organization_Final_15.docx`
- `outputs_large/submission_package_manifest_final15.json`
- `outputs_large/docx_qa_summary_15_final.json`

Main figure TIFF exports are in:

- `figures_large/final15_tiff_300dpi/`

## Fixed Reviewer Release

The fixed reviewer package release is:

- `v1.0-reviewer-package`: https://github.com/a1553189184-stack/SCI/releases/tag/v1.0-reviewer-package

The release includes the source/result archive, checkpoint archive, checkpoint manifest, release asset manifest, and SHA256 checksum file.

## Large Files Not Tracked

Raw image files, virtual environments, model checkpoint files, and large zip archives are intentionally omitted from this GitHub-safe repository.

GitHub blocks ordinary Git files larger than 100 MiB. If model checkpoints need to be shared, use a controlled archive, a release asset, Git LFS, Zenodo, OSF, Figshare, or another storage service after confirming dataset and institutional requirements.

A checkpoint archive has been prepared outside Git as `CXR_model_checkpoints_v1.0-reviewer-package.zip`; a source/result archive has been prepared as `CXR_reviewer_source_package_v1.0-reviewer-package.zip`. Their manifest and SHA256 checksums are tracked in `release_assets/`.

## Reproducibility

Recommended setup on Windows:

```powershell
cd <PROJECT_ROOT>
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
python -m pip install -r environment\requirements.txt
python scripts\check_environment.py --save-freeze
```

Regenerate final submission materials:

```powershell
python scripts\build_10_upgrade_assets.py
python scripts\build_10_sci_upgrade_docs.py
python scripts\build_12_final_submission_docs.py
python scripts\build_15_submission_package.py
```

The completed run used:

- Python 3.12.10
- PyTorch 2.11.0+cu128
- CUDA 12.8
- NVIDIA GeForce RTX 5060 Laptop GPU
- random seed 20260614

## Data Availability

The original NIH ChestX-ray14 and VinDr-CXR/VinBigData-derived image and label resources should be obtained from their official public sources. Users must follow the original dataset licenses, access conditions, and citation requirements.

- NIH ChestX-ray14: https://docs.cloud.google.com/healthcare-api/docs/resources/public-datasets/nih-chest
- VinDr-CXR v1.0.0: https://physionet.org/content/vindr-cxr/1.0.0/

This repository provides derived metadata, splits, predictions, result tables, figures, and code needed to audit the reported public-subset experiment.

## Important Interpretation Guardrails

- This is selected public-subset validation, not full official-cohort validation.
- VinDr-derived external data were not used for threshold tuning, model selection, retraining, or calibration fitting.
- External discrimination claims are restricted to nonzero-prevalence external-evaluable labels.
- Edema and Pneumonia are not external primary validated labels in this analyzed subset.
- Calibration findings are method-dependent and should not be described as uniform improvement.
- Grad-CAM++ is qualitative failure-mode saliency, not evidence of radiologist-like reasoning.
- The study does not establish clinical readiness.

## License

Repository code licensing is not finalized. Add a project license before making the repository public if redistribution is intended.

Dataset licenses are controlled by the original dataset providers and are not replaced by this repository.
