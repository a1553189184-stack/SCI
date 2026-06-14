# Data and Code Availability

## Ready-to-Paste Draft

The code, configuration files, derived metadata, NIH patient-level split files, prediction CSVs, metric tables, figure source data, manuscript-ready figures, package-version records, and training logs supporting this selected-public-subset validation study are available at https://github.com/a1553189184-stack/SCI. The fixed reviewer-package release is `v1.0-reviewer-package` at https://github.com/a1553189184-stack/SCI/releases/tag/v1.0-reviewer-package. The original NIH ChestX-ray14 and VinDr-CXR images are not redistributed by the authors and should be obtained from the original public dataset providers under their respective access terms. NIH ChestX-ray14 can be obtained through the NIH Clinical Center download site or the Google Cloud public dataset route described at https://docs.cloud.google.com/healthcare-api/docs/resources/public-datasets/nih-chest. VinDr-CXR v1.0.0 can be obtained from PhysioNet at https://physionet.org/content/vindr-cxr/1.0.0/. Model checkpoint files are available in the release asset `CXR_model_checkpoints_v1.0-reviewer-package.zip`, with SHA256 checksums in `release_assets/`; public redistribution should be confirmed against dataset and institutional requirements before final publication.

## Short Code Availability Draft

The analysis code and configuration files are available at https://github.com/a1553189184-stack/SCI. The repository includes scripts for metadata preparation, patient-level splitting, training, internal testing, external validation, calibration analysis, Grad-CAM++ failure-mode review, and manuscript table/figure generation.

## Author Confirmation Needed

- Add final repository DOI if a DOI archive is created.
- Add checkpoint release URL or DOI after model weights are deposited.
- Confirm whether the target journal separates Data Availability and Code Availability.
- Confirm final dataset citations in the manuscript reference list.
- Confirm ethics, funding, conflict-of-interest, author-contribution, and corresponding-author declarations.
