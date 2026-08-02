import hashlib
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from ..constants import TrustLevel, TRUST_LEVEL_THRESHOLD, COOLDOWN_HOURS

User = get_user_model()


class Contributor(models.Model):
    """Tracks edit history for trust levels."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='contributor_profile'
    )
    session_key = models.CharField(max_length=64, blank=True, default='', db_index=True)
    ip_hash = models.CharField(max_length=64, blank=True, default='')

    approved_edits = models.IntegerField(default=0)
    rejected_edits = models.IntegerField(default=0)
    trust_level = models.IntegerField(
        choices=[(l.value, l.name) for l in TrustLevel],
        default=TrustLevel.ANONYMOUS
    )

    is_banned = models.BooleanField(default=False)
    cooldown_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['session_key']),
            models.Index(fields=['trust_level']),
        ]

    def __str__(self):
        if self.user:
            return f"Contributor: {self.user.username}"
        return f"Contributor: anon-{self.session_key[:8]}"

    @classmethod
    def hash_ip(cls, ip_address: str) -> str:
        """Hash IP address for privacy-preserving rate limiting."""
        return hashlib.sha256(ip_address.encode()).hexdigest()

    @classmethod
    def get_or_create_for_request(cls, request) -> 'Contributor':
        """Get or create contributor from request context."""
        if request.user.is_authenticated:
            contrib, _ = cls.objects.get_or_create(
                user=request.user,
                defaults={'trust_level': TrustLevel.NEW}
            )
            return contrib

        session_key = request.session.session_key or ''
        if not session_key:
            request.session.create()
            session_key = request.session.session_key

        ip = cls._get_client_ip(request)
        ip_hash = cls.hash_ip(ip) if ip else ''

        contrib, created = cls.objects.get_or_create(
            session_key=session_key,
            defaults={
                'ip_hash': ip_hash,
                'trust_level': TrustLevel.ANONYMOUS
            }
        )
        return contrib

    @staticmethod
    def _get_client_ip(request) -> str:
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')

    def recalculate_trust_level(self):
        """Update trust level based on approved edits.

        Note: TRUSTED is granted once approved_edits crosses the
        threshold, regardless of whether the contributor is tied to
        an authenticated user. Below the threshold, authenticated
        contributors are NEW and anonymous (session-only) contributors
        remain ANONYMOUS.
        """
        if self.trust_level == TrustLevel.MODERATOR:
            return  # Moderators are manually promoted

        if self.approved_edits >= TRUST_LEVEL_THRESHOLD:
            self.trust_level = TrustLevel.TRUSTED
        elif self.user:
            self.trust_level = TrustLevel.NEW
        else:
            self.trust_level = TrustLevel.ANONYMOUS

        self.save(update_fields=['trust_level'])

    @property
    def can_auto_approve(self) -> bool:
        """Check if edits from this contributor are auto-approved."""
        return self.trust_level >= TrustLevel.TRUSTED

    @property
    def can_review_edits(self) -> bool:
        """Check if this contributor can review others' edits."""
        return self.trust_level >= TrustLevel.TRUSTED

    @property
    def is_moderator(self) -> bool:
        return self.trust_level == TrustLevel.MODERATOR

    @property
    def is_on_cooldown(self) -> bool:
        """Check if contributor is on submission cooldown."""
        if not self.cooldown_until:
            return False
        return timezone.now() < self.cooldown_until

    def apply_cooldown(self):
        """Apply rate limit cooldown."""
        self.cooldown_until = timezone.now() + timedelta(hours=COOLDOWN_HOURS)
        self.save(update_fields=['cooldown_until'])

    def record_approved_edit(self):
        """Record an approved edit and recalculate trust."""
        self.approved_edits += 1
        self.save(update_fields=['approved_edits'])
        self.recalculate_trust_level()

    def record_rejected_edit(self):
        """Record a rejected edit, apply cooldown if threshold met."""
        self.rejected_edits += 1
        self.save(update_fields=['rejected_edits'])
        # Apply cooldown after 2 consecutive rejections
        if self.rejected_edits >= 2 and self.rejected_edits % 2 == 0:
            self.apply_cooldown()
