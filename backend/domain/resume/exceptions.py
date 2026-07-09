"""简历领域异常 —— 定义文件上传和处理过程中的业务异常。"""


class UnsupportedFileFormatError(Exception):
    """上传了不支持的文件格式（如 .exe、.jpg）。"""
    def __init__(self, ext: str) -> None:
        self.ext = ext
        super().__init__(f"Unsupported file format: {ext}")


class FileTooLargeError(Exception):
    """上传的文件超过大小限制。"""
    def __init__(self, size_bytes: int, max_bytes: int) -> None:
        self.size_bytes = size_bytes
        self.max_bytes = max_bytes
        super().__init__(f"File too large: {size_bytes} bytes (max {max_bytes})")


class DuplicateResumeError(Exception):
    """简历文件内容重复（SHA-256 哈希相同）。"""
    def __init__(self, resume_id: str) -> None:
        self.resume_id = resume_id
        super().__init__(f"Duplicate resume: {resume_id}")
