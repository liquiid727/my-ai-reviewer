"""DOC 解析器 —— 处理旧版 Word 二进制格式 (.doc, Word 97-2003)。

python-docx 无法读取 .doc（仅支持 .docx），因此本解析器采用两层策略：
  1. 若环境中存在 LibreOffice/soffice，先将其转换为 .docx，再复用 DocxResumeParser；
  2. 否则降级为「尽力而为」的文本打捞：从二进制流中提取可读字符片段。

注意：降级模式无法完美还原格式与表格，仅保证可抽取正文文本，
仅供后续 LLM 提取环节使用。解析器版本号显式标注 besteffort 以提示下游。
"""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from backend.infrastructure.parsers.base import (
    ParsedResumeText,
    ResumeParser,
    blocks_from_text,
)
from backend.infrastructure.parsers.docx_parser import DocxResumeParser

# 可读字符范围：ASCII 可打印 + 常见 CJK + 全角标点
_PRINTABLE_RE = re.compile(
    r"[\x20-\x7e"
    r"\u4e00-\u9fff"  # CJK 统一表意文字
    r"\u3000-\u303f"  # CJK 符号和标点
    r"\uff00-\uffef"  # 全角字符
    r"]+"
)


def _find_soffice() -> str | None:
    """查找 LibreOffice 可执行文件（soffice / libreoffice）。"""
    for name in ("soffice", "libreoffice"):
        path = shutil.which(name)
        if path:
            return path
    return None


def _try_libreoffice_convert(file_path: str) -> str | None:
    """尝试用 LibreOffice 将 .doc 转为 .docx，返回临时 docx 路径或 None。"""
    soffice = _find_soffice()
    if soffice is None:
        return None
    try:
        out_dir = tempfile.mkdtemp(prefix="docconv_")
        subprocess.run(
            [soffice, "--headless", "--convert-to", "docx", "--outdir", out_dir, file_path],
            check=True,
            capture_output=True,
            timeout=60,
        )
        converted = next(Path(out_dir).glob("*.docx"), None)
        return str(converted) if converted else None
    except (subprocess.SubprocessError, OSError):
        return None


def _best_effort_text(data: bytes) -> str:
    """从二进制流中打捞可读文本片段。"""
    text = data.decode("latin-1", errors="ignore")
    runs = _PRINTABLE_RE.findall(text)
    joined = " ".join(run.strip() for run in runs if run.strip())
    # 折叠多余空白，避免打捞出的碎片过于稀疏
    return re.sub(r"\s{2,}", " ", joined).strip()


class DocResumeParser(ResumeParser):
    """旧版 Word (.doc) 解析器：优先 LibreOffice 转换，降级为文本打捞。"""

    @property
    def version(self) -> str:
        return "doc-legacy-besteffort-v1"

    def parse(self, file_path: str) -> ParsedResumeText:
        converted = _try_libreoffice_convert(file_path)
        if converted:
            return DocxResumeParser().parse(converted)

        with open(file_path, "rb") as f:
            data = f.read()

        raw_text = _best_effort_text(data)
        return ParsedResumeText(
            raw_text=raw_text,
            page_count=None,
            blocks=blocks_from_text(raw_text),
        )
