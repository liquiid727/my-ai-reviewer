"""证件照处理相关异常。"""


class ImagingError(Exception):
    """照片处理异常基类。"""


class ImageDecodeError(ImagingError):
    """图片损坏或格式不受支持，无法解码。"""


class FaceNotFoundError(ImagingError):
    """照片中未检测到人脸。"""


class ImagingNotAvailableError(ImagingError):
    """imaging 可选依赖（opencv/rembg）未安装。"""
