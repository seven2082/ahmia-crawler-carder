from .registry import register_service
from ..models import Contributor
from ..constants import TrustLevel


@register_service('trust_service')
class TrustService:
    """Service for contributor trust level checks."""

    def get_or_create_contributor(self, request) -> Contributor:
        """Get or create contributor from request."""
        return Contributor.get_or_create_for_request(request)

    def can_edit(self, contributor: Contributor) -> bool:
        """Check if contributor can submit edits."""
        if contributor.is_banned:
            return False
        if contributor.is_on_cooldown:
            return False
        return True

    def can_review(self, contributor: Contributor) -> bool:
        """Check if contributor can review edits."""
        if contributor.is_banned:
            return False
        return contributor.can_review_edits

    def can_moderate(self, contributor: Contributor) -> bool:
        """Check if contributor has moderator privileges."""
        if contributor.is_banned:
            return False
        return contributor.is_moderator

    def promote_to_moderator(self, contributor: Contributor) -> None:
        """Promote contributor to moderator."""
        contributor.trust_level = TrustLevel.MODERATOR
        contributor.save(update_fields=['trust_level'])

    def ban_contributor(self, contributor: Contributor) -> None:
        """Ban a contributor."""
        contributor.is_banned = True
        contributor.save(update_fields=['is_banned'])

    def unban_contributor(self, contributor: Contributor) -> None:
        """Unban a contributor."""
        contributor.is_banned = False
        contributor.save(update_fields=['is_banned'])
