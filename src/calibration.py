from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .config import load_config, resolve_path
from .inference import predict_to_dataframe
from .utils import ensure_dirs, setup_logging


def sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def brier(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    return float(np.mean((y_prob - y_true) ** 2))


def ece_mce(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> tuple[float, float]:
    bins = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    mce = 0.0
    n = len(y_true)
    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        mask = (y_prob >= lo) & (y_prob < hi if i < n_bins - 1 else y_prob <= hi)
        if not mask.any():
            continue
        conf = float(y_prob[mask].mean())
        acc = float(y_true[mask].mean())
        gap = abs(acc - conf)
        ece += gap * (int(mask.sum()) / max(n, 1))
        mce = max(mce, gap)
    return float(ece), float(mce)


def calibration_slope_intercept(y_true: np.ndarray, y_prob: np.ndarray) -> tuple[float, float]:
    if len(np.unique(y_true)) < 2:
        return float("nan"), float("nan")
    from sklearn.linear_model import LogisticRegression

    x = logit(y_prob).reshape(-1, 1)
    model = LogisticRegression(solver="lbfgs", C=np.inf, max_iter=1000)
    try:
        model.fit(x, y_true.astype(int))
        return float(model.coef_[0][0]), float(model.intercept_[0])
    except Exception:
        return float("nan"), float("nan")


def fit_temperature(logits: np.ndarray, y_true: np.ndarray) -> float:
    from scipy.optimize import minimize_scalar

    def loss(temp: float) -> float:
        probs = sigmoid(logits / max(temp, 1e-3))
        probs = np.clip(probs, 1e-6, 1 - 1e-6)
        return float(-(y_true * np.log(probs) + (1 - y_true) * np.log(1 - probs)).mean())

    result = minimize_scalar(loss, bounds=(0.05, 10.0), method="bounded")
    return float(result.x if result.success else 1.0)


def fit_platt(logits: np.ndarray, y_true: np.ndarray):
    from sklearn.linear_model import LogisticRegression

    models = []
    for j in range(y_true.shape[1]):
        if len(np.unique(y_true[:, j])) < 2:
            models.append(None)
            continue
        model = LogisticRegression(solver="lbfgs", max_iter=1000)
        model.fit(logits[:, [j]], y_true[:, j].astype(int))
        models.append(model)
    return models


def fit_isotonic(probs: np.ndarray, y_true: np.ndarray):
    from sklearn.isotonic import IsotonicRegression

    models = []
    for j in range(y_true.shape[1]):
        if len(np.unique(y_true[:, j])) < 2:
            models.append(None)
            continue
        model = IsotonicRegression(out_of_bounds="clip")
        model.fit(probs[:, j], y_true[:, j])
        models.append(model)
    return models


def apply_calibrators(df: pd.DataFrame, label_cols: list[str], temperature: float, platt_models, isotonic_models) -> pd.DataFrame:
    out = df.copy()
    logits = out[[f"logit_{label}" for label in label_cols]].to_numpy(dtype=float)
    probs = out[[f"prob_{label}" for label in label_cols]].to_numpy(dtype=float)
    temp_probs = sigmoid(logits / max(float(temperature), 1e-3))
    for j, label in enumerate(label_cols):
        out[f"temperature_prob_{label}"] = temp_probs[:, j]
        if platt_models[j] is None:
            out[f"platt_prob_{label}"] = probs[:, j]
        else:
            out[f"platt_prob_{label}"] = platt_models[j].predict_proba(logits[:, [j]])[:, 1]
        if isotonic_models[j] is None:
            out[f"isotonic_prob_{label}"] = probs[:, j]
        else:
            out[f"isotonic_prob_{label}"] = isotonic_models[j].predict(probs[:, j])
    return out


def calibration_metrics_for_df(df: pd.DataFrame, label_cols: list[str], dataset: str, method: str, prob_prefix: str, n_bins: int) -> pd.DataFrame:
    rows = []
    y_true_all = []
    y_prob_all = []
    for label in label_cols:
        y_true = df[f"true_{label}"].to_numpy(dtype=float)
        y_prob = df[f"{prob_prefix}_{label}"].to_numpy(dtype=float)
        slope, intercept = calibration_slope_intercept(y_true, y_prob)
        ece, mce = ece_mce(y_true, y_prob, n_bins=n_bins)
        rows.append(
            {
                "dataset": dataset,
                "method": method,
                "average": "label",
                "label": label,
                "brier": brier(y_true, y_prob),
                "ece": ece,
                "mce": mce,
                "slope": slope,
                "intercept": intercept,
            }
        )
        y_true_all.append(y_true)
        y_prob_all.append(y_prob)
    label_rows = pd.DataFrame(rows)
    macro = {"dataset": dataset, "method": method, "average": "macro", "label": "macro"}
    for metric in ["brier", "ece", "mce", "slope", "intercept"]:
        vals = label_rows[metric].dropna().to_numpy(dtype=float)
        macro[metric] = float(np.mean(vals[np.isfinite(vals)])) if np.isfinite(vals).any() else float("nan")
    y_true_micro = np.concatenate(y_true_all)
    y_prob_micro = np.concatenate(y_prob_all)
    slope, intercept = calibration_slope_intercept(y_true_micro, y_prob_micro)
    ece, mce = ece_mce(y_true_micro, y_prob_micro, n_bins=n_bins)
    micro = {
        "dataset": dataset,
        "method": method,
        "average": "micro",
        "label": "micro",
        "brier": brier(y_true_micro, y_prob_micro),
        "ece": ece,
        "mce": mce,
        "slope": slope,
        "intercept": intercept,
    }
    return pd.concat([label_rows, pd.DataFrame([macro, micro])], ignore_index=True)


def plot_reliability(df: pd.DataFrame, label_cols: list[str], dataset: str, curves_dir: Path, n_bins: int) -> None:
    import matplotlib.pyplot as plt

    methods = {
        "uncalibrated": "prob",
        "temperature": "temperature_prob",
        "platt": "platt_prob",
        "isotonic": "isotonic_prob",
    }
    bins = np.linspace(0, 1, n_bins + 1)
    fig, ax = plt.subplots(figsize=(5.2, 5.0), dpi=150)
    ax.plot([0, 1], [0, 1], "k--", linewidth=1, label="Perfect calibration")
    for method, prefix in methods.items():
        xs, ys = [], []
        for i in range(n_bins):
            lo, hi = bins[i], bins[i + 1]
            y_true_all, y_prob_all = [], []
            for label in label_cols:
                probs = df[f"{prefix}_{label}"].to_numpy(dtype=float)
                true = df[f"true_{label}"].to_numpy(dtype=float)
                mask = (probs >= lo) & (probs < hi if i < n_bins - 1 else probs <= hi)
                y_true_all.extend(true[mask].tolist())
                y_prob_all.extend(probs[mask].tolist())
            if y_prob_all:
                xs.append(float(np.mean(y_prob_all)))
                ys.append(float(np.mean(y_true_all)))
        if xs:
            ax.plot(xs, ys, marker="o", linewidth=1.5, label=method)
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Observed frequency")
    ax.set_title(f"Reliability diagram: {dataset}")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)
    curves_dir.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(curves_dir / f"reliability_{dataset}.png", dpi=300)
    fig.savefig(curves_dir / f"reliability_{dataset}.pdf")
    plt.close(fig)


def run_calibration(config_path: str | Path, checkpoint_path: str | Path | None = None) -> dict[str, str]:
    config = load_config(config_path)
    cal_cfg = config.get("calibration", {})
    eval_cfg = config.get("evaluation", {})
    splits_cfg = config["splits"]
    logger = setup_logging(resolve_path(config, "logs/calibration.log"))

    checkpoint = resolve_path(config, checkpoint_path or eval_cfg.get("checkpoint_path"))
    prefix = resolve_path(config, splits_cfg["output_prefix"])
    calibration_csv = Path(f"{prefix}_calibration.csv")
    internal_csv = Path(f"{prefix}_internal_test.csv")
    external_csv = resolve_path(config, config["vindr"]["output_csv"])
    raw_cal_pred_csv = resolve_path(config, cal_cfg.get("raw_calibration_predictions_csv", "predictions/nih_calibration_predictions.csv"))
    raw_internal_pred_csv = resolve_path(config, cal_cfg.get("raw_internal_predictions_csv", "predictions/internal_test_predictions.csv"))
    raw_external_pred_csv = resolve_path(config, cal_cfg.get("raw_external_predictions_csv", "predictions/external_vindr_predictions.csv"))
    output_dir = resolve_path(config, cal_cfg.get("output_dir", "outputs/calibration"))
    calibrated_csv = resolve_path(config, cal_cfg.get("calibrated_predictions_csv", "outputs/calibration/calibrated_predictions.csv"))
    metrics_csv = resolve_path(config, cal_cfg.get("calibration_metrics_csv", "outputs/calibration/calibration_metrics.csv"))
    curves_dir = resolve_path(config, cal_cfg.get("curves_dir", "figures/calibration"))
    ensure_dirs([raw_cal_pred_csv.parent, raw_internal_pred_csv.parent, raw_external_pred_csv.parent, output_dir, calibrated_csv.parent, metrics_csv.parent, curves_dir])

    logger.info("Generating calibration split predictions from NIH calibration split")
    cal_pred = predict_to_dataframe(config, checkpoint, calibration_csv, raw_cal_pred_csv)
    label_cols = [col.replace("true_", "") for col in cal_pred.columns if col.startswith("true_")]
    internal_pred = pd.read_csv(raw_internal_pred_csv) if raw_internal_pred_csv.exists() else predict_to_dataframe(config, checkpoint, internal_csv, raw_internal_pred_csv)
    external_pred = pd.read_csv(raw_external_pred_csv) if raw_external_pred_csv.exists() else predict_to_dataframe(config, checkpoint, external_csv, raw_external_pred_csv)

    cal_logits = cal_pred[[f"logit_{label}" for label in label_cols]].to_numpy(dtype=float)
    cal_probs = cal_pred[[f"prob_{label}" for label in label_cols]].to_numpy(dtype=float)
    cal_true = cal_pred[[f"true_{label}" for label in label_cols]].to_numpy(dtype=float)
    temperature = fit_temperature(cal_logits, cal_true)
    platt_models = fit_platt(cal_logits, cal_true)
    isotonic_models = fit_isotonic(cal_probs, cal_true)
    logger.info("Fitted calibration models on NIH calibration only. Temperature=%.4f", temperature)

    calibrated_frames = []
    metric_frames = []
    for dataset_name, df in [("NIH_internal_test", internal_pred), ("VinDr_external", external_pred)]:
        calibrated = apply_calibrators(df, label_cols, temperature, platt_models, isotonic_models)
        calibrated["calibration_dataset"] = dataset_name
        calibrated_frames.append(calibrated)
        for method, prefix in [
            ("uncalibrated", "prob"),
            ("temperature", "temperature_prob"),
            ("platt", "platt_prob"),
            ("isotonic", "isotonic_prob"),
        ]:
            metric_frames.append(calibration_metrics_for_df(calibrated, label_cols, dataset_name, method, prefix, n_bins=int(cal_cfg.get("n_bins", 10))))
        plot_reliability(calibrated, label_cols, dataset_name, curves_dir, n_bins=int(cal_cfg.get("n_bins", 10)))

    calibrated_all = pd.concat(calibrated_frames, ignore_index=True)
    metrics = pd.concat(metric_frames, ignore_index=True)
    calibrated_all.to_csv(calibrated_csv, index=False)
    metrics.to_csv(metrics_csv, index=False)
    pd.DataFrame([{"temperature": temperature}]).to_csv(output_dir / "calibrator_parameters.csv", index=False)
    logger.info("Saved calibrated predictions: %s", calibrated_csv)
    logger.info("Saved calibration metrics: %s", metrics_csv)
    return {"calibrated_predictions": str(calibrated_csv), "calibration_metrics": str(metrics_csv), "curves_dir": str(curves_dir)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Fit NIH calibration models and evaluate calibration transfer to VinDr-CXR.")
    parser.add_argument("--config", default="configs/config.yaml")
    parser.add_argument("--checkpoint", default=None)
    args = parser.parse_args()
    print(run_calibration(args.config, checkpoint_path=args.checkpoint))


if __name__ == "__main__":
    main()


