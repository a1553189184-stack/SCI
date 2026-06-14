# Reviewer Reproducibility Checklist

This file maps the manuscript claims, tables, and figures to concrete repository artifacts. It is intended for editors, reviewers, and internal audit before submission.

## Scope

- Study type: retrospective public-dataset machine-learning development and external validation study.
- Development dataset: selected NIH ChestX-ray14 public subset.
- Independent external validation dataset: selected VinDr-CXR/VinBigData-derived public subset.
- Main model: DenseNet121.
- Comparator models: ResNet50 and EfficientNet-B0.
- Image size: 224 x 224.
- Task: multi-label chest radiograph classification.
- Primary design guardrail: no VinDr-CXR threshold tuning, model selection, retraining, or calibration fitting.

This repository supports a selected public-subset validation experiment. It is not a full official-cohort benchmark and does not establish clinical readiness.

## Quick Integrity Checks

| Check | Evidence file | Status |
|---|---|---|
| NIH patient-level train/validation/calibration/internal-test split exists | `splits_large/hf_large_nih_all_splits.csv` | Available |
| Split statistics exist | `splits_large/hf_large_nih_split_statistics.csv`, `tables_large/table1_nih_split_summary.csv` | Available |
| Label harmonization is explicit | `configs/label_map.yaml`, `tables_large/table2_external_evaluable_labels_main_final15.csv` | Available |
| NIH validation-derived thresholds are saved | `tables_large/thresholds_from_val.csv` | Available |
| Internal predictions are saved | `predictions_large/internal_test_predictions.csv` | Available |
| External predictions are saved | `predictions_large/external_vindr_predictions.csv` | Available |
| Calibration fitting uses NIH calibration split | `predictions_large/nih_calibration_predictions.csv`, `tables_large/calibration_metrics.csv` | Available |
| Grad-CAM case index is saved | `tables_large/gradcam_case_index.csv` | Available |
| Final manuscript tables are source-backed | `tables_large/table*_final15.csv`, `outputs_large/submission_package_manifest_final15.json` | Available |
| Package versions and training environment are saved | `outputs_large/training/*/environment_report.json`, `outputs_large/training/*/pip_freeze.txt` | Available |

## Result-to-Artifact Map

| Manuscript element | Primary source artifact | Generating script |
|---|---|---|
| Table 1: dataset characteristics | `tables_large/table1_dataset_characteristics_main_final15.csv` | `scripts/build_15_submission_package.py` |
| Table 2: external-evaluable labels | `tables_large/table2_external_evaluable_labels_main_final15.csv` | `scripts/build_15_submission_package.py` |
| Table 3: DenseNet121 internal/external performance | `tables_large/table3_densenet121_main_performance_final15.csv` | `scripts/build_15_submission_package.py`; upstream `scripts/evaluate_internal.py`, `scripts/evaluate_external.py` |
| Table 4: architecture comparison | `tables_large/table4_architecture_macro_main_final15.csv` | `scripts/build_15_submission_package.py`; upstream model-specific evaluation outputs |
| Table 5: calibration transfer | `tables_large/table5_calibration_transfer_main_final15.csv` | `scripts/build_15_submission_package.py`; upstream `scripts/calibration.py` |
| Supplementary subgroup table | `tables_large/supplementary_table_descriptive_subgroup_final15.csv` | `scripts/build_15_submission_package.py` |
| Figure 1: workflow | `figures_large/figure1_study_workflow_three_models.png`, `.pdf`, `.tiff` | `scripts/build_15_submission_package.py` |
| Figure 2: internal vs external discrimination | `figures_large/figure2_densenet121_internal_external_ci.png`, `.pdf`, `.tiff` | `scripts/build_15_submission_package.py` |
| Figure 3: prevalence and AUPRC baseline/lift | `figures_large/figure3_prevalence_auprc_baseline_lift.png`, `.pdf`, `.tiff` | `scripts/build_15_submission_package.py` |
| Figure 4: calibration curves | `figures_large/figure4_calibration_curves_upgraded.png`, `.tiff` | `scripts/build_15_submission_package.py`; upstream `scripts/calibration.py` |
| Figure 5: Grad-CAM++ failure modes | `figures_large/figure5_gradcam_failure_modes_upgraded.png`, `.tiff` | `scripts/build_15_submission_package.py`; upstream `scripts/gradcam.py` |
| Figure 6: external-minus-internal AUROC | `figures_large/figure6_internal_minus_external_auroc.png`, `.pdf`, `.tiff` | `scripts/build_15_submission_package.py` |

## Prediction and Metric Files

| Analysis | Predictions | Metrics and intervals |
|---|---|---|
| DenseNet121 NIH validation threshold selection | `predictions_large/nih_validation_predictions.csv` | `tables_large/thresholds_from_val.csv` |
| DenseNet121 NIH internal test | `predictions_large/internal_test_predictions.csv` | `tables_large/internal_metrics.csv`, `tables_large/bootstrap_ci.csv` |
| DenseNet121 VinDr external validation | `predictions_large/external_vindr_predictions.csv` | `tables_large/external_metrics.csv`, `tables_large/internal_external_comparison.csv`, `tables_large/performance_drop.csv` |
| DenseNet121 calibration | `predictions_large/nih_calibration_predictions.csv` | `tables_large/calibration_metrics.csv` |
| ResNet50 comparison | `predictions_large/resnet50_*_predictions.csv` | `tables_large/resnet50_*metrics.csv`, `tables_large/resnet50_performance_drop.csv` |
| EfficientNet-B0 comparison | `predictions_large/efficientnet_b0_*_predictions.csv` | `tables_large/efficientnet_b0_*metrics.csv`, `tables_large/efficientnet_b0_performance_drop.csv` |

## Rebuild Commands

The commands below assume the original public data have been restored under the paths configured in `configs/hf_large.yaml` and model checkpoint files have been restored under `models_large/`.

```powershell
cd <PROJECT_ROOT>
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
python -m pip install -r environment\requirements.txt
python scripts\check_environment.py --save-freeze
```

Prepare metadata and splits:

```powershell
python scripts\prepare_nih.py --config configs\hf_large.yaml
python scripts\prepare_vindr.py --config configs\hf_large.yaml
python scripts\create_patient_splits.py --config configs\hf_large.yaml
```

Train and evaluate DenseNet121:

```powershell
python scripts\train.py --config configs\hf_large.yaml
python scripts\evaluate_internal.py --config configs\hf_large.yaml
python scripts\evaluate_external.py --config configs\hf_large.yaml
python scripts\calibration.py --config configs\hf_large.yaml
python scripts\gradcam.py --config configs\hf_large.yaml
```

Regenerate final manuscript assets:

```powershell
python scripts\build_10_upgrade_assets.py
python scripts\build_10_sci_upgrade_docs.py
python scripts\build_12_final_submission_docs.py
python scripts\build_15_submission_package.py
```

## Leakage and Tuning Audit

| Risk | Repository control |
|---|---|
| Patient leakage inside NIH development data | Patient-level split file and split-statistics table are provided in `splits_large/` |
| Test-set threshold tuning | Thresholds are stored in `tables_large/thresholds_from_val.csv` and are selected from NIH validation predictions |
| External validation tuning | README and manuscript guardrails state that VinDr was not used for threshold tuning, model selection, retraining, or calibration fitting |
| Calibration leakage | Calibration models are fitted using NIH calibration predictions only |
| Unsupported external labels | Edema and Pneumonia are marked not externally evaluable because the selected external subset has zero positives |
| Saliency overinterpretation | Grad-CAM++ is described as qualitative failure-mode analysis, not clinical reasoning proof |

## Known Non-blocking Limitations

- Raw NIH and VinDr-CXR images are not redistributed because they should be obtained from the original public dataset sources under their own access terms.
- Model checkpoint files are not tracked in normal Git. Use `RELEASE_AND_CHECKPOINT_PLAN.md` for the checkpoint distribution plan.
- The present package supports a selected public subset, not the complete official NIH or VinDr cohorts.
- A repository DOI is not included yet. Create a GitHub release and archive it through Zenodo, OSF, Figshare, or another DOI-issuing repository before final submission if the target journal expects a persistent identifier.

