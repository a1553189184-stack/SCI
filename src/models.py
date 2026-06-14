from __future__ import annotations

from typing import Any


def create_densenet121(num_labels: int, pretrained: bool = True, dropout: float = 0.0):
    import torch.nn as nn
    from torchvision.models import DenseNet121_Weights, densenet121

    weights = DenseNet121_Weights.DEFAULT if pretrained else None
    model = densenet121(weights=weights)
    in_features = model.classifier.in_features
    if dropout and dropout > 0:
        model.classifier = nn.Sequential(nn.Dropout(p=float(dropout)), nn.Linear(in_features, num_labels))
    else:
        model.classifier = nn.Linear(in_features, num_labels)
    return model


def create_resnet50(num_labels: int, pretrained: bool = True, dropout: float = 0.0):
    import torch.nn as nn
    from torchvision.models import ResNet50_Weights, resnet50

    weights = ResNet50_Weights.DEFAULT if pretrained else None
    model = resnet50(weights=weights)
    in_features = model.fc.in_features
    if dropout and dropout > 0:
        model.fc = nn.Sequential(nn.Dropout(p=float(dropout)), nn.Linear(in_features, num_labels))
    else:
        model.fc = nn.Linear(in_features, num_labels)
    return model


def create_efficientnet_b0(num_labels: int, pretrained: bool = True, dropout: float = 0.0):
    import torch.nn as nn
    from torchvision.models import EfficientNet_B0_Weights, efficientnet_b0

    weights = EfficientNet_B0_Weights.DEFAULT if pretrained else None
    model = efficientnet_b0(weights=weights)
    in_features = model.classifier[-1].in_features
    classifier_dropout = float(dropout) if dropout and dropout > 0 else 0.2
    model.classifier = nn.Sequential(nn.Dropout(p=classifier_dropout, inplace=True), nn.Linear(in_features, num_labels))
    return model


def freeze_backbone(model) -> None:
    for name, param in model.named_parameters():
        param.requires_grad = name.startswith("classifier") or name.startswith("fc")


def unfreeze_all(model) -> None:
    for param in model.parameters():
        param.requires_grad = True


def create_model(config: dict[str, Any], num_labels: int):
    model_cfg = config.get("model", {})
    name = str(model_cfg.get("name", "densenet121")).lower()
    pretrained = bool(model_cfg.get("pretrained", True))
    dropout = float(model_cfg.get("dropout", 0.0))
    if name == "densenet121":
        return create_densenet121(num_labels=num_labels, pretrained=pretrained, dropout=dropout)
    if name == "resnet50":
        return create_resnet50(num_labels=num_labels, pretrained=pretrained, dropout=dropout)
    if name in {"efficientnet_b0", "efficientnet-b0"}:
        return create_efficientnet_b0(num_labels=num_labels, pretrained=pretrained, dropout=dropout)
    raise ValueError(f"Unsupported model.name={name!r}. Expected densenet121, resnet50, or efficientnet_b0.")


