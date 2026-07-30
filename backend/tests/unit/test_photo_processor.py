"""照片处理器单测 —— 人脸 / 无人脸 / 多人脸 / 降级四路径。

本地环境不安装 imaging 可选依赖（cv2/rembg），故通过 monkeypatch 替换
人脸检测与抠图两个接缝，验证 process_photo 的编排、裁剪与降级逻辑。
"""

import io
from pathlib import Path

import pytest
from PIL import Image

from backend.infrastructure.imaging import (
    BG_COLORS,
    FaceNotFoundError,
    ImageDecodeError,
    ImagingNotAvailableError,
    process_photo,
)
from backend.infrastructure.imaging import photo_processor as pp

FIXTURES = Path(__file__).parent.parent / "fixtures" / "photos"


def _load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _fake_detect(face: tuple[int, int, int, int]):
    """构造返回固定人脸框的检测函数（替代 Haar，避免依赖 cv2）。"""

    def detect(img: Image.Image) -> tuple[int, int, int, int]:
        return face

    return detect


def _fake_remove_background(img: Image.Image) -> Image.Image:
    """替代 rembg：返回带透明边缘的 RGBA 前景。"""
    rgba = img.convert("RGBA")
    # 挖空左上角模拟背景被移除
    for x in range(min(10, rgba.width)):
        for y in range(min(10, rgba.height)):
            rgba.putpixel((x, y), (0, 0, 0, 0))
    return rgba


class TestProcessPhoto:
    """process_photo 主流程。"""

    def test_face_photo_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """人脸照片 → 295x413 PNG，背景替换成功。"""
        monkeypatch.setattr(pp, "_detect_largest_face", _fake_detect((240, 220, 120, 120)))
        monkeypatch.setattr(pp, "_remove_background", _fake_remove_background)

        result = process_photo(_load("face.jpg"), bg_color="blue")

        assert result.background_replaced is True
        assert result.degraded_reason is None
        img = Image.open(io.BytesIO(result.png_bytes))
        assert img.format == "PNG"
        assert img.size == (pp.PHOTO_WIDTH, pp.PHOTO_HEIGHT)

    def test_no_face_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """无人脸照片 → FaceNotFoundError。"""

        def detect(img: Image.Image) -> tuple[int, int, int, int]:
            return pp._select_largest_face([])  # 模拟 Haar 零检出

        monkeypatch.setattr(pp, "_detect_largest_face", detect)

        with pytest.raises(FaceNotFoundError):
            process_photo(_load("no_face.jpg"))

    def test_two_faces_picks_largest(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """多张人脸 → 取面积最大者为裁剪锚点。"""
        big = (188, 228, 144, 144)
        small = (558, 278, 84, 84)
        picked: list[tuple[int, int, int, int]] = []

        def detect(img: Image.Image) -> tuple[int, int, int, int]:
            face = pp._select_largest_face([small, big])
            picked.append(face)
            return face

        monkeypatch.setattr(pp, "_detect_largest_face", detect)
        monkeypatch.setattr(pp, "_remove_background", _fake_remove_background)

        result = process_photo(_load("two_faces.jpg"))

        assert picked == [big]
        assert result.background_replaced is True

    def test_rembg_failure_degrades(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """抠图失败 → 降级仅裁剪+增强，携带 degraded_reason。"""
        monkeypatch.setattr(pp, "_detect_largest_face", _fake_detect((240, 220, 120, 120)))

        def broken_remove(img: Image.Image) -> Image.Image:
            raise RuntimeError("u2net session failed")

        monkeypatch.setattr(pp, "_remove_background", broken_remove)

        result = process_photo(_load("face.jpg"))

        assert result.background_replaced is False
        assert result.degraded_reason is not None
        assert "u2net session failed" in result.degraded_reason
        img = Image.open(io.BytesIO(result.png_bytes))
        assert img.size == (pp.PHOTO_WIDTH, pp.PHOTO_HEIGHT)

    def test_imaging_not_available_not_degraded(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """依赖缺失（ImagingNotAvailableError）不降级，直接抛出。"""
        monkeypatch.setattr(pp, "_detect_largest_face", _fake_detect((240, 220, 120, 120)))

        def missing_dep(img: Image.Image) -> Image.Image:
            raise ImagingNotAvailableError("rembg 未安装")

        monkeypatch.setattr(pp, "_remove_background", missing_dep)

        with pytest.raises(ImagingNotAvailableError):
            process_photo(_load("face.jpg"))

    def test_corrupt_bytes_raises_decode_error(self) -> None:
        """损坏字节 → ImageDecodeError。"""
        with pytest.raises(ImageDecodeError):
            process_photo(b"not-an-image")

    def test_invalid_bg_color_raises(self) -> None:
        """非法背景色 → ValueError（不触及解码/检测）。"""
        with pytest.raises(ValueError, match="不支持的背景色"):
            process_photo(_load("face.jpg"), bg_color="green")


class TestCropBox:
    """一寸裁剪框计算。"""

    def test_aspect_ratio_and_containment(self) -> None:
        """裁剪框保持 295:413 比例且不越界。"""
        left, top, right, bottom = pp._compute_crop_box(600, 800, (240, 220, 120, 120))
        w, h = right - left, bottom - top
        assert 0 <= left < right <= 600
        assert 0 <= top < bottom <= 800
        assert abs(w / h - pp.PHOTO_WIDTH / pp.PHOTO_HEIGHT) < 0.02

    def test_face_horizontally_centered(self) -> None:
        """人脸水平中心与裁剪框中心一致（无越界场景）。"""
        face = (240, 220, 120, 120)
        left, _, right, _ = pp._compute_crop_box(600, 800, face)
        face_cx = face[0] + face[2] / 2
        crop_cx = (left + right) / 2
        assert abs(face_cx - crop_cx) <= 1

    def test_edge_face_shifts_inward(self) -> None:
        """人脸贴边时裁剪框向内平移，不越界。"""
        left, top, right, bottom = pp._compute_crop_box(600, 800, (0, 0, 120, 120))
        assert left >= 0 and top >= 0
        assert right <= 600 and bottom <= 800


class TestBackgroundComposite:
    """背景合成与颜色表。"""

    def test_bg_colors_complete(self) -> None:
        assert set(BG_COLORS) == {"white", "blue", "red"}
        assert BG_COLORS["white"] == (0xFF, 0xFF, 0xFF)
        assert BG_COLORS["blue"] == (0x43, 0x8E, 0xDB)
        assert BG_COLORS["red"] == (0xD4, 0x3D, 0x3D)

    def test_composite_fills_transparent_area(self) -> None:
        """透明区域被目标背景色填充。"""
        fg = Image.new("RGBA", (20, 20), (0, 0, 0, 0))  # 全透明
        out = pp._composite_background(fg, BG_COLORS["red"])
        assert out.mode == "RGB"
        assert out.getpixel((10, 10)) == BG_COLORS["red"]
