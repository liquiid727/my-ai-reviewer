"""Public pagination policy and candidate-selection behavior."""

from io import BytesIO

import fitz
import pytest
from playwright.async_api import Error as PlaywrightError
from pydantic import ValidationError

from backend.domain.resume import enums as resume_enums
from backend.domain.resume_builder.enums import LayoutDensity, LayoutMode
from backend.domain.resume_builder.schemas import (
    DraftItem,
    DraftSection,
    LayoutPolicy,
    ResumeDraft,
)
from backend.infrastructure.rendering.pdf_renderer import (
    LayoutCandidate,
    PdfRenderer,
    count_pdf_pages,
    select_layout_candidate,
)


def test_auto_pages_selects_loosest_density_at_smallest_page_count() -> None:
    candidates = [
        LayoutCandidate(LayoutDensity.LOOSE, b"loose", 3),
        LayoutCandidate(LayoutDensity.NORMAL, b"normal", 2),
        LayoutCandidate(LayoutDensity.TIGHT, b"tight", 2),
        LayoutCandidate(LayoutDensity.COMPACT, b"compact", 2),
    ]

    selected, target_met = select_layout_candidate(candidates, LayoutPolicy())

    assert selected.density == LayoutDensity.NORMAL
    assert selected.page_count == 2
    assert target_met is True


def test_target_pages_selects_loosest_exact_match() -> None:
    candidates = [
        LayoutCandidate(LayoutDensity.LOOSE, b"loose", 3),
        LayoutCandidate(LayoutDensity.NORMAL, b"normal", 2),
        LayoutCandidate(LayoutDensity.TIGHT, b"tight", 2),
        LayoutCandidate(LayoutDensity.COMPACT, b"compact", 1),
    ]
    policy = LayoutPolicy(mode=LayoutMode.TARGET_PAGES, target_page_count=2)

    selected, target_met = select_layout_candidate(candidates, policy)

    assert selected.density == LayoutDensity.NORMAL
    assert selected.page_count == 2
    assert target_met is True


def test_unmet_target_falls_back_to_automatic_result() -> None:
    candidates = [
        LayoutCandidate(LayoutDensity.LOOSE, b"loose", 4),
        LayoutCandidate(LayoutDensity.NORMAL, b"normal", 3),
        LayoutCandidate(LayoutDensity.TIGHT, b"tight", 3),
        LayoutCandidate(LayoutDensity.COMPACT, b"compact", 3),
    ]
    policy = LayoutPolicy(mode=LayoutMode.TARGET_PAGES, target_page_count=2)

    selected, target_met = select_layout_candidate(candidates, policy)

    assert selected.density == LayoutDensity.NORMAL
    assert selected.page_count == 3
    assert target_met is False


def test_target_page_count_is_required_only_in_target_mode() -> None:
    with pytest.raises(ValidationError):
        LayoutPolicy(mode=LayoutMode.TARGET_PAGES)

    with pytest.raises(ValidationError):
        LayoutPolicy(mode=LayoutMode.AUTO_PAGES, target_page_count=2)


def test_count_pdf_pages_reads_generated_pdf() -> None:
    document = fitz.open()
    for _ in range(3):
        document.new_page()
    pdf_bytes = document.tobytes()
    document.close()

    assert count_pdf_pages(pdf_bytes) == 3


def test_count_pdf_pages_rejects_invalid_pdf() -> None:
    with pytest.raises(ValueError, match="Invalid PDF"):
        count_pdf_pages(BytesIO(b"not a pdf").getvalue())


async def test_renderer_reports_real_multi_page_result_and_unmet_target() -> None:
    sections = [
        DraftSection(
            section_type=resume_enums.ResumeSectionType.WORK_EXPERIENCE,
            title=f"Experience {section_index}",
            items=[
                DraftItem(
                    heading=f"Company {item_index}",
                    bullets=[
                        f"Delivered measurable result {bullet_index} with a detailed explanation."
                        for bullet_index in range(5)
                    ],
                )
                for item_index in range(4)
            ],
            order=section_index,
        )
        for section_index in range(6)
    ]
    draft = ResumeDraft(
        title="Long resume",
        identity={"name": "Test Candidate"},
        sections=sections,
        layout_policy=LayoutPolicy(mode=LayoutMode.TARGET_PAGES, target_page_count=1),
    )

    try:
        pdf_bytes, page_count, target_met, _density = await PdfRenderer().render_pdf(draft)
    except PlaywrightError as exc:
        if "MachPortRendezvousServer" in str(exc) or "Permission denied" in str(exc):
            pytest.skip("Chromium launch is blocked by the macOS sandbox")
        raise

    assert page_count >= 2
    assert count_pdf_pages(pdf_bytes) == page_count
    assert target_met is False
