from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


def _normalize_array_to_uint8(array: np.ndarray, clip_percentiles: tuple[float, float] = (1.0, 99.0)) -> np.ndarray:
    array = array.astype(np.float32)
    lo, hi = np.percentile(array, clip_percentiles)
    if hi <= lo:
        lo, hi = float(array.min()), float(array.max())
    if hi <= lo:
        return np.zeros_like(array, dtype=np.uint8)
    array = np.clip(array, lo, hi)
    array = (array - lo) / (hi - lo)
    return (array * 255.0).round().astype(np.uint8)


def load_dicom_image(path: str | Path, photometric_correction: bool = True, clip_percentiles: tuple[float, float] = (1.0, 99.0)) -> Image.Image:
    import pydicom

    ds = pydicom.dcmread(str(path))
    pixels = ds.pixel_array.astype(np.float32)
    slope = float(getattr(ds, "RescaleSlope", 1.0))
    intercept = float(getattr(ds, "RescaleIntercept", 0.0))
    pixels = pixels * slope + intercept
    if photometric_correction and str(getattr(ds, "PhotometricInterpretation", "")).upper() == "MONOCHROME1":
        pixels = pixels.max() - pixels
    image = _normalize_array_to_uint8(pixels, clip_percentiles=clip_percentiles)
    return Image.fromarray(image).convert("RGB")


def load_cxr_image(path: str | Path, photometric_correction: bool = True, clip_percentiles: tuple[float, float] = (1.0, 99.0)) -> Image.Image:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in {".dcm", ".dicom"}:
        return load_dicom_image(path, photometric_correction=photometric_correction, clip_percentiles=clip_percentiles)
    return Image.open(path).convert("RGB")


def build_transforms(config: dict[str, Any], train: bool):
    from torchvision import transforms
    from torchvision.transforms import InterpolationMode

    image_cfg = config.get("image", {})
    size = int(image_cfg.get("size", 224))
    mean = image_cfg.get("imagenet_mean", [0.485, 0.456, 0.406])
    std = image_cfg.get("imagenet_std", [0.229, 0.224, 0.225])
    aug = image_cfg.get("train_augmentation", {})

    ops = [transforms.Resize((size, size), interpolation=InterpolationMode.BILINEAR)]
    if train:
        if bool(aug.get("random_horizontal_flip", True)):
            ops.append(transforms.RandomHorizontalFlip(p=float(aug.get("horizontal_flip_p", 0.5))))
        rotation = float(aug.get("random_rotation_degrees", 0))
        if rotation > 0:
            ops.append(transforms.RandomRotation(degrees=rotation, interpolation=InterpolationMode.BILINEAR))
    ops.extend([transforms.ToTensor(), transforms.Normalize(mean=mean, std=std)])
    return transforms.Compose(ops)


class CXRImageLoader:
    def __init__(self, photometric_correction: bool = True, clip_percentiles: tuple[float, float] = (1.0, 99.0)) -> None:
        self.photometric_correction = photometric_correction
        self.clip_percentiles = clip_percentiles

    def __call__(self, path: str | Path) -> Image.Image:
        return load_cxr_image(path, photometric_correction=self.photometric_correction, clip_percentiles=self.clip_percentiles)


def image_loader_from_config(config: dict[str, Any]):
    image_cfg = config.get("image", {})
    photometric_correction = bool(image_cfg.get("photometric_correction", True))
    clip = tuple(float(v) for v in image_cfg.get("dicom_percentile_clip", [1.0, 99.0]))
    return CXRImageLoader(photometric_correction=photometric_correction, clip_percentiles=clip)


