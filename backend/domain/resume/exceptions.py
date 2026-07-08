class UnsupportedFileFormatError(Exception):
    def __init__(self, ext: str) -> None:
        self.ext = ext
        super().__init__(f"Unsupported file format: {ext}")


class FileTooLargeError(Exception):
    def __init__(self, size_bytes: int, max_bytes: int) -> None:
        self.size_bytes = size_bytes
        self.max_bytes = max_bytes
        super().__init__(f"File too large: {size_bytes} bytes (max {max_bytes})")


class DuplicateResumeError(Exception):
    def __init__(self, resume_id: str) -> None:
        self.resume_id = resume_id
        super().__init__(f"Duplicate resume: {resume_id}")
