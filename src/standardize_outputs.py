from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .config import load_config, resolve_path


REQUIRED_STANDARD_FILES = [
    "predictions/internal_test_predictions.csv",
    "predictions/external_vindr_predictions.csv",
    "tables/internal_metrics.csv",
    "tables/external_metrics.csv",
    "tables/internal_external_comparison.csv",
    "tables/performance_drop.csv",
    "tables/calibration_metrics.csv",
    "tables/gradcam_case_index.csv",
    "figures/calibration_curves_internal.png",
    "figures/calibration_curves_external.png",
    "figures/gradcam_internal_examples.png",
    "figures/gradcam_vindr_examples.png",
    "figures/performance_drop_by_label.png",
]


def is_smoke_or_synthetic(path: Path) -> bool:
    lowered = str(path).lower()
    return "smoke" in lowered or "synthetic" in lowered


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def file_status(root: Path) -> pd.DataFrame:
    rows = []
    for rel in REQUIRED_STANDARD_FILES:
        path = root / rel
        rows.append(
            {
                "required_file": rel,
                "exists": path.exists(),
                "bytes": path.stat().st_size if path.exists() else np.nan,
                "path": str(path),
            }
        )
    return pd.DataFrame(rows)


def configured_sources(config: dict[str, Any]) -> dict[str, Path]:
    eval_cfg = config.get("evaluation", {})
    cal_cfg = config.get("calibration", {})
    grad_cfg = config.get("gradcam", {})
    curves_dir = resolve_path(config, cal_cfg.get("curves_dir", "figures/calibration"))
    return {
        "predictions/internal_test_predictions.csv": resolve_path(config, eval_cfg.get("internal_predictions_csv", "predictions/internal_test_predictions.csv")),
        "predictions/external_vindr_predictions.csv": resolve_path(config, eval_cfg.get("external_predictions_csv", "predictions/external_vindr_predictions.csv")),
        "tables/internal_metrics.csv": resolve_path(config, eval_cfg.get("internal_metrics_csv", "outputs/evaluation/internal_metrics.csv")),
        "tables/external_metrics.csv": resolve_path(config, eval_cfg.get("external_metrics_csv", "outputs/evaluation/external_metrics.csv")),
        "tables/internal_external_comparison.csv": resolve_path(config, eval_cfg.get("internal_external_comparison_csv", "outputs/evaluation/internal_external_comparison.csv")),
        "tables/performance_drop.csv": resolve_path(config, eval_cfg.get("performance_drop_csv", "outputs/evaluation/performance_drop.csv")),
        "tables/calibration_metrics.csv": resolve_path(config, cal_cfg.get("calibration_metrics_csv", "outputs/calibration/calibration_metrics.csv")),
        "tables/gradcam_case_index.csv": resolve_path(config, grad_cfg.get("case_index_csv", "outputs/gradcam/case_index.csv")),
        "figures/calibration_curves_internal.png": curves_dir / "reliability_NIH_internal_test.png",
        "figures/calibration_curves_external.png": curves_dir / "reliability_VinDr_external.png",
    }


def copy_standard_sources(config: dict[str, Any], allow_smoke: bool = False) -> pd.DataFrame:
    root = Path(config["project"]["root"]).resolve()
    rows = []
    for rel, src in configured_sources(config).items():
        dst = root / rel
        issue = ""
        copied = False
        if not src.exists():
            issue = "source_missing"
        elif is_smoke_or_synthetic(src) and not allow_smoke:
            issue = "source_is_smoke_or_synthetic"
        else:
            ensure_parent(dst)
            if src.resolve() != dst.resolve():
                shutil.copy2(src, dst)
            copied = True
        rows.append(
            {
                "required_file": rel,
                "source": str(src),
                "destination": str(dst),
                "copied": copied,
                "issue": issue,
            }
        )
    return pd.DataFrame(rows)


def _label_rows(df: pd.DataFrame) -> pd.DataFrame:
    if "average" in df.columns:
        return df[df["average"].astype(str).str.lower().eq("label")].copy()
    return df.copy()


def make_performance_drop_plot(root: Path) -> bool:
    src = root / "tables" / "performance_drop.csv"
    if not src.exists():
        return False
    import matplotlib.pyplot as plt

    df = pd.read_csv(src)
    plot_df = df[(df.get("average", "label") == "label") & (df.get("metric", "") == "auroc")].copy()
    if plot_df.empty:
        return False
    plot_df["absolute_drop"] = pd.to_numeric(plot_df["absolute_drop"], errors="coerce")
    plot_df = plot_df.dropna(subset=["absolute_drop"])
    if plot_df.empty:
        return False
    plot_df = plot_df.sort_values("absolute_drop", ascending=True)
    fig, ax = plt.subplots(figsize=(7.0, 4.0), dpi=150)
    colors = ["#b95f5f" if value > 0 else "#4f7f8f" for value in plot_df["absolute_drop"]]
    ax.barh(plot_df["label"], plot_df["absolute_drop"], color=colors)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Internal minus external AUROC")
    ax.set_ylabel("")
    ax.set_title("External performance drop by label")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    out = root / "figures" / "performance_drop_by_label.png"
    ensure_parent(out)
    fig.savefig(out, dpi=300)
    fig.savefig(out.with_suffix(".pdf"))
    plt.close(fig)
    return True


def _compose_gradcam_panel(case_index: pd.DataFrame, dataset_key: str, output_path: Path, max_cases: int = 12) -> bool:
    from PIL import Image, ImageDraw

    sub = case_index[case_index["analysis_dataset"].astype(str).str.contains(dataset_key, case=False, na=False)].copy()
    if sub.empty or "panel_path" not in sub.columns:
        return False
    images = []
    for _, row in sub.head(max_cases).iterrows():
        panel = Path(str(row["panel_path"]))
        if not panel.exists():
            continue
        img = Image.open(panel).convert("RGB").resize((260, 260))
        tile = Image.new("RGB", (260, 305), "white")
        tile.paste(img, (0, 0))
        draw = ImageDraw.Draw(tile)
        caption = f"{row.get('label', '')} | {row.get('case_type', '')}"
        draw.text((6, 266), caption[:42], fill=(20, 20, 20))
        images.append(tile)
    if not images:
        return False
    cols = min(4, len(images))
    rows = int(np.ceil(len(images) / cols))
    canvas = Image.new("RGB", (cols * 260, rows * 305), "white")
    for i, img in enumerate(images):
        x = (i % cols) * 260
        y = (i // cols) * 305
        canvas.paste(img, (x, y))
    ensure_parent(output_path)
    canvas.save(output_path)
    return True


def make_gradcam_summary_panels(root: Path) -> dict[str, bool]:
    idx = root / "tables" / "gradcam_case_index.csv"
    if not idx.exists():
        return {"internal": False, "external": False}
    case_index = pd.read_csv(idx)
    return {
        "internal": _compose_gradcam_panel(case_index, "NIH_internal", root / "figures" / "gradcam_internal_examples.png"),
        "external": _compose_gradcam_panel(case_index, "VinDr", root / "figures" / "gradcam_vindr_examples.png"),
    }


def make_table_outputs(root: Path, config: dict[str, Any]) -> dict[str, bool]:
    tables = root / "tables"
    made: dict[str, bool] = {}

    internal_pred = root / "predictions" / "internal_test_predictions.csv"
    external_pred = root / "predictions" / "external_vindr_predictions.csv"
    if internal_pred.exists() and external_pred.exists():
        frames = []
        for dataset_name, path in [("NIH internal test", internal_pred), ("VinDr-CXR external", external_pred)]:
            df = pd.read_csv(path)
            patient_n = df["patient_id"].nunique() if "patient_id" in df.columns else np.nan
            image_n = len(df)
            frames.append({"dataset": dataset_name, "patients": patient_n, "images": image_n})
        pd.DataFrame(frames).to_csv(tables / "table1_dataset_characteristics.csv", index=False)
        made["table1_dataset_characteristics.csv"] = True

    label_map = resolve_path(config, config["paths"]["label_map"])
    if label_map.exists():
        import yaml

        data = yaml.safe_load(label_map.read_text(encoding="utf-8"))
        rows = []
        labels_obj = data.get("labels", {})
        if isinstance(labels_obj, list):
            iterable = [(item.get("harmonized", ""), item) for item in labels_obj]
        else:
            iterable = list(labels_obj.items())
        for label, spec in iterable:
            nih_spec = spec.get("nih", {}) if isinstance(spec.get("nih", {}), dict) else {}
            vindr_spec = spec.get("vindr", {}) if isinstance(spec.get("vindr", {}), dict) else {}
            rows.append(
                {
                    "harmonized_label": label,
                    "nih_terms": "; ".join(nih_spec.get("source_labels", []) or spec.get("nih", []) or []),
                    "vindr_terms": "; ".join(vindr_spec.get("source_labels", []) or spec.get("vindr", []) or []),
                    "role": spec.get("role", spec.get("status", "")),
                    "definition_risk": spec.get("definition_risk", ""),
                    "missing_label_rule": spec.get("missing_label_rule", ""),
                }
            )
        pd.DataFrame(rows).to_csv(tables / "table2_label_harmonization.csv", index=False)
        made["table2_label_harmonization.csv"] = True

    int_metrics = tables / "internal_metrics.csv"
    ext_metrics = tables / "external_metrics.csv"
    if int_metrics.exists() and ext_metrics.exists():
        internal = _label_rows(pd.read_csv(int_metrics))
        external = _label_rows(pd.read_csv(ext_metrics))
        internal["dataset"] = "NIH internal test"
        external["dataset"] = "VinDr-CXR external"
        table3 = pd.concat([internal, external], ignore_index=True)
        table3.insert(0, "model", config.get("model", {}).get("name", "densenet121"))
        table3.to_csv(tables / "table3_internal_external_performance.csv", index=False)
        made["table3_internal_external_performance.csv"] = True

        sens_cols = [c for c in ["sensitivity", "specificity", "f1", "accuracy", "ppv", "npv"] if c in table3.columns]
        if sens_cols:
            table3[["model", "dataset", "label", *sens_cols]].to_csv(tables / "table5_sensitivity_subgroup_analysis.csv", index=False)
            made["table5_sensitivity_subgroup_analysis.csv"] = True

    cal_metrics = tables / "calibration_metrics.csv"
    if cal_metrics.exists():
        pd.read_csv(cal_metrics).to_csv(tables / "table4_calibration_metrics.csv", index=False)
        made["table4_calibration_metrics.csv"] = True

    flat = []
    for section in ["image", "dataloader", "model", "training", "evaluation", "calibration", "gradcam"]:
        for key, value in config.get(section, {}).items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            flat.append({"section": section, "parameter": key, "value": value})
    pd.DataFrame(flat).to_csv(tables / "supplementary_table1_hyperparameters.csv", index=False)
    made["supplementary_table1_hyperparameters.csv"] = True

    medmnist_root = root.parent / "cxr_generalization_calibration_paper" / "experiments" / "medmnist_pilot_20260613"
    med_rows = []
    if medmnist_root.exists():
        med_rows.append({"component": "MedMNIST pipeline verification", "path": str(medmnist_root), "status": "available"})
    else:
        med_rows.append({"component": "MedMNIST pipeline verification", "path": "", "status": "not_found"})
    pd.DataFrame(med_rows).to_csv(tables / "supplementary_table2_medmnist_pipeline_verification.csv", index=False)
    made["supplementary_table2_medmnist_pipeline_verification.csv"] = True
    return made


def make_publication_figures(root: Path) -> dict[str, bool]:
    import matplotlib.pyplot as plt

    made: dict[str, bool] = {}
    figures = root / "figures"
    figures.mkdir(parents=True, exist_ok=True)

    # Figure 1: workflow schematic.
    fig, ax = plt.subplots(figsize=(8.2, 2.4), dpi=150)
    ax.axis("off")
    steps = ["NIH ChestX-ray14\ndevelopment", "Patient-level\nsplits", "DenseNet121\ntraining", "Internal test\nperformance", "NIH calibration\nfit only", "VinDr-CXR\nexternal validation"]
    x = np.linspace(0.08, 0.92, len(steps))
    for i, (xi, label) in enumerate(zip(x, steps)):
        ax.text(xi, 0.55, label, ha="center", va="center", fontsize=8, bbox=dict(boxstyle="round,pad=0.35", fc="#f5f5f5", ec="#555555", lw=0.8))
        if i < len(steps) - 1:
            ax.annotate("", xy=(x[i + 1] - 0.065, 0.55), xytext=(xi + 0.065, 0.55), arrowprops=dict(arrowstyle="->", lw=0.8))
    fig.tight_layout()
    fig.savefig(figures / "figure1_study_workflow.png", dpi=300)
    fig.savefig(figures / "figure1_study_workflow.pdf")
    plt.close(fig)
    made["figure1_study_workflow"] = True

    comparison = root / "tables" / "internal_external_comparison.csv"
    if comparison.exists():
        df = pd.read_csv(comparison)
        if {"internal_auroc", "external_auroc", "internal_auprc", "external_auprc"}.issubset(df.columns):
            sub = df[df.get("average", "label") == "label"].copy()
            labels = sub["label"].dropna().tolist()
            fig, axes = plt.subplots(1, 2, figsize=(8.0, 3.8), dpi=150, sharey=True)
            for ax, metric in zip(axes, ["auroc", "auprc"]):
                part = sub.set_index("label").reindex(labels)
                internal_col = f"internal_{metric}"
                external_col = f"external_{metric}"
                part[internal_col] = pd.to_numeric(part[internal_col], errors="coerce")
                part[external_col] = pd.to_numeric(part[external_col], errors="coerce")
                y = np.arange(len(labels))
                ax.plot(part[internal_col], y, "o", label="Internal", color="#3b6ea8")
                ax.plot(part[external_col], y, "s", label="External", color="#b05d55")
                for yi, row in enumerate(part.itertuples()):
                    internal_value = getattr(row, internal_col)
                    external_value = getattr(row, external_col)
                    ax.plot([internal_value, external_value], [yi, yi], color="#bbbbbb", lw=0.8)
                ax.set_title(metric.upper())
                ax.set_xlabel("Score")
                ax.set_xlim(0, 1)
                ax.grid(axis="x", alpha=0.25)
            axes[0].set_yticks(np.arange(len(labels)), labels)
            axes[1].legend(loc="lower right", fontsize=7)
            fig.tight_layout()
            fig.savefig(figures / "figure2_internal_vs_external_auroc_auprc.png", dpi=300)
            fig.savefig(figures / "figure2_internal_vs_external_auroc_auprc.pdf")
            plt.close(fig)
            made["figure2_internal_vs_external_auroc_auprc"] = True

    if (figures / "calibration_curves_internal.png").exists() and (figures / "calibration_curves_external.png").exists():
        from PIL import Image

        imgs = [Image.open(figures / "calibration_curves_internal.png").convert("RGB"), Image.open(figures / "calibration_curves_external.png").convert("RGB")]
        target_h = 520
        resized = [img.resize((int(img.width * target_h / img.height), target_h)) for img in imgs]
        canvas = Image.new("RGB", (sum(img.width for img in resized), target_h), "white")
        x = 0
        for img in resized:
            canvas.paste(img, (x, 0))
            x += img.width
        canvas.save(figures / "figure3_calibration_curves.png")
        made["figure3_calibration_curves"] = True

    grad = make_gradcam_summary_panels(root)
    made.update({f"gradcam_{k}_examples": v for k, v in grad.items()})
    if (figures / "gradcam_internal_examples.png").exists() and (figures / "gradcam_vindr_examples.png").exists():
        from PIL import Image

        imgs = [Image.open(figures / "gradcam_internal_examples.png").convert("RGB"), Image.open(figures / "gradcam_vindr_examples.png").convert("RGB")]
        width = max(img.width for img in imgs)
        canvas = Image.new("RGB", (width, sum(img.height for img in imgs)), "white")
        y = 0
        for img in imgs:
            canvas.paste(img, (0, y))
            y += img.height
        canvas.save(figures / "figure4_gradcam_examples.png")
        made["figure4_gradcam_examples"] = True

    made["performance_drop_by_label"] = make_performance_drop_plot(root)
    if (figures / "performance_drop_by_label.png").exists():
        shutil.copy2(figures / "performance_drop_by_label.png", figures / "figure5_external_performance_drop_by_label.png")
        made["figure5_external_performance_drop_by_label"] = True

    return made


def standardize_and_report(config_path: str | Path, allow_smoke: bool = False) -> dict[str, Any]:
    config = load_config(config_path)
    root = Path(config["project"]["root"]).resolve()
    report_dir = root / "outputs" / "publication_asset_audit"
    report_dir.mkdir(parents=True, exist_ok=True)

    before = file_status(root)
    copy_report = copy_standard_sources(config, allow_smoke=allow_smoke)
    made_plot = make_performance_drop_plot(root)
    made_gradcam = make_gradcam_summary_panels(root)
    table_report = make_table_outputs(root, config)
    figure_report = make_publication_figures(root)
    after = file_status(root)

    before.to_csv(report_dir / "required_outputs_before.csv", index=False)
    copy_report.to_csv(report_dir / "copy_report.csv", index=False)
    after.to_csv(report_dir / "required_outputs_after.csv", index=False)
    payload = {
        "allow_smoke": allow_smoke,
        "all_required_present": bool(after["exists"].all()),
        "missing_required": after.loc[~after["exists"], "required_file"].tolist(),
        "copied_files": int(copy_report["copied"].sum()),
        "performance_drop_plot": made_plot,
        "gradcam_panels": made_gradcam,
        "manuscript_tables": table_report,
        "publication_figures": figure_report,
    }
    (report_dir / "summary.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Standardize verified CXR result outputs for manuscript tables and figures.")
    parser.add_argument("--config", default="configs/config.yaml")
    parser.add_argument("--allow-smoke", action="store_true", help="Allow smoke/synthetic sources. Do not use for manuscript results.")
    args = parser.parse_args()
    payload = standardize_and_report(args.config, allow_smoke=args.allow_smoke)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    if not payload["all_required_present"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()


