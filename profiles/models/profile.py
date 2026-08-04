import secrets
import hashlib
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.text import slugify
from datetime import timedelta

from .base import BaseModel
from .taxonomy import Category, Tag
from ..constants import ProfileStatus, MigrationSource, VERIFICATION_TOKEN_EXPIRY_DAYS

User = get_user_model()


def generate_deterministic_slug(domain: str) -> str:
    """Generate deterministic slug from domain. Same domain = same slug always."""
    domain_clean = domain.lower().replace('.onion', '').strip()
    hash_part = hashlib.sha256(domain_clean.encode()).hexdigest()[:12]
    return f"site-{hash_part}"


class OnionProfile(BaseModel):
    """Primary model representing a single onion website."""

    slug = models.SlugField(max_length=100, unique=True, db_index=True)
    current_domain = models.CharField(max_length=70, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='profiles'
    )
    tags = models.ManyToManyField(Tag, through='ProfileTag', related_name='profiles')
    logo = models.TextField(blank=True, default='')  # Base64 data URI

    # Verification
    is_verified = models.BooleanField(default=False, db_index=True)
    verification_token = models.CharField(max_length=64, blank=True, default='')
    verification_token_expires = models.DateTimeField(null=True, blank=True)
    verification_fail_count = models.IntegerField(default=0)
    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_profiles'
    )

    # Cached stats from ES
    page_count = models.IntegerField(default=0)
    last_seen = models.DateTimeField(null=True, blank=True)

    # Live status from crawler
    is_online = models.BooleanField(default=False, db_index=True)
    response_time_ms = models.IntegerField(null=True, blank=True)
    last_checked = models.DateTimeField(null=True, blank=True)
    screenshot = models.TextField(blank=True, default='')  # Base64 PNG or URL
    screenshot_synced = models.BooleanField(default=False, db_index=True)

    # Status
    status = models.CharField(
        max_length=20,
        choices=ProfileStatus.CHOICES,
        default=ProfileStatus.ACTIVE,
        db_index=True
    )

    class Meta:
        ordering = ['-last_seen', 'name']
        indexes = [
            models.Index(fields=['status', 'is_verified']),
            models.Index(fields=['category', 'status']),
        ]

    def __str__(self):
        return self.name

    def generate_verification_token(self) -> str:
        """Generate a new verification token."""
        token = secrets.token_hex(32)
        self.verification_token = token
        self.verification_token_expires = timezone.now() + timedelta(days=VERIFICATION_TOKEN_EXPIRY_DAYS)
        self.save(update_fields=['verification_token', 'verification_token_expires', 'updated_at'])
        return token

    def clear_verification(self):
        """Remove verification status."""
        self.is_verified = False
        self.verification_token = ''
        self.verification_token_expires = None
        self.verification_fail_count = 0
        self.owner = None
        self.save(update_fields=[
            'is_verified', 'verification_token', 'verification_token_expires',
            'verification_fail_count', 'owner', 'updated_at'
        ])

    @property
    def is_active(self) -> bool:
        return self.status == ProfileStatus.ACTIVE

    @property
    def truncated_domain(self) -> str:
        """Return shortened domain for display: first8...last8.onion"""
        if len(self.current_domain) > 20:
            name = self.current_domain.replace('.onion', '')
            return f"{name[:8]}...{name[-8:]}.onion"
        return self.current_domain

    def save(self, *args, **kwargs):
        """Auto-generate deterministic slug from domain if not set."""
        if not self.slug and self.current_domain:
            self.slug = generate_deterministic_slug(self.current_domain)
        super().save(*args, **kwargs)


class ProfileTag(models.Model):
    """Through model for profile-tag relationship."""
    profile = models.ForeignKey(OnionProfile, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['profile', 'tag']


class DomainHistory(models.Model):
    """Tracks URL changes over time."""
    profile = models.ForeignKey(
        OnionProfile,
        on_delete=models.CASCADE,
        related_name='domain_history'
    )
    domain = models.CharField(max_length=70, db_index=True)
    was_active_from = models.DateTimeField()
    was_active_to = models.DateTimeField()
    migration_type = models.CharField(
        max_length=20,
        choices=MigrationSource.CHOICES
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-was_active_to']
        verbose_name_plural = 'Domain histories'

    def __str__(self):
        return f"{self.domain} ({self.was_active_from.date()} - {self.was_active_to.date()})"
