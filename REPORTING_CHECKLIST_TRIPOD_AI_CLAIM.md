# Reporting Checklist Audit: TRIPOD+AI and CLAIM

This audit is a reviewer-facing map from reporting expectations to repository and manuscript evidence. It does not replace the journal's official checklist forms.

## Guideline Rationale

- Primary guideline: TRIPOD+AI, because the study develops and evaluates clinical prediction/classification models using machine learning.
- Imaging AI companion guideline: CLAIM 2024, because the study concerns artificial intelligence applied to medical imaging.
- Additional diagnostic-accuracy framing may be useful for journals that request STARD-style reporting, but the core manuscript claim is model development and validation.

## Compliance Matrix

| Domain | Status | Evidence | Repository location | Remaining action before submission |
|---|---|---|---|---|
| Title identifies AI imaging validation topic | Complete | Final manuscript title and abstract | `outputs_large/CXR_Manuscript_SCI_Submission_Final_15.docx` | Confirm target journal title limits |
| Study design and objective | Complete | Public-subset retrospective development and external validation framing | Manuscript Methods; `README.md` | None |
| Dataset source and eligibility | Partial | NIH and VinDr source descriptions, subset caveat | `DATA_ACCESS_AND_RECONSTRUCTION.md`, `metadata_large/` | Add journal-specific dataset citations to final reference list |
| Sample flow and denominators | Complete for selected subset | Dataset characteristics and split summaries | `tables_large/table1_dataset_characteristics_main_final15.csv`, `splits_large/` | None |
| Predictor/input definition | Complete | 224 x 224 chest radiograph inputs, ImageNet normalization, augmentation | `configs/hf_large.yaml`, `src/datasets.py`, `src/preprocessing.py` | None |
| Outcome/label definition | Complete with limitations | Harmonized labels and high-risk label notes | `configs/label_map.yaml`, `tables_large/table2_external_evaluable_labels_main_final15.csv` | Keep Edema/Pneumonia caveat in main text |
| Missing labels and exclusions | Partial | Missing-label handling in label map and preprocessing scripts | `configs/label_map.yaml`, `src/prepare_nih.py`, `src/prepare_vindr.py` | Expand prose if target journal requires full exclusion flow |
| Split strategy | Complete | Patient-level NIH split files and statistics | `splits_large/`, `tables_large/table1_nih_split_summary.csv` | None |
| Model architecture | Complete | DenseNet121 main model, ResNet50/EfficientNet-B0 comparators | `src/models.py`, `configs/hf_large*.yaml` | None |
| Training details | Complete | Hyperparameters, optimizer, mixed precision, seed, logs | `configs/hf_large.yaml`, `logs_large/`, `outputs_large/training/` | None |
| Threshold selection | Complete | NIH validation-derived thresholds only | `tables_large/thresholds_from_val.csv`, `predictions_large/nih_validation_predictions.csv` | None |
| Internal validation metrics | Complete | AUROC, AUPRC, thresholded metrics, bootstrap CI | `tables_large/internal_metrics.csv`, `tables_large/bootstrap_ci.csv` | None |
| External validation independence | Complete | External predictions and metrics are separate; no VinDr tuning | `predictions_large/external_vindr_predictions.csv`, `tables_large/external_metrics.csv`, `README.md` | Keep statement in Methods and Discussion |
| Calibration analysis | Complete with caveat | NIH calibration fitting and NIH/VinDr evaluation | `tables_large/calibration_metrics.csv`, `scripts/calibration.py` | Do not claim uniform calibration improvement |
| Explainability/saliency reporting | Complete with caveat | Grad-CAM++ case index and panels | `tables_large/gradcam_case_index.csv`, `figures_large/figure5_gradcam_failure_modes_upgraded.png` | Maintain qualitative-only interpretation |
| Comparator reporting | Complete descriptive | ResNet50 and EfficientNet-B0 output files and macro table | `predictions_large/resnet50_*`, `predictions_large/efficientnet_b0_*`, `tables_large/table4_architecture_macro_main_final15.csv` | Do not overstate superiority without powered comparison |
| Uncertainty reporting | Complete | Bootstrap confidence intervals in main tables | `tables_large/bootstrap_ci.csv`, model-specific bootstrap files | None |
| Bias and limitations | Complete in final manuscript | Selected subset, label harmonization, prevalence, external zero positives | Manuscript Discussion; `tables_large/pre_submission_risk_table_final15.csv` | None |
| Code availability | Complete for code | GitHub repository with scripts and config | `README.md`, `src/`, `scripts/` | Add archived DOI when available |
| Data availability | Partial | Public source datasets and derived artifacts documented | `DATA_ACCESS_AND_RECONSTRUCTION.md` | Add final DOI/accession for repository release if created |
| Model availability | Partial | Checkpoint file paths and sharing plan documented | `models_large/MODEL_CHECKPOINTS_OMITTED.md`, `RELEASE_AND_CHECKPOINT_PLAN.md` | Deposit checkpoints if the journal/reviewers require exact re-inference |
| Ethics | Needs author confirmation | Public de-identified datasets are used | Manuscript declarations | Confirm final wording required by target journal |
| Funding, conflicts, author contributions | Needs author confirmation | Placeholders/checklist exist | `tables_large/final_submission_checklist_final15.csv` | Fill with real author information |

## Reviewer-Risk Summary

- The evidence chain for reported numerical results is strong because prediction CSVs, metric CSVs, and manuscript tables are included.
- The main remaining reproducibility limitation is exact checkpoint availability. This is addressed by the release plan but still requires deposition if reviewers request exact re-inference.
- The main reporting limitation is author-side declaration completion: ethics wording, funding, conflicts, contributions, affiliations, and corresponding-author details.
- The manuscript should continue to avoid clinical-readiness language and full-cohort benchmark claims.

