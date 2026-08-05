"""JD review-draft application use cases (RIP-011 §6.2, §7.1)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.jd.enums import JDProcessingStep, JDStatus
from backend.domain.jd.schemas import ReviewDraft
from backend.infrastructure.db.models import JobDescriptionModel


class JDReviewError(Exception):
    """Base JD review-draft error."""


class JDReviewConflictError(JDReviewError):
    """Expected review revision is stale."""


class JDReviewNotInReviewError(JDReviewError):
    """JD is not in a reviewable state."""


class JDReviewInvalidDraftError(JDReviewError):
    """Review draft failed schema validation."""


class JDReviewFinalizeError(JDReviewError):
    """Run ownership is stale; no business mutation recorded."""


class JDReviewDraftUseCases:
    """Write a review draft, mark manual edits, and expose current-version usability."""

    async def save_review_draft(
        self,
        session: AsyncSession,
        jd_id: uuid.UUID,
        *,
        expected_review_revision: int,
        draft: ReviewDraft,
    ) -> dict[str, Any]:
        """Revision-safe save of a structured review draft."""
        jd = await session.get(JobDescriptionModel, jd_id)
        if jd is None:
            raise JDReviewNotInReviewError("JD not found")
        if jd.review_revision != expected_review_revision:
            raise JDReviewConflictError(
                f"expected review revision {expected_review_revision}, current {jd.review_revision}"
            )
        if jd.status not in {JDStatus.NEEDS_REVIEW.value, JDStatus.PROCESSING.value}:
            raise JDReviewNotInReviewError(
                f"JD status {jd.status} is not reviewable (need needs_review/processing)"
            )

        # Mark fields the user changed as manual. Compare against the existing
        # draft's provenance: new values that differ from stored llm values become manual.
        prior = jd.review_draft or {}
        updated = self._mark_manual(prior, draft)

        jd.review_draft = updated
        jd.review_revision = jd.review_revision + 1
        jd.status = JDStatus.NEEDS_REVIEW.value
        jd.processing_step = JDProcessingStep.REVIEW.value
        jd.review_error = None
        await session.commit()
        await session.refresh(jd)
        return {
            "jd_id": str(jd.id),
            "review_revision": jd.review_revision,
            "status": jd.status,
            "draft": jd.review_draft,
        }

    async def get_review_draft(
        self,
        session: AsyncSession,
        jd_id: uuid.UUID,
    ) -> dict[str, Any] | None:
        jd = await session.get(JobDescriptionModel, jd_id)
        if jd is None or jd.review_draft is None:
            return None
        return {
            "jd_id": str(jd.id),
            "review_revision": jd.review_revision,
            "status": jd.status,
            "draft": jd.review_draft,
            "has_current_version": jd.current_version_id is not None,
            "current_version_id": str(jd.current_version_id) if jd.current_version_id else None,
        }

    async def finalize_draft_from_run(
        self,
        session: AsyncSession,
        jd_id: uuid.UUID,
        run_id: uuid.UUID,
        draft: ReviewDraft,
    ) -> bool:
        """Write a review draft only when the run still owns the JD (stale-safe)."""
        jd = await session.get(JobDescriptionModel, jd_id)
        if jd is None:
            raise JDReviewFinalizeError("JD not found")
        if jd.processing_run_id != run_id:
            raise JDReviewFinalizeError(
                f"run {run_id} no longer owns JD {jd_id} (current run {jd.processing_run_id})"
            )
        if jd.status not in {JDStatus.PROCESSING.value, JDStatus.DUPLICATE_PENDING.value}:
            raise JDReviewFinalizeError(f"JD status {jd.status} not processing")

        jd.review_draft = draft.model_dump(mode="json")
        jd.review_revision = jd.review_revision + 1
        jd.status = JDStatus.NEEDS_REVIEW.value
        jd.processing_step = JDProcessingStep.REVIEW.value
        jd.review_error = None
        await session.commit()
        return True

    @staticmethod
    def _mark_manual(prior: dict[str, Any], draft: ReviewDraft) -> dict[str, Any]:
        """Return the draft JSON with provenance=manual where values changed."""
        data = draft.model_dump(mode="json")
        prior_items = {
            (item.get("key"), "responsibilities"): item
            for item in (prior.get("responsibilities") or [])
        }
        for kind, items in (
            ("responsibilities", data.get("responsibilities") or []),
            ("required_skills", data.get("required_skills") or []),
            ("preferred_skills", data.get("preferred_skills") or []),
            ("hard_conditions", data.get("hard_conditions") or []),
        ):
            for item in items:
                prev = prior_items.get((item.get("key"), kind))
                if prev and prev.get("value") != item.get("value"):
                    item["provenance"] = "manual"
                elif prev is None and item.get("provenance") != "manual":
                    # A brand-new item added by the user is manual.
                    item["provenance"] = "manual"
        return data
