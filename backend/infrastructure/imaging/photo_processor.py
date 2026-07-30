"""证件照处理核心流程 —— 人脸检测、一寸裁剪、背景替换、画质增强。

全部本地处理（Pillow + OpenCV Haar + rembg），照片不发送任何第三方服务。
opencv/rembg 为可选依赖（pyproject `imaging` 分组），在函数内部懒加载；
未安装时抛 ImagingNotAvailableError，由 API 层映射为 HTTP 501。
"""

import io
import logging
from dataclasses import dataclass

from PIL import Image, ImageEnhance, ImageOps

from backend.infrastructure.imaging.exceptions import (
    FaceNotFoundError,
    ImageDecodeError,
    ImagingNotAvailableError,
)

logger = logging.getLogger(__name__)

# 一寸证件照标准像素（295×413 @ 300dpi）
PHOTO_WIDTH = 295
PHOTO_HEIGHT = 413

# 背景色（证件照常用三色）
BG_COLORS: dict[str, tuple[int, int, int]] = {
    "white": (0xFF, 0xFF, 0xFF),
    "blue": (0x43, 0x8E, 0xDB),
    "red": (0xD4, 0x3D, 0x3D),
}

# 裁剪构图参数：人脸高约占画面 40%，头顶留白约占画面高 7%
FACE_HEIGHT_RATIO = 0.40
HEAD_MARGIN_RATIO = 0.07

# 增强系数（温和，避免失真）
BRIGHTNESS_FACTOR = 1.05
CONTRAST_FACTOR = 1.05
SHARPNESS_FACTOR = 1.1


@dataclass
class ProcessedPhoto:
    """照片处理结果。

    Attributes:
        png_bytes: 处理后的 295x413 PNG 图片字节。
        background_replaced: 是否成功完成抠图换底。
        degraded_reason: 抠图失败降级时的原因说明（成功时为 None）。
    """

    png_bytes: bytes
    background_replaced: bool
    degraded_reason: str | None = None


def _decode_image(data: bytes) -> Image.Image:
    """解码并规整输入图片：校验可解码、EXIF 方向矫正、转 RGB。"""
    try:
        raw = Image.open(io.BytesIO(data))
        raw.load()
    except Exception as exc:  # Pillow 对损坏文件抛多种异常，统一收敛
        raise ImageDecodeError(f"图片无法解码: {exc}") from exc
    # 手机照片常带 EXIF 旋转标记，先矫正再处理
    img = ImageOps.exif_transpose(raw)
    return img.convert("RGB")


def _select_largest_face(faces: list[tuple[int, int, int, int]]) -> tuple[int, int, int, int]:
    """从候选人脸框中选面积最大者（主体人物）。

    空列表抛 FaceNotFoundError。
    """
    if not faces:
        raise FaceNotFoundError("照片中未检测到人脸")
    return max(faces, key=lambda f: f[2] * f[3])


def _detect_largest_face(img: Image.Image) -> tuple[int, int, int, int]:
    """用 OpenCV Haar cascade 检测人脸，返回面积最大的 (x, y, w, h)。

    0 张人脸抛 FaceNotFoundError；cv2 未安装抛 ImagingNotAvailableError。
    """
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise ImagingNotAvailableError("opencv 未安装，请安装 imaging 可选依赖") from exc

    gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
    candidates = [(int(x), int(y), int(w), int(h)) for x, y, w, h in faces]
    return _select_largest_face(candidates)


def _compute_crop_box(
    img_width: int, img_height: int, face: tuple[int, int, int, int]
) -> tuple[int, int, int, int]:
    """以人脸框为锚计算一寸比例（295:413）裁剪框，返回 (left, top, right, bottom)。

    构图规则：人脸水平居中；人脸高约占画面 40%；头顶留白约 7%；越界时向内收缩。
    """
    fx, fy, fw, fh = face
    aspect = PHOTO_WIDTH / PHOTO_HEIGHT

    # 由人脸高反推目标画面高，并推出宽
    crop_h = fh / FACE_HEIGHT_RATIO
    crop_w = crop_h * aspect

    # 画面不能超过原图：等比收缩
    scale = min(img_width / crop_w, img_height / crop_h, 1.0)
    crop_w *= scale
    crop_h *= scale

    # 人脸水平居中；头顶上方留白 7% 画面高
    face_cx = fx + fw / 2
    left = face_cx - crop_w / 2
    top = fy - crop_h * HEAD_MARGIN_RATIO

    # 越界时向内平移
    left = max(0.0, min(left, img_width - crop_w))
    top = max(0.0, min(top, img_height - crop_h))

    return int(left), int(top), int(left + crop_w), int(top + crop_h)


def _remove_background(img: Image.Image) -> Image.Image:
    """rembg 抠图，返回 RGBA 前景。rembg 未安装抛 ImagingNotAvailableError。"""
    try:
        from rembg import remove
    except ImportError as exc:
        raise ImagingNotAvailableError("rembg 未安装，请安装 imaging 可选依赖") from exc

    result = remove(img)
    if not isinstance(result, Image.Image):  # rembg 按输入类型返回，Image 入则 Image 出
        raise TypeError(f"rembg 返回类型异常: {type(result)}")
    return result.convert("RGBA")


def _composite_background(fg_rgba: Image.Image, bg_color: tuple[int, int, int]) -> Image.Image:
    """将 RGBA 前景合成到纯色背景上，返回 RGB 图。"""
    background = Image.new("RGBA", fg_rgba.size, (*bg_color, 255))
    return Image.alpha_composite(background, fg_rgba).convert("RGB")


def _enhance(img: Image.Image) -> Image.Image:
    """温和画质增强：亮度 / 对比度 / 锐化。"""
    img = ImageEnhance.Brightness(img).enhance(BRIGHTNESS_FACTOR)
    img = ImageEnhance.Contrast(img).enhance(CONTRAST_FACTOR)
    return ImageEnhance.Sharpness(img).enhance(SHARPNESS_FACTOR)


def process_photo(data: bytes, bg_color: str = "white") -> ProcessedPhoto:
    """证件照处理主流程。

    流程：解码校验 → 人脸检测 → 一寸裁剪 → 抠图换底 → 增强 → 输出 295x413 PNG。
    抠图失败时降级为"仅裁剪 + 增强"，通过 degraded_reason 告知原因；
    人脸检测失败（FaceNotFoundError）与依赖缺失（ImagingNotAvailableError）不降级，直接抛出。

    Args:
        data: 原始图片字节（jpg/png）。
        bg_color: 背景色，white / blue / red 之一。

    Raises:
        ValueError: bg_color 不合法。
        ImageDecodeError: 图片损坏无法解码。
        FaceNotFoundError: 未检测到人脸。
        ImagingNotAvailableError: imaging 可选依赖未安装。
    """
    if bg_color not in BG_COLORS:
        raise ValueError(f"不支持的背景色: {bg_color}，可选 {sorted(BG_COLORS)}")

    img = _decode_image(data)
    face = _detect_largest_face(img)
    img = img.crop(_compute_crop_box(img.width, img.height, face))

    background_replaced = False
    degraded_reason: str | None = None
    try:
        fg = _remove_background(img)
        img = _composite_background(fg, BG_COLORS[bg_color])
        background_replaced = True
    except ImagingNotAvailableError:
        raise  # 依赖缺失属环境问题，不降级
    except Exception as exc:  # 抠图失败降级：仅裁剪 + 增强
        degraded_reason = f"背景替换失败，已降级为仅裁剪与增强: {exc}"
        logger.warning("rembg 抠图失败，降级处理: %s", exc)

    img = _enhance(img)
    img = img.resize((PHOTO_WIDTH, PHOTO_HEIGHT), Image.Resampling.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return ProcessedPhoto(
        png_bytes=buf.getvalue(),
        background_replaced=background_replaced,
        degraded_reason=degraded_reason,
    )
