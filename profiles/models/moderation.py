from django.db import models
from django.utils import timezone

from .profile import OnionProfile, DomainHistory
from .contributor import Contributor
from ..constants import EditStatus, MigrationSource


class ProfileEdit(models.Model):
    """Pending and historical edits."""

    profile = models.ForeignKey(
        OnionProfile,
        on_delete=models.CASCADE,
        related_name='edits'
    )
    field_name = models.CharField(max_length=50)
    old_value = models.TextField(blank=True, default='')
    new_value = models.TextField()

    submitted_by = models.ForeignKey(
        Contributor,
        on_delete=models.SET_NULL,
        null=True,
        related_name='submitted_edits'
    )
    status = models.CharField(
        max_length=20,
        choices=EditStatus.CHOICES,
        default=EditStatus.PENDING,
        db_index=True
    )
    reviewed_by = models.ForeignKey(
        Contributor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_edits'
    )
    review_notes = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['profile', 'status']),
        ]

    def __str__(self):
        return f"Edit {self.field_name} on {self.profile.slug}"

    def approve(self, reviewer: Contributor, notes: str = ''):
        """Approve and apply this edit."""
        self.status = EditStatus.APPROVED
        self.reviewed_by = reviewer
        self.review_notes = notes
        self.reviewed_at = timezone.now()
        self.save()
        self._apply_to_profile()
        if self.submitted_by:
            self.submitted_by.record_approved_edit()

    def reject(self, reviewer: Contributor, notes: str = ''):
        """Reject this edit."""
        self.status = EditStatus.REJECTED
        self.reviewed_by = reviewer
        self.review_notes = notes
        self.reviewed_at = timezone.now()
        self.save()
        if self.submitted_by:
            self.submitted_by.record_rejected_edit()

    def _apply_to_profile(self):
        """Apply the edit to the profile."""
        if self.field_name == 'category':
            from .taxonomy import Category
            self.profile.category = Category.objects.get(slug=self.new_value)
        elif hasattr(self.profile, self.field_name):
            setattr(self.profile, self.field_name, self.new_value)
        self.profile.save()


class MigrationReport(models.Model):
    """Reports of URL changes."""

    profile = models.ForeignKey(
        OnionProfile,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='migration_reports'
    )
    old_domain = models.CharField(max_length=70, db_index=True)
    new_domain = models.CharField(max_length=70)
    source = models.CharField(
        max_length=20,
        choices=MigrationSource.CHOICES
    )
    evidence_url = models.URLField(blank=True, default='')
    evidence_text = models.TextField(blank=True, default='')

    status = models.CharField(
        max_length=20,
        choices=EditStatus.CHOICES,
        default=EditStatus.PENDING,
        db_index=True
    )
    submitted_by = models.ForeignKey(
        Contributor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submitted_migrations'
    )
    reviewed_by = models.ForeignKey(
        Contributor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_migrations'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['old_domain']),
        ]

    def __str__(self):
        return f"Migration: {self.old_domain[:20]}... → {self.new_domain[:20]}..."

    def approve(self, reviewer: Contributor):
        """Approve and apply migration."""
        self.status = EditStatus.APPROVED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.save()
        self._apply_migration()
        if self.submitted_by:
            self.submitted_by.record_approved_edit()

    def reject(self, reviewer: Contributor):
        """Reject this migration report."""
        self.status = EditStatus.REJECTED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.save()
        if self.submitted_by:
            self.submitted_by.record_rejected_edit()

    def _apply_migration(self):
        """Apply migration to profile."""
        if not self.profile:
            try:
                self.profile = OnionProfile.objects.get(current_domain=self.old_domain)
            except OnionProfile.DoesNotExist:
                return

        # Record history
        DomainHistory.objects.create(
            profile=self.profile,
            domain=self.old_domain,
            was_active_from=self.profile.created_at,
            was_active_to=timezone.now(),
            migration_type=self.source
        )

        # Update current domain
        self.profile.current_domain = self.new_domain
        self.profile.save(update_fields=['current_domain', 'updated_at'])
