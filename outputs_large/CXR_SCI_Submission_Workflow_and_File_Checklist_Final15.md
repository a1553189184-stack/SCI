# SCI Submission Workflow and File Checklist - Final 15 CXR Manuscript

Generated: 2026-06-14

## Current Package Status

- QA result: 78 checked items, all PASS; no FAIL/WARN after repair.
- Repaired during this pass: manuscript/submission-package reference count changed from 26 to 27; stale repository-link placeholder removed; src/make_tables.py and src/make_figures.py added.
- Remaining placeholders are administrative fields that require author/journal input, not scientific-result gaps.

## Repository Links
- GitHub repository: https://github.com/a1553189184-stack/SCI
- GitHub release: https://github.com/a1553189184-stack/SCI/releases/tag/v1.0-reviewer-package
- Zenodo DOI: https://doi.org/10.5281/zenodo.20688290

## Detailed Submission Workflow
1. Select the target journal and confirm scope, article type, word limit, abstract structure, figure rules, supplementary policy, reporting-guideline requirements, publication fees, and double-blind policy.
2. Create a journal-specific working copy of the main manuscript. Keep the current public-subset positioning and avoid changing reported numbers unless regenerated from CSV outputs.
3. Fill administrative fields on the title page and cover letter: authors, affiliations, corresponding author, email, ORCID, date, editor, and journal name.
4. Confirm ethics wording. Because the work uses de-identified public datasets, retain the exemption/waiver framing, but insert the local IRB exemption number only if your institution requires it.
5. Format the main manuscript according to the target journal: title page, abstract style, references, table/figure placement, line numbering, double spacing, and blinded/unblinded requirements.
6. Prepare separate figure uploads from the TIFF folder. Use PNG/PDF only if the journal prefers them. Confirm every figure number and caption matches the manuscript.
7. Prepare supplementary material. Upload the supplementary organization DOCX, selected CSV source data, reporting checklist, or reviewer package only if the journal allows or asks for them.
8. Use the Data and Code Availability statement already inserted in the manuscript. Cite the public GitHub repository, GitHub release, and Zenodo DOI exactly as listed.
9. Complete reporting-guideline checks. For this study type, TRIPOD+AI/EQUATOR AI guidance is the closest reporting framework; STARD-AI may be relevant only if the target journal frames the study as diagnostic-accuracy reporting.
10. Upload files in the submission system, enter title/abstract/keywords/funding/conflict-of-interest fields, add suggested reviewers if requested, and confirm that no external validation tuning claim is overstated.
11. Review the system-generated PDF proof page by page before final submission. Check author fields, links, figures, tables, and line breaks.
12. Submit, save the confirmation email/PDF, and record manuscript ID, journal, date, uploaded file versions, and any portal warnings.

## Manual Fields Still Required Before Upload
- Target journal, article type, editor name, and submission system account.
- Author names, affiliations, corresponding author, email, ORCID, contribution statement if required.
- Final manuscript word count according to target-journal counting rules.
- Local IRB exemption/waiver wording and approval number if your institution requires one.
- Final conflict-of-interest, funding, acknowledgments, and AI-use declarations.
- Reference style conversion, DOI/volume/issue/page verification, and journal abbreviation format.
- Journal-specific data/code availability form wording if the platform has a separate field.

## Files To Upload Or Cite
- Main manuscript: `C:\Users\ETHAN\Desktop\CXR_Manuscript_SCI_Submission_Final_15.docx`
- Cover letter: `C:\Users\ETHAN\Desktop\CXR_Cover_Letter_Final_15.docx`
- Separate figure files, preferably TIFF: `C:\Users\ETHAN\cxr_nih_to_vindr_github\figures_large\final15_tiff_300dpi`
- Supplementary materials organization file, if journal accepts supplement: `C:\Users\ETHAN\Desktop\CXR_Supplementary_Materials_Organization_Final_15.docx`

## Complete File Inventory

| Category | Role | Status | Use | Path |
|---|---|---|---|---|
| Manuscript | Main manuscript DOCX for journal upload | PASS | Submit | `C:\Users\ETHAN\Desktop\CXR_Manuscript_SCI_Submission_Final_15.docx` |
| Manuscript | Cover letter DOCX | PASS | Submit | `C:\Users\ETHAN\Desktop\CXR_Cover_Letter_Final_15.docx` |
| Supplement | Supplementary materials organization DOCX | PASS | Submit if requested | `C:\Users\ETHAN\Desktop\CXR_Supplementary_Materials_Organization_Final_15.docx` |
| Internal package | Combined final submission package | PASS | Do not submit unless journal allows combined package | `C:\Users\ETHAN\Desktop\CXR_Final_Submission_Package_15.docx` |
| Archive | Reviewer source package ZIP | PASS | Repository/release/Zenodo asset | `C:\Users\ETHAN\Desktop\CXR_reviewer_source_package_v1.0-reviewer-package.zip` |
| Archive | Model checkpoint ZIP | PASS | Release/Zenodo asset | `C:\Users\ETHAN\Desktop\CXR_model_checkpoints_v1.0-reviewer-package.zip` |
| Repository documentation | Repository landing page | PASS | Repository | `C:\Users\ETHAN\cxr_nih_to_vindr_github\README.md` |
| Repository documentation | Data/code availability | PASS | Repository | `C:\Users\ETHAN\cxr_nih_to_vindr_github\DATA_AND_CODE_AVAILABILITY.md` |
| Repository documentation | Raw data reconstruction guide | PASS | Repository | `C:\Users\ETHAN\cxr_nih_to_vindr_github\DATA_ACCESS_AND_RECONSTRUCTION.md` |
| Repository documentation | Reviewer checklist | PASS | Repository | `C:\Users\ETHAN\cxr_nih_to_vindr_github\REVIEWER_REPRODUCIBILITY_CHECKLIST.md` |
| Repository documentation | Reporting checklist | PASS | Repository | `C:\Users\ETHAN\cxr_nih_to_vindr_github\REPORTING_CHECKLIST_TRIPOD_AI_CLAIM.md` |
| Repository documentation | Citation metadata | PASS | Repository | `C:\Users\ETHAN\cxr_nih_to_vindr_github\CITATION.cff` |
| Repository documentation | Zenodo metadata | PASS | Repository | `C:\Users\ETHAN\cxr_nih_to_vindr_github\.zenodo.json` |
| Repository documentation | Zenodo summary | PASS | Repository | `C:\Users\ETHAN\cxr_nih_to_vindr_github\ZENODO_RECORD_SUMMARY.md` |
| Repository documentation | Release plan | PASS | Repository | `C:\Users\ETHAN\cxr_nih_to_vindr_github\RELEASE_AND_CHECKPOINT_PLAN.md` |
| Reproducibility | environment/requirements.txt | PASS | Repository | `C:\Users\ETHAN\cxr_nih_to_vindr_github\environment\requirements.txt` |
| Reproducibility | environment/create_env_commands.txt | PASS | Repository | `C:\Users\ETHAN\cxr_nih_to_vindr_github\environment\create_env_commands.txt` |
| Reproducibility | configs/hf_large.yaml | PASS | Repository | `C:\Users\ETHAN\cxr_nih_to_vindr_github\configs\hf_large.yaml` |
| Reproducibility | configs/hf_large_resnet50.yaml | PASS | Repository | `C:\Users\ETHAN\cxr_nih_to_vindr_github\configs\hf_large_resnet50.yaml` |
| Reproducibility | configs/hf_large_efficientnet_b0.yaml | PASS | Repository | `C:\Users\ETHAN\cxr_nih_to_vindr_github\configs\hf_large_efficientnet_b0.yaml` |
| Reproducibility | configs/label_map.yaml | PASS | Repository | `C:\Users\ETHAN\cxr_nih_to_vindr_github\configs\label_map.yaml` |
| Source code | src/datasets.py | PASS | Repository | `C:\Users\ETHAN\cxr_nih_to_vindr_github\src\datasets.py` |
| Source code | src/models.py | PASS | Repository | `C:\Users\ETHAN\cxr_nih_to_vindr_github\src\models.py` |
| Source code | src/train.py | PASS | Repository | `C:\Users\ETHAN\cxr_nih_to_vindr_github\src\train.py` |
| Source code | src/evaluate_internal.py | PASS | Repository | `C:\Users\ETHAN\cxr_nih_to_vindr_github\src\evaluate_internal.py` |
| Source code | src/evaluate_external.py | PASS | Repository | `C:\Users\ETHAN\cxr_nih_to_vindr_github\src\evaluate_external.py` |
| Source code | src/calibration.py | PASS | Repository | `C:\Users\ETHAN\cxr_nih_to_vindr_github\src\calibration.py` |
| Source code | src/gradcam.py | PASS | Repository | `C:\Users\ETHAN\cxr_nih_to_vindr_github\src\gradcam.py` |
| Source code | src/make_tables.py | PASS | Repository | `C:\Users\ETHAN\cxr_nih_to_vindr_github\src\make_tables.py` |
| Source code | src/make_figures.py | PASS | Repository | `C:\Users\ETHAN\cxr_nih_to_vindr_github\src\make_figures.py` |
| Splits | hf_large_nih_train.csv | PASS | Repository | `C:\Users\ETHAN\cxr_nih_to_vindr_github\splits_large\hf_large_nih_train.csv` |
| Splits | hf_large_nih_validation.csv | PASS | Repository | `C:\Users\ETHAN\cxr_nih_to_vindr_github\splits_large\hf_large_nih_validation.csv` |
| Splits | hf_large_nih_calibration.csv | PASS | Repository | `C:\Users\ETHAN\cxr_nih_to_vindr_github\splits_large\hf_large_nih_calibration.csv` |
| Splits | hf_large_nih_internal_test.csv | PASS | Repository | `C:\Users\ETHAN\cxr_nih_to_vindr_github\splits_large\hf_large_nih_internal_test.csv` |
| Splits | hf_large_nih_all_splits.csv | PASS | Repository | `C:\Users\ETHAN\cxr_nih_to_vindr_github\splits_large\hf_large_nih_all_splits.csv` |
| Splits | hf_large_nih_split_statistics.csv | PASS | Repository | `C:\Users\ETHAN\cxr_nih_to_vindr_github\splits_large\hf_large_nih_split_statistics.csv` |
| Predictions | internal_test_predictions.csv | PASS | Repository/source package | `C:\Users\ETHAN\cxr_nih_to_vindr_github\predictions_large\internal_test_predictions.csv` |
| Predictions | external_vindr_predictions.csv | PASS | Repository/source package | `C:\Users\ETHAN\cxr_nih_to_vindr_github\predictions_large\external_vindr_predictions.csv` |
| Predictions | nih_validation_predictions.csv | PASS | Repository/source package | `C:\Users\ETHAN\cxr_nih_to_vindr_github\predictions_large\nih_validation_predictions.csv` |
| Predictions | nih_calibration_predictions.csv | PASS | Repository/source package | `C:\Users\ETHAN\cxr_nih_to_vindr_github\predictions_large\nih_calibration_predictions.csv` |
| Predictions | resnet50_internal_test_predictions.csv | PASS | Repository/source package | `C:\Users\ETHAN\cxr_nih_to_vindr_github\predictions_large\resnet50_internal_test_predictions.csv` |
| Predictions | resnet50_external_vindr_predictions.csv | PASS | Repository/source package | `C:\Users\ETHAN\cxr_nih_to_vindr_github\predictions_large\resnet50_external_vindr_predictions.csv` |
| Predictions | efficientnet_b0_internal_test_predictions.csv | PASS | Repository/source package | `C:\Users\ETHAN\cxr_nih_to_vindr_github\predictions_large\efficientnet_b0_internal_test_predictions.csv` |
| Predictions | efficientnet_b0_external_vindr_predictions.csv | PASS | Repository/source package | `C:\Users\ETHAN\cxr_nih_to_vindr_github\predictions_large\efficientnet_b0_external_vindr_predictions.csv` |
| Tables | table1_dataset_characteristics_main_final15.csv | PASS | Repository/source data | `C:\Users\ETHAN\cxr_nih_to_vindr_github\tables_large\table1_dataset_characteristics_main_final15.csv` |
| Tables | table2_external_evaluable_labels_main_final15.csv | PASS | Repository/source data | `C:\Users\ETHAN\cxr_nih_to_vindr_github\tables_large\table2_external_evaluable_labels_main_final15.csv` |
| Tables | table3_densenet121_main_performance_final15.csv | PASS | Repository/source data | `C:\Users\ETHAN\cxr_nih_to_vindr_github\tables_large\table3_densenet121_main_performance_final15.csv` |
| Tables | table4_architecture_macro_main_final15.csv | PASS | Repository/source data | `C:\Users\ETHAN\cxr_nih_to_vindr_github\tables_large\table4_architecture_macro_main_final15.csv` |
| Tables | table5_calibration_transfer_main_final15.csv | PASS | Repository/source data | `C:\Users\ETHAN\cxr_nih_to_vindr_github\tables_large\table5_calibration_transfer_main_final15.csv` |
| Tables | supplementary_table7_hyperparameters.csv | PASS | Repository/source data | `C:\Users\ETHAN\cxr_nih_to_vindr_github\tables_large\supplementary_table7_hyperparameters.csv` |
| Tables | supplementary_table9_medmnist_pipeline_verification.csv | PASS | Repository/source data | `C:\Users\ETHAN\cxr_nih_to_vindr_github\tables_large\supplementary_table9_medmnist_pipeline_verification.csv` |
| Tables | internal_metrics.csv | PASS | Repository/source data | `C:\Users\ETHAN\cxr_nih_to_vindr_github\tables_large\internal_metrics.csv` |
| Tables | external_metrics.csv | PASS | Repository/source data | `C:\Users\ETHAN\cxr_nih_to_vindr_github\tables_large\external_metrics.csv` |
| Tables | calibration_metrics.csv | PASS | Repository/source data | `C:\Users\ETHAN\cxr_nih_to_vindr_github\tables_large\calibration_metrics.csv` |
| Tables | performance_drop.csv | PASS | Repository/source data | `C:\Users\ETHAN\cxr_nih_to_vindr_github\tables_large\performance_drop.csv` |
| Tables | thresholds_from_val.csv | PASS | Repository/source data | `C:\Users\ETHAN\cxr_nih_to_vindr_github\tables_large\thresholds_from_val.csv` |
| Tables | bootstrap_ci.csv | PASS | Repository/source data | `C:\Users\ETHAN\cxr_nih_to_vindr_github\tables_large\bootstrap_ci.csv` |
| Tables | final_submission_checklist_final15.csv | PASS | Repository/source data | `C:\Users\ETHAN\cxr_nih_to_vindr_github\tables_large\final_submission_checklist_final15.csv` |
| Figures PNG | figure1_study_workflow_three_models.png | PASS | Submit if PNG accepted | `C:\Users\ETHAN\cxr_nih_to_vindr_github\figures_large\figure1_study_workflow_three_models.png` |
| Figures PNG | figure2_densenet121_internal_external_ci.png | PASS | Submit if PNG accepted | `C:\Users\ETHAN\cxr_nih_to_vindr_github\figures_large\figure2_densenet121_internal_external_ci.png` |
| Figures PNG | figure3_prevalence_auprc_baseline_lift.png | PASS | Submit if PNG accepted | `C:\Users\ETHAN\cxr_nih_to_vindr_github\figures_large\figure3_prevalence_auprc_baseline_lift.png` |
| Figures PNG | figure4_calibration_curves_upgraded.png | PASS | Submit if PNG accepted | `C:\Users\ETHAN\cxr_nih_to_vindr_github\figures_large\figure4_calibration_curves_upgraded.png` |
| Figures PNG | figure5_gradcam_failure_modes_upgraded.png | PASS | Submit if PNG accepted | `C:\Users\ETHAN\cxr_nih_to_vindr_github\figures_large\figure5_gradcam_failure_modes_upgraded.png` |
| Figures PNG | figure6_internal_minus_external_auroc.png | PASS | Submit if PNG accepted | `C:\Users\ETHAN\cxr_nih_to_vindr_github\figures_large\figure6_internal_minus_external_auroc.png` |
| Figures PNG | graphical_abstract_plan_final15.png | PASS | Submit if PNG accepted | `C:\Users\ETHAN\cxr_nih_to_vindr_github\figures_large\graphical_abstract_plan_final15.png` |
| Figures TIFF | figure1_study_workflow_three_models.tiff | PASS | Preferred separate figure upload | `C:\Users\ETHAN\cxr_nih_to_vindr_github\figures_large\final15_tiff_300dpi\figure1_study_workflow_three_models.tiff` |
| Figures TIFF | figure2_densenet121_internal_external_ci.tiff | PASS | Preferred separate figure upload | `C:\Users\ETHAN\cxr_nih_to_vindr_github\figures_large\final15_tiff_300dpi\figure2_densenet121_internal_external_ci.tiff` |
| Figures TIFF | figure3_prevalence_auprc_baseline_lift.tiff | PASS | Preferred separate figure upload | `C:\Users\ETHAN\cxr_nih_to_vindr_github\figures_large\final15_tiff_300dpi\figure3_prevalence_auprc_baseline_lift.tiff` |
| Figures TIFF | figure4_calibration_curves_upgraded.tiff | PASS | Preferred separate figure upload | `C:\Users\ETHAN\cxr_nih_to_vindr_github\figures_large\final15_tiff_300dpi\figure4_calibration_curves_upgraded.tiff` |
| Figures TIFF | figure5_gradcam_failure_modes_upgraded.tiff | PASS | Preferred separate figure upload | `C:\Users\ETHAN\cxr_nih_to_vindr_github\figures_large\final15_tiff_300dpi\figure5_gradcam_failure_modes_upgraded.tiff` |
| Figures TIFF | figure6_internal_minus_external_auroc.tiff | PASS | Preferred separate figure upload | `C:\Users\ETHAN\cxr_nih_to_vindr_github\figures_large\final15_tiff_300dpi\figure6_internal_minus_external_auroc.tiff` |
| Figures TIFF | graphical_abstract_plan_final15.tiff | PASS | Preferred separate figure upload | `C:\Users\ETHAN\cxr_nih_to_vindr_github\figures_large\final15_tiff_300dpi\graphical_abstract_plan_final15.tiff` |
| Release assets | CHECKPOINT_MANIFEST_v1.0-reviewer-package.csv | PASS | Release/Zenodo | `C:\Users\ETHAN\cxr_nih_to_vindr_github\release_assets\CHECKPOINT_MANIFEST_v1.0-reviewer-package.csv` |
| Release assets | RELEASE_ASSET_MANIFEST_v1.0-reviewer-package.csv | PASS | Release/Zenodo | `C:\Users\ETHAN\cxr_nih_to_vindr_github\release_assets\RELEASE_ASSET_MANIFEST_v1.0-reviewer-package.csv` |
| Release assets | SHA256SUMS_checkpoints_v1.0-reviewer-package.txt | PASS | Release/Zenodo | `C:\Users\ETHAN\cxr_nih_to_vindr_github\release_assets\SHA256SUMS_checkpoints_v1.0-reviewer-package.txt` |
| Online links | GitHub repository | PASS | Cite | `https://github.com/a1553189184-stack/SCI` |
| Online links | GitHub release | PASS | Cite | `https://github.com/a1553189184-stack/SCI/releases/tag/v1.0-reviewer-package` |
| Online links | Zenodo DOI | PASS | Cite | `https://doi.org/10.5281/zenodo.20688290` |

## Reviewer-Risk Audit
- Data leakage: patient-level NIH splits are available; thresholds and checkpoint selection derive from NIH validation, not external VinDr.
- External validation: VinDr-CXR is used as independent external validation and is not used for retraining, threshold tuning, model selection, or main calibration fitting.
- Calibration: calibration models are fitted on the NIH calibration split; VinDr calibration results are transfer evaluation only.
- MedMNIST: retained only as supplementary pipeline verification, not evidence for the main claims.
- Grad-CAM: presented as qualitative failure-mode analysis, not clinical proof of reasoning.
- Clinical claims: manuscript wording states public-subset reproducibility/generalizability limits and does not claim clinical readiness.

## External Guidance Consulted
- ICMJE manuscript preparation: https://www.icmje.org/recommendations/browse/manuscript-preparation/preparing-for-submission.html
- EQUATOR TRIPOD+AI reporting guideline page: https://www.equator-network.org/reporting-guidelines/tripod-statement/
- EQUATOR AI/ML reporting-guideline collection: https://www.equator-network.org/reporting-guidelines-study-design/artificial-intelligence-machine-learning-studies/
- Springer Nature cover-letter guidance: https://support.springernature.com/en/support/solutions/articles/6000245674-cover-letter
- Springer Nature data-availability statement guidance: https://www.springernature.com/gp/authors/research-data-policy/data-availability-statements