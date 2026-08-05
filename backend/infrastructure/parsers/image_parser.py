"""OCR image parser (RIP-012, prerequisite inline of issue #030).

Engine-agnostic: the OCR backend is resolved by ``get_ocr_engine()`` so JD
code never imports a provider SDK. The shipped default engine reports
unavailable; an implementation registers itself with ``register_ocr_engine``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.infrastructure.parsers.base import ParsedResumeText, ResumeParser, blocks_from_text


@dataclass(frozen=True)
class OCRResult:
    """Plain OCR text plus optional per-page evidence positions."""

    raw_text: str
    pages: int | None = None
    warnings: list[str] = field(default_factory=list)


class OCRAvailabilityError(RuntimeError):
    """The OCR engine is not installed/configured in this environment."""


class OCRTimeoutError(TimeoutError):
    """OCR exceeded the bound and must be treated as a source failure."""


class OCREngine:
    """Provider-agnostic OCR backend contract."""

    @property
    def version(self) -> str:
        return "ocr-none-v0"

    async def extract(self, image_path: str) -> OCRResult:  # pragma: no cover - default unavailable
        raise OCRAvailabilityError("No OCR engine is configured")


_ENGINE: OCREngine | None = None


def register_ocr_engine(engine: OCREngine) -> None:
    """Register the process-wide OCR engine (imported by an implementation)."""
    global _ENGINE
    _ENGINE = engine


def get_ocr_engine() -> OCREngine:
    """Resolve the OCR engine through the registry; JD code imports only this."""
    if _ENGINE is None:
        raise OCRAvailabilityError("No OCR engine is configured")
    return _ENGINE


class ImageOcrParser(ResumeParser):
    """PNG/JPEG parser that extracts text through the OCR registry."""

    @property
    def version(self) -> str:
        return get_ocr_engine().version

    def parse(self, file_path: str) -> ParsedResumeText:
        engine = get_ocr_engine()
        try:
            import asyncio

            result = asyncio.run(engine.extract(file_path))
        except OCRAvailabilityError:
            raise
        except (OCRTimeoutError, TimeoutError) as exc:
            raise OCRTimeoutError("OCR timed out") from exc
        except Exception as exc:
            raise ValueError(f"OCR failed: {exc}") from exc
        return ParsedResumeText(
            raw_text=result.raw_text,
            page_count=result.pages,
            blocks=blocks_from_text(result.raw_text),
        )
