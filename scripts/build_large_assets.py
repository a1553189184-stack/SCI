from __future__ import annotations

import json
import math
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
LABELS = ["Atelectasis", "Cardiomegaly", "Pleural Effusion", "Pneumothorax", "Consolidation", "Edema", "Pneumonia", "No Finding"]


def fmt(x: float, digits: int = 3) -> str:
    try:
        x = float(x)
        if math.isnan(x):
            return "NA"
        return f"{x:.{digits}f}"
    except Exception:
        return str(x)


def label_rows(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["average"].astype(str).eq("label")].copy()


def macro_row(df: pd.DataFrame) -> dict:
    return df[(df["average"].astype(str) == "macro") & (df["label"].astype(str) == "macro")].iloc[0].to_dict()


def add_prevalence(metrics: pd.DataFrame) -> pd.DataFrame:
    out = metrics.copy()
    out["prevalence"] = pd.to_numeric(out["positives"], errors="coerce") / pd.to_numeric(out["n"], errors="coerce")
    return out


def existing_model_outputs(tables: Path) -> list[dict[str, object]]:
    specs = [
        {
            "model": "DenseNet121",
            "internal": tables / "internal_metrics.csv",
            "external": tables / "external_metrics.csv",
            "drop": tables / "performance_drop.csv",
            "calibration": tables / "calibration_metrics.csv",
        },
        {
            "model": "ResNet50",
            "internal": tables / "resnet50_internal_metrics.csv",
            "external": tables / "resnet50_external_metrics.csv",
            "drop": tables / "resnet50_performance_drop.csv",
            "calibration": tables / "resnet50_calibration_metrics.csv",
        },
        {
            "model": "EfficientNet-B0",
            "internal": tables / "efficientnet_b0_internal_metrics.csv",
            "external": tables / "efficientnet_b0_external_metrics.csv",
            "drop": tables / "efficientnet_b0_performance_drop.csv",
            "calibration": tables / "efficientnet_b0_calibration_metrics.csv",
        },
    ]
    return [spec for spec in specs if Path(spec["internal"]).exists() and Path(spec["external"]).exists()]


def model_metric_frame(spec: dict[str, object]) -> pd.DataFrame:
    internal_df = add_prevalence(pd.read_csv(Path(spec["internal"])))
    external_df = add_prevalence(pd.read_csv(Path(spec["external"])))
    return pd.concat(
        [
            label_rows(internal_df).assign(model=spec["model"], dataset_group="NIH internal test"),
            label_rows(external_df).assign(model=spec["model"], dataset_group="VinDr-derived external"),
        ],
        ignore_index=True,
    )


def model_macro_summary(specs: list[dict[str, object]]) -> pd.DataFrame:
    rows = []
    for spec in specs:
        internal_df = pd.read_csv(Path(spec["internal"]))
        external_df = pd.read_csv(Path(spec["external"]))
        internal_macro = macro_row(internal_df)
        external_macro = macro_row(external_df)
        drop_path = Path(spec["drop"])
        auroc_drop = np.nan
        auprc_drop = np.nan
        auroc_relative_drop = np.nan
        if drop_path.exists():
            drop_df = pd.read_csv(drop_path)
            auroc_row = drop_df[(drop_df["average"] == "macro") & (drop_df["label"] == "macro") & (drop_df["metric"] == "auroc")]
            auprc_row = drop_df[(drop_df["average"] == "macro") & (drop_df["label"] == "macro") & (drop_df["metric"] == "auprc")]
            if not auroc_row.empty:
                auroc_drop = auroc_row.iloc[0]["absolute_drop"]
                auroc_relative_drop = auroc_row.iloc[0]["relative_drop"]
            if not auprc_row.empty:
                auprc_drop = auprc_row.iloc[0]["absolute_drop"]
        rows.append(
            {
                "model": spec["model"],
                "internal_macro_auroc": internal_macro["auroc"],
                "internal_macro_auprc": internal_macro["auprc"],
                "external_macro_auroc": external_macro["auroc"],
                "external_macro_auprc": external_macro["auprc"],
                "macro_auroc_absolute_drop": auroc_drop,
                "macro_auroc_relative_drop": auroc_relative_drop,
                "macro_auprc_absolute_drop": auprc_drop,
            }
        )
    return pd.DataFrame(rows)


def save_workflow_figure(path: Path) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(9.0, 2.5), dpi=150)
    ax.axis("off")
    steps = [
        "NIH HF subset\n5,000 images",
        "Patient-level\ntrain/val/cal/test",
        "DenseNet121\n5 epochs",
        "NIH internal test\n95% CI",
        "NIH calibration\nfit only",
        "VinDr-derived external\n1,000 images",
    ]
    x = np.linspace(0.07, 0.93, len(steps))
    for i, (xi, label) in enumerate(zip(x, steps)):
        ax.text(xi, 0.56, label, ha="center", va="center", fontsize=8, bbox=dict(boxstyle="round,pad=0.35", fc="#F4F7FA", ec="#4B5563", lw=0.8))
        if i < len(steps) - 1:
            ax.annotate("", xy=(x[i + 1] - 0.055, 0.56), xytext=(xi + 0.055, 0.56), arrowprops=dict(arrowstyle="->", lw=0.8, color="#374151"))
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=300)
    fig.savefig(path.with_suffix(".pdf"))
    plt.close(fig)


def save_metric_comparison_figure(comp: pd.DataFrame, out: Path) -> None:
    import matplotlib.pyplot as plt

    sub = comp[comp["average"] == "label"].copy()
    labels = sub["label"].tolist()
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 4.2), dpi=150, sharey=True)
    for ax, metric in zip(axes, ["auroc", "auprc"]):
        y = np.arange(len(labels))
        internal = pd.to_numeric(sub[f"internal_{metric}"], errors="coerce")
        external = pd.to_numeric(sub[f"external_{metric}"], errors="coerce")
        ax.plot(internal, y, "o", color="#3366A6", label="NIH internal")
        ax.plot(external, y, "s", color="#B45F55", label="External")
        for yi, i_val, e_val in zip(y, internal, external):
            if np.isfinite(i_val) and np.isfinite(e_val):
                ax.plot([i_val, e_val], [yi, yi], color="#BDBDBD", lw=0.8)
        ax.set_title(metric.upper())
        ax.set_xlim(0, 1)
        ax.set_xlabel("Score")
        ax.grid(axis="x", alpha=0.25)
    axes[0].set_yticks(np.arange(len(labels)), labels)
    axes[1].legend(loc="lower right", fontsize=7)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=300)
    fig.savefig(out.with_suffix(".pdf"))
    plt.close(fig)


def save_performance_drop_figure(drop: pd.DataFrame, out: Path) -> None:
    import matplotlib.pyplot as plt

    sub = drop[(drop["average"] == "label") & (drop["metric"] == "auroc")].copy()
    sub["absolute_drop"] = pd.to_numeric(sub["absolute_drop"], errors="coerce")
    sub = sub.dropna(subset=["absolute_drop"]).sort_values("absolute_drop")
    fig, ax = plt.subplots(figsize=(7.2, 4.0), dpi=150)
    colors = ["#B45F55" if v > 0 else "#4F7F8F" for v in sub["absolute_drop"]]
    ax.barh(sub["label"], sub["absolute_drop"], color=colors)
    ax.axvline(0, color="black", lw=0.8)
    ax.set_xlabel("Internal minus external AUROC")
    ax.set_title("External performance drop by label")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=300)
    fig.savefig(out.with_suffix(".pdf"))
    plt.close(fig)


def compose_side_by_side(images: list[Path], out: Path) -> None:
    from PIL import Image

    opened = [Image.open(p).convert("RGB") for p in images if p.exists()]
    if not opened:
        return
    target_h = 560
    resized = [img.resize((int(img.width * target_h / img.height), target_h)) for img in opened]
    canvas = Image.new("RGB", (sum(img.width for img in resized), target_h), "white")
    x = 0
    for img in resized:
        canvas.paste(img, (x, 0))
        x += img.width
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out)


def compose_gradcam_panel(case_index: pd.DataFrame, dataset_key: str, out: Path, max_cases: int = 12) -> bool:
    from PIL import Image, ImageDraw

    sub = case_index[case_index["analysis_dataset"].astype(str).str.contains(dataset_key, case=False, na=False)].head(max_cases)
    tiles = []
    for _, row in sub.iterrows():
        p = Path(str(row["panel_path"]))
        if not p.exists():
            continue
        img = Image.open(p).convert("RGB").resize((270, 270))
        tile = Image.new("RGB", (270, 315), "white")
        tile.paste(img, (0, 0))
        draw = ImageDraw.Draw(tile)
        draw.text((6, 274), f"{row['label']} | {row['case_type']}"[:44], fill=(20, 20, 20))
        tiles.append(tile)
    if not tiles:
        return False
    cols = min(4, len(tiles))
    rows = int(np.ceil(len(tiles) / cols))
    canvas = Image.new("RGB", (cols * 270, rows * 315), "white")
    for i, tile in enumerate(tiles):
        canvas.paste(tile, ((i % cols) * 270, (i // cols) * 315))
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out)
    return True


def build_assets() -> dict:
    tables = ROOT / "tables_large"
    figs = ROOT / "figures_large"
    outputs = ROOT / "outputs_large"
    tables.mkdir(exist_ok=True)
    figs.mkdir(exist_ok=True)
    outputs.mkdir(exist_ok=True)

    internal = add_prevalence(pd.read_csv(tables / "internal_metrics.csv"))
    external = add_prevalence(pd.read_csv(tables / "external_metrics.csv"))
    comp = pd.read_csv(tables / "internal_external_comparison.csv")
    drop = pd.read_csv(tables / "performance_drop.csv")
    cal = pd.read_csv(tables / "calibration_metrics.csv")
    case_index = pd.read_csv(tables / "gradcam_case_index.csv")
    split = pd.read_csv(ROOT / "splits_large" / "hf_large_nih_split_statistics.csv")
    nih_meta = pd.read_csv(ROOT / "metadata_large" / "hf_large_nih_clean_metadata.csv")
    vindr_meta = pd.read_csv(ROOT / "metadata_large" / "hf_large_vindr_clean_metadata.csv")
    train_log = pd.read_csv(ROOT / "logs_large" / "hf_large_densenet121_train_log.csv")

    # Table 1.
    external_row = pd.DataFrame([{"split": "VinDr-derived external", "n_patients": vindr_meta["patient_id"].nunique(), "n_images": len(vindr_meta)}])
    table1 = pd.concat([split[["split", "n_patients", "n_images"]], external_row], ignore_index=True)
    table1.to_csv(tables / "table1_dataset_characteristics.csv", index=False)

    # Table 2.
    small_table2 = ROOT / "tables" / "table2_label_harmonization.csv"
    if small_table2.exists():
        shutil.copy2(small_table2, tables / "table2_label_harmonization.csv")

    # Table 3 with prevalence and CI.
    model_specs = existing_model_outputs(tables)
    table3 = pd.concat([model_metric_frame(spec) for spec in model_specs], ignore_index=True)
    table3 = table3[["model", "dataset_group"] + [c for c in table3.columns if c not in {"model", "dataset_group"}]]
    table3.to_csv(tables / "table3_internal_external_performance_with_prevalence_ci.csv", index=False)
    macro_comparison = model_macro_summary(model_specs)
    macro_comparison.to_csv(tables / "table3_model_macro_comparison.csv", index=False)

    # Table 4.
    cal.to_csv(tables / "table4_calibration_metrics.csv", index=False)

    # Table 5 threshold and subgroup summary.
    threshold_cols = ["dataset", "label", "prevalence", "sensitivity", "specificity", "f1", "accuracy", "ppv", "npv"]
    threshold_summary = table3[threshold_cols].copy()
    threshold_summary.to_csv(tables / "table5_sensitivity_threshold_analysis.csv", index=False)

    subgroup_rows = []
    from src.metrics import compute_metrics

    pred = pd.read_csv(ROOT / "predictions_large" / "internal_test_predictions.csv")
    labels = [c.replace("true_", "") for c in pred.columns if c.startswith("true_")]
    for col in ["sex", "view_position"]:
        if col in pred.columns:
            for value, group in pred.groupby(col):
                if len(group) < 20:
                    continue
                m = compute_metrics(group, labels, f"NIH_internal_test_{col}_{value}")
                macro = macro_row(m)
                subgroup_rows.append(
                    {
                        "dataset": "NIH_internal_test",
                        "subgroup_variable": col,
                        "subgroup": value,
                        "n_images": len(group),
                        "n_patients": group["patient_id"].nunique(),
                        "macro_auroc": macro["auroc"],
                        "macro_auprc": macro["auprc"],
                        "macro_f1": macro["f1"],
                        "macro_accuracy": macro["accuracy"],
                    }
                )
    subgroup = pd.DataFrame(subgroup_rows)
    subgroup.to_csv(tables / "table5_subgroup_analysis.csv", index=False)

    # Supplementary small public-subset table.
    small_registry = ROOT / "outputs" / "manuscript_value_registry.json"
    if small_registry.exists():
        small = json.loads(small_registry.read_text(encoding="utf-8"))
        pd.DataFrame(
            [
                {
                    "experiment": "original small public subset",
                    "nih_images": small["dataset"]["nih_images"],
                    "external_images": small["dataset"]["vindr_images"],
                    "internal_macro_auroc": small["performance"]["internal_macro_auroc"],
                    "internal_macro_auprc": small["performance"]["internal_macro_auprc"],
                    "external_macro_auroc": small["performance"]["external_macro_auroc"],
                    "external_macro_auprc": small["performance"]["external_macro_auprc"],
                }
            ]
        ).to_csv(tables / "supplementary_table_original_small_public_subset.csv", index=False)

    # Figures.
    save_workflow_figure(figs / "figure1_study_workflow_large.png")
    save_metric_comparison_figure(comp, figs / "figure2_internal_vs_external_auroc_auprc_ci.png")
    shutil.copy2(figs / "calibration" / "hf_large" / "reliability_NIH_internal_test.png", figs / "calibration_curves_internal.png")
    shutil.copy2(figs / "calibration" / "hf_large" / "reliability_VinDr_external.png", figs / "calibration_curves_external.png")
    compose_side_by_side([figs / "calibration_curves_internal.png", figs / "calibration_curves_external.png"], figs / "figure3_calibration_curves_large.png")
    compose_gradcam_panel(case_index, "NIH_internal", figs / "gradcam_internal_examples.png")
    compose_gradcam_panel(case_index, "VinDr", figs / "gradcam_vindr_examples.png")
    compose_side_by_side([figs / "gradcam_internal_examples.png", figs / "gradcam_vindr_examples.png"], figs / "figure4_gradcam_failure_modes_large.png")
    save_performance_drop_figure(drop, figs / "performance_drop_by_label.png")
    shutil.copy2(figs / "performance_drop_by_label.png", figs / "figure5_external_performance_drop_by_label.png")
    small_fig = ROOT / "figures" / "figure2_internal_vs_external_auroc_auprc.png"
    if small_fig.exists():
        shutil.copy2(small_fig, figs / "supplementary_figure_original_small_subset.png")

    mi = macro_row(internal)
    me = macro_row(external)
    d_auc = drop[(drop["average"] == "macro") & (drop["label"] == "macro") & (drop["metric"] == "auroc")].iloc[0].to_dict()
    cal_i_uncal = cal[(cal["dataset"] == "NIH_internal_test") & (cal["method"] == "uncalibrated") & (cal["average"] == "macro")].iloc[0].to_dict()
    cal_i_temp = cal[(cal["dataset"] == "NIH_internal_test") & (cal["method"] == "temperature") & (cal["average"] == "macro")].iloc[0].to_dict()
    cal_e_temp = cal[(cal["dataset"] == "VinDr_external") & (cal["method"] == "temperature") & (cal["average"] == "macro")].iloc[0].to_dict()
    registry = {
        "dataset": {
            "nih_images": int(len(nih_meta)),
            "nih_patients": int(nih_meta["patient_id"].nunique()),
            "external_images": int(len(vindr_meta)),
            "external_patients": int(vindr_meta["patient_id"].nunique()),
            "split_images": table1.to_dict(orient="records"),
            "external_note": "VinDr-CXR/VinBigData-derived public PNG cached subset; Edema and Pneumonia unavailable externally.",
        },
        "training": {
            "epochs_completed": int(train_log["epoch"].max()),
            "best_val_macro_auprc": fmt(train_log["best_val_macro_auprc"].max()),
            "best_epoch": int(train_log.loc[train_log["val_macro_auprc"].idxmax(), "epoch"]),
        },
        "performance": {
            "internal_macro_auroc": fmt(mi["auroc"]),
            "internal_macro_auprc": fmt(mi["auprc"]),
            "external_macro_auroc": fmt(me["auroc"]),
            "external_macro_auprc": fmt(me["auprc"]),
            "macro_auroc_absolute_drop": fmt(d_auc["absolute_drop"]),
            "macro_auroc_relative_drop": fmt(d_auc["relative_drop"]),
        },
        "calibration": {
            "internal_uncalibrated_macro_brier": fmt(cal_i_uncal["brier"]),
            "internal_uncalibrated_macro_ece": fmt(cal_i_uncal["ece"]),
            "internal_uncalibrated_macro_mce": fmt(cal_i_uncal["mce"]),
            "internal_uncalibrated_macro_slope": fmt(cal_i_uncal["slope"]),
            "internal_uncalibrated_macro_intercept": fmt(cal_i_uncal["intercept"]),
            "internal_temperature_macro_ece": fmt(cal_i_temp["ece"]),
            "external_temperature_macro_ece": fmt(cal_e_temp["ece"]),
        },
        "gradcam": {
            "n_cases": int(len(case_index)),
            "case_counts": {str(k): int(v) for k, v in case_index.groupby(["analysis_dataset", "case_type"]).size().to_dict().items()},
        },
        "model_comparison": macro_comparison.to_dict(orient="records"),
    }
    (outputs / "manuscript_value_registry_large.json").write_text(json.dumps(registry, indent=2), encoding="utf-8")
    return registry


if __name__ == "__main__":
    print(json.dumps(build_assets(), indent=2))


