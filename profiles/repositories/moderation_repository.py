from django.db.models import QuerySet
from uuid import UUID

from ..models import ProfileEdit, MigrationReport
from ..constants import EditStatus


class ModerationRepository:
    """Repository for moderation queue operations."""

    def get_pending_edits(self) -> QuerySet[ProfileEdit]:
        """Get all pending edits."""
        return ProfileEdit.objects.filter(
            status=EditStatus.PENDING
        ).select_related('profile', 'submitted_by').order_by('created_at')

    def get_pending_migrations(self) -> QuerySet[MigrationReport]:
        """Get all pending migration reports."""
        return MigrationReport.objects.filter(
            status=EditStatus.PENDING
        ).select_related('profile', 'submitted_by').order_by('created_at')

    def get_edits_for_profile(self, profile_id: UUID) -> QuerySet[ProfileEdit]:
        """Get all edits for a specific profile."""
        return ProfileEdit.objects.filter(
            profile_id=profile_id
        ).select_related('submitted_by', 'reviewed_by').order_by('-created_at')

    def get_edit_by_id(self, edit_id: int) -> ProfileEdit:
        """Get edit by ID."""
        return ProfileEdit.objects.select_related(
            'profile', 'submitted_by'
        ).get(pk=edit_id)

    def get_migration_by_id(self, migration_id: int) -> MigrationReport:
        """Get migration report by ID."""
        return MigrationReport.objects.select_related(
            'profile', 'submitted_by'
        ).get(pk=migration_id)

    def count_pending(self) -> dict:
        """Count pending edits and migrations."""
        return {
            'edits': ProfileEdit.objects.filter(status=EditStatus.PENDING).count(),
            'migrations': MigrationReport.objects.filter(status=EditStatus.PENDING).count(),
        }
