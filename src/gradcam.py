from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from PIL import Image

from .config import load_config, resolve_path
from .inference import load_checkpoint_model
from .preprocessing import build_transforms, load_cxr_image
from .utils import ensure_dirs, setup_logging


def _case_type(true_value: int, pred_value: int) -> str:
    if true_value == 1 and pred_value == 1:
        return "true_positive"
    if true_value == 0 and pred_value == 1:
        return "false_positive"
    if true_value == 1 and pred_value == 0:
        return "false_negative"
    return "true_negative"


def select_cases(pred_df: pd.DataFrame, label_cols: list[str], max_cases_per_label: int) -> pd.DataFrame:
    rows = []
    for label in label_cols:
        if f"pred_{label}" not in pred_df.columns:
            pred_df[f"pred_{label}"] = (pred_df[f"prob_{label}"] >= 0.5).astype(int)
        tmp = pred_df.copy()
        tmp["_case_type"] = [
            _case_type(int(t), int(p))
            for t, p in zip(tmp[f"true_{label}"].to_numpy(), tmp[f"pred_{label}"].to_numpy())
        ]
        for case_type in ["true_positive", "false_positive", "false_negative", "true_negative"]:
            sub = tmp[tmp["_case_type"] == case_type].copy()
            if sub.empty:
                continue
            if case_type in {"true_positive", "false_positive"}:
                sub = sub.sort_values(f"prob_{label}", ascending=False)
            elif case_type == "false_negative":
                sub = sub.sort_values(f"prob_{label}", ascending=True)
            else:
                sub = sub.sort_values(f"prob_{label}", ascending=True)
            take = sub.head(max_cases_per_label)
            for _, row in take.iterrows():
                rows.append(
                    {
                        "label": label,
                        "case_type": case_type,
                        "dataset": row.get("dataset", ""),
                        "patient_id": row["patient_id"],
                        "image_id": row["image_id"],
                        "image_path": row.get("image_path", ""),
                        "true": int(row[f"true_{label}"]),
                        "pred": int(row[f"pred_{label}"]),
                        "probability": float(row[f"prob_{label}"]),
                    }
                )
    return pd.DataFrame(rows)


def _find_image_path(pred_row: pd.Series, metadata_df: pd.DataFrame | None = None) -> str:
    if "image_path" in pred_row and isinstance(pred_row["image_path"], str) and pred_row["image_path"]:
        return pred_row["image_path"]
    if metadata_df is not None:
        match = metadata_df[metadata_df["image_id"].astype(str) == str(pred_row["image_id"])]
        if not match.empty and "image_path" in match.columns:
            return str(match.iloc[0]["image_path"])
    raise FileNotFoundError(f"Image path not found for image_id={pred_row['image_id']}")


def _overlay_heatmap(image: Image.Image, heatmap: np.ndarray) -> Image.Image:
    import cv2

    rgb = np.array(image.convert("RGB").resize((heatmap.shape[1], heatmap.shape[0])))
    heat = np.uint8(255 * np.clip(heatmap, 0, 1))
    heat_color = cv2.applyColorMap(heat, cv2.COLORMAP_JET)
    heat_color = cv2.cvtColor(heat_color, cv2.COLOR_BGR2RGB)
    overlay = np.uint8(0.55 * rgb + 0.45 * heat_color)
    return Image.fromarray(overlay)


def _boxes_for_case(boxes_df: pd.DataFrame | None, image_id: str, label: str) -> pd.DataFrame:
    if boxes_df is None or boxes_df.empty:
        return pd.DataFrame()
    if "image_id" not in boxes_df.columns:
        return pd.DataFrame()
    sub = boxes_df[boxes_df["image_id"].astype(str) == str(image_id)].copy()
    if sub.empty:
        return sub
    if "source_label" in sub.columns:
        canon = label.strip().lower()
        sub = sub[sub["source_label"].astype(str).str.lower().str.contains(canon.split()[0], regex=False, na=False)]
    return sub


def localization_metrics(heatmap: np.ndarray, boxes: pd.DataFrame, quantile: float, original_size: tuple[int, int]) -> dict[str, float]:
    if boxes.empty:
        return {"pointing_game_hit": np.nan, "heatmap_box_overlap": np.nan}
    h, w = heatmap.shape
    orig_w, orig_h = original_size
    sx = w / max(orig_w, 1)
    sy = h / max(orig_h, 1)
    max_y, max_x = np.unravel_index(np.argmax(heatmap), heatmap.shape)
    hit = 0
    box_mask = np.zeros_like(heatmap, dtype=bool)
    for _, box in boxes.iterrows():
        x_min = int(np.clip(float(box["x_min"]) * sx, 0, w - 1))
        x_max = int(np.clip(float(box["x_max"]) * sx, 0, w - 1))
        y_min = int(np.clip(float(box["y_min"]) * sy, 0, h - 1))
        y_max = int(np.clip(float(box["y_max"]) * sy, 0, h - 1))
        if x_min <= max_x <= x_max and y_min <= max_y <= y_max:
            hit = 1
        box_mask[y_min : y_max + 1, x_min : x_max + 1] = True
    heat_mask = heatmap >= np.quantile(heatmap, quantile)
    intersection = float((heat_mask & box_mask).sum())
    union = float((heat_mask | box_mask).sum())
    return {"pointing_game_hit": float(hit), "heatmap_box_overlap": intersection / union if union else np.nan}


def gradcam_target_layers(model) -> list:
    if hasattr(model, "features"):
        return [model.features[-1]]
    if hasattr(model, "layer4"):
        return [model.layer4[-1]]
    raise ValueError(f"Cannot infer Grad-CAM target layer for model type {type(model).__name__}")


def run_gradcam(config_path: str | Path, checkpoint_path: str | Path | None = None, max_cases_per_label: int | None = None) -> dict[str, str]:
    import torch
    from pytorch_grad_cam import GradCAMPlusPlus
    from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget

    config = load_config(config_path)
    grad_cfg = config.get("gradcam", {})
    eval_cfg = config.get("evaluation", {})
    logger = setup_logging(resolve_path(config, "logs/gradcam.log"))
    checkpoint = resolve_path(config, checkpoint_path or eval_cfg.get("checkpoint_path"))
    output_dir = resolve_path(config, grad_cfg.get("output_dir", "figures/gradcam"))
    case_index_csv = resolve_path(config, grad_cfg.get("case_index_csv", "outputs/gradcam/case_index.csv"))
    loc_csv = resolve_path(config, grad_cfg.get("localization_metrics_csv", "outputs/gradcam/localization_metrics.csv"))
    ensure_dirs([output_dir, case_index_csv.parent, loc_csv.parent])

    internal_pred = pd.read_csv(resolve_path(config, grad_cfg.get("internal_predictions_csv", eval_cfg.get("internal_predictions_csv"))))
    external_pred = pd.read_csv(resolve_path(config, grad_cfg.get("external_predictions_csv", eval_cfg.get("external_predictions_csv"))))
    label_cols = [col.replace("true_", "") for col in internal_pred.columns if col.startswith("true_")]
    max_cases = int(max_cases_per_label or grad_cfg.get("max_cases_per_label", 1))
    internal_cases = select_cases(internal_pred, label_cols, max_cases)
    internal_cases["analysis_dataset"] = "NIH_internal_test"
    external_cases = select_cases(external_pred, label_cols, max_cases)
    external_cases["analysis_dataset"] = "VinDr_external"
    cases = pd.concat([internal_cases, external_cases], ignore_index=True)

    internal_meta = pd.read_csv(Path(f"{resolve_path(config, config['splits']['output_prefix'])}_internal_test.csv"))
    external_meta = pd.read_csv(resolve_path(config, config["vindr"]["output_csv"]))
    boxes_path = resolve_path(config, config["vindr"].get("boxes_output_csv"))
    boxes_df = pd.read_csv(boxes_path) if boxes_path is not None and boxes_path.exists() else None

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, checkpoint_labels, _ = load_checkpoint_model(config, checkpoint, device)
    transform = build_transforms(config, train=False)
    target_layers = gradcam_target_layers(model)
    cam = GradCAMPlusPlus(model=model, target_layers=target_layers)
    loc_rows = []
    case_rows = []

    for idx, row in cases.iterrows():
        label = row["label"]
        label_idx = checkpoint_labels.index(label)
        meta = internal_meta if row["analysis_dataset"] == "NIH_internal_test" else external_meta
        image_path = _find_image_path(row, meta)
        image = load_cxr_image(image_path)
        tensor = transform(image).unsqueeze(0).to(device)
        grayscale_cam = cam(input_tensor=tensor, targets=[ClassifierOutputTarget(label_idx)])[0]
        overlay = _overlay_heatmap(image, grayscale_cam)
        subdir = output_dir / row["analysis_dataset"] / label.replace(" ", "_") / row["case_type"]
        subdir.mkdir(parents=True, exist_ok=True)
        out_png = subdir / f"{row['image_id']}_{label.replace(' ', '_')}_{row['case_type']}.png"
        overlay.save(out_png)
        case_record = dict(row)
        case_record["panel_path"] = str(out_png)
        case_rows.append(case_record)
        if row["analysis_dataset"] == "VinDr_external":
            boxes = _boxes_for_case(boxes_df, str(row["image_id"]), label)
            loc = localization_metrics(grayscale_cam, boxes, quantile=float(grad_cfg.get("heatmap_quantile", 0.80)), original_size=image.size)
            loc.update({"image_id": row["image_id"], "label": label, "case_type": row["case_type"], "panel_path": str(out_png)})
            loc_rows.append(loc)

    pd.DataFrame(case_rows).to_csv(case_index_csv, index=False)
    pd.DataFrame(loc_rows).to_csv(loc_csv, index=False)
    logger.info("Saved Grad-CAM case index: %s", case_index_csv)
    logger.info("Saved localization metrics: %s", loc_csv)
    logger.info("Grad-CAM is for failure-mode analysis only, not proof of clinical reasoning.")
    return {"case_index": str(case_index_csv), "localization_metrics": str(loc_csv), "output_dir": str(output_dir)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Grad-CAM++ failure-mode panels for NIH internal and VinDr external cases.")
    parser.add_argument("--config", default="configs/config.yaml")
    parser.add_argument("--checkpoint", default=None)
    parser.add_argument("--max-cases-per-label", type=int, default=None)
    args = parser.parse_args()
    print(run_gradcam(args.config, checkpoint_path=args.checkpoint, max_cases_per_label=args.max_cases_per_label))


if __name__ == "__main__":
    main()


