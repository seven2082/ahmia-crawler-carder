from typing import Optional
from django.utils import timezone
from datetime import timedelta

from .registry import register_service
from ..models import ProfileEdit, MigrationReport, OnionProfile, Contributor
from ..repositories import ModerationRepository
from ..constants import EditStatus, MigrationSource, RATE_LIMIT_EDITS_PER_HOUR
from ..exceptions import RateLimitExceededError, ContributorBannedError


@register_service('moderation_service')
class ModerationService:
    """Service for edit submission and approval workflow."""

    def __init__(self):
        self._repo = ModerationRepository()

    def submit_edit(
        self,
        profile: OnionProfile,
        field_name: str,
        new_value: str,
        contributor: Contributor
    ) -> ProfileEdit:
        """Submit an edit for review."""
        self._check_contributor_allowed(contributor)

        old_value = getattr(profile, field_name, '')
        if hasattr(old_value, 'slug'):  # Handle FK like category
            old_value = old_value.slug

        edit = ProfileEdit.objects.create(
            profile=profile,
            field_name=field_name,
            old_value=str(old_value),
            new_value=new_value,
            submitted_by=contributor,
            status=EditStatus.PENDING
        )

        # Auto-approve for trusted contributors
        if contributor.can_auto_approve:
            edit.approve(contributor)

        return edit

    def approve_edit(self, edit: ProfileEdit, reviewer: Contributor, notes: str = '') -> None:
        """Approve an edit."""
        edit.approve(reviewer, notes)

    def reject_edit(self, edit: ProfileEdit, reviewer: Contributor, notes: str = '') -> None:
        """Reject an edit."""
        edit.reject(reviewer, notes)

    def submit_migration(
        self,
        old_domain: str,
        new_domain: str,
        contributor: Contributor,
        evidence_url: str = '',
        evidence_text: str = ''
    ) -> MigrationReport:
        """Submit a migration report."""
        self._check_contributor_allowed(contributor)

        # Try to find existing profile
        try:
            profile = OnionProfile.objects.get(current_domain=old_domain)
        except OnionProfile.DoesNotExist:
            profile = None

        report = MigrationReport.objects.create(
            profile=profile,
            old_domain=old_domain,
            new_domain=new_domain,
            source=MigrationSource.COMMUNITY,
            evidence_url=evidence_url,
            evidence_text=evidence_text,
            submitted_by=contributor,
            status=EditStatus.PENDING
        )

        return report

    def _check_contributor_allowed(self, contributor: Contributor) -> None:
        """Check if contributor can submit edits."""
        if contributor.is_banned:
            raise ContributorBannedError("Contributor is banned")

        if contributor.is_on_cooldown:
            raise RateLimitExceededError("Contributor is on cooldown")

        # Check rate limit
        recent_edits = ProfileEdit.objects.filter(
            submitted_by=contributor,
            created_at__gte=timezone.now() - timedelta(hours=1)
        ).count()

        if recent_edits >= RATE_LIMIT_EDITS_PER_HOUR:
            raise RateLimitExceededError("Rate limit exceeded")
