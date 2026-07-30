"""证件照美化基础设施 —— 人脸裁剪、背景替换、画质增强（全本地处理）。"""

from backend.infrastructure.imaging.exceptions import (
    FaceNotFoundError,
    ImageDecodeError,
    ImagingNotAvailableError,
)
from backend.infrastructure.imaging.photo_processor import (
    BG_COLORS,
    ProcessedPhoto,
    process_photo,
)

__all__ = [
    "BG_COLORS",
    "FaceNotFoundError",
    "ImageDecodeError",
    "ImagingNotAvailableError",
    "ProcessedPhoto",
    "process_photo",
]
