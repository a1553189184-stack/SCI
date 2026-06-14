# Data Access and Reconstruction

This file documents how a reviewer or independent researcher can reconstruct the analysis inputs from public dataset sources and the derived files included in this repository.

## Public Source Datasets

| Dataset | Role in this study | Public source | Notes |
|---|---|---|---|
| NIH ChestX-ray14 | Development dataset for training, validation, calibration, and internal testing | NIH download site and Google Cloud public dataset documentation: https://docs.cloud.google.com/healthcare-api/docs/resources/public-datasets/nih-chest | NIH ChestX-ray14 images are de-identified PNG chest radiographs. The NIH Clinical Center is the data provider. |
| VinDr-CXR | Independent external validation dataset | PhysioNet VinDr-CXR v1.0.0: https://physionet.org/content/vindr-cxr/1.0.0/ | PhysioNet lists VinDr-CXR as a credentialed-access database and provides the dataset citation and DOI. |

The raw images are not redistributed in this Git repository. Users must download them from the original dataset providers and comply with their licences, access terms, and citation requirements.

## Expected Local Layout

The default configuration `configs/hf_large.yaml` expects this layout after raw data have been restored:

```text
<PROJECT_ROOT>/
  data/
    nih_chestxray14/
      Data_Entry_2017.csv
      images or extracted NIH image folders
    vindr_cxr/
      annotations_train.csv
      PNG or DICOM-derived image files used for the selected subset
```

The project can be adapted to another layout by editing `configs/hf_large.yaml`. Avoid changing label order after predictions have been generated.

## Derived Data Included in This Repository

| Derived data family | Location | Purpose |
|---|---|---|
| Clean NIH metadata | `metadata_large/hf_large_nih_clean_metadata.csv` | Analysis-ready development metadata and label columns |
| Clean VinDr metadata | `metadata_large/hf_large_vindr_clean_metadata.csv` | Analysis-ready external metadata and label columns |
| VinDr boxes | `metadata_large/hf_large_vindr_boxes_clean.csv` | Optional localization metadata for Grad-CAM overlap analyses |
| NIH splits | `splits_large/hf_large_nih_*.csv` | Patient-level train/validation/calibration/internal-test assignments |
| Predictions | `predictions_large/*.csv` | Model probabilities, labels, and binary decisions used for metrics |
| Metrics and source tables | `tables_large/*.csv` | Performance, calibration, harmonization, subgroup, and figure-source tables |
| Figures | `figures_large/` | Manuscript figures and 300 dpi TIFF exports |
| Environment and logs | `outputs_large/training/`, `logs_large/` | Training logs, environment reports, package versions, and resolved configs |

## Reconstruction Workflow

1. Restore raw NIH ChestX-ray14 and VinDr-CXR/VinBigData-derived files under `data/`.
2. Review `configs/label_map.yaml` and `configs/hf_large.yaml`.
3. Run metadata preparation:

```powershell
python scripts\prepare_nih.py --config configs\hf_large.yaml
python scripts\prepare_vindr.py --config configs\hf_large.yaml
```

4. Rebuild NIH patient-level splits:

```powershell
python scripts\create_patient_splits.py --config configs\hf_large.yaml
```

5. Train DenseNet121:

```powershell
python scripts\train.py --config configs\hf_large.yaml
```

6. Recreate predictions, metrics, calibration outputs, and Grad-CAM panels:

```powershell
python scripts\evaluate_internal.py --config configs\hf_large.yaml
python scripts\evaluate_external.py --config configs\hf_large.yaml
python scripts\calibration.py --config configs\hf_large.yaml
python scripts\gradcam.py --config configs\hf_large.yaml
```

7. Regenerate manuscript tables and figures:

```powershell
python scripts\build_15_submission_package.py
```

## Data Availability Statement Draft

The study used publicly available chest radiograph datasets. NIH ChestX-ray14 should be obtained from the NIH Clinical Center download site or the Google Cloud public dataset route described at https://docs.cloud.google.com/healthcare-api/docs/resources/public-datasets/nih-chest. VinDr-CXR should be obtained from PhysioNet v1.0.0 at https://physionet.org/content/vindr-cxr/1.0.0/ under the applicable PhysioNet access terms. The present repository provides derived metadata, NIH patient-level split files, model prediction CSVs, metric tables, figure source data, manuscript-ready figures, code, package-version records, and training logs. Raw images are not redistributed by the authors. Model checkpoint files are not tracked in normal Git; if required for review, they should be deposited as a controlled release asset or DOI-linked archive according to `RELEASE_AND_CHECKPOINT_PLAN.md`.

## Citation and Licence Notes

- Cite the original NIH ChestX-ray14 publication and acknowledge the NIH Clinical Center as data provider.
- Cite the PhysioNet VinDr-CXR dataset record and its DOI.
- Do not apply this repository's code licence to the third-party datasets.
- Add a final repository/code licence before making the repository public for reuse.

