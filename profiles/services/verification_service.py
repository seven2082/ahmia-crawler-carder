import requests
from typing import Optional
from django.utils import timezone
from django.conf import settings

from .registry import register_service
from ..models import OnionProfile
from ..exceptions import VerificationError
from ..constants import VERIFICATION_MAX_FAILURES


@register_service('verification_service')
class VerificationService:
    """Service for owner verification via .well-known file."""

    WELL_KNOWN_PATH = '/.well-known/ahmia-verify.txt'
    TOKEN_PREFIX = 'ahmia-token='

    def start_verification(self, profile: OnionProfile) -> str:
        """Generate verification token for profile."""
        token = profile.generate_verification_token()
        return token

    def check_verification(self, profile: OnionProfile) -> bool:
        """
        Check if verification file exists and contains valid token.
        Returns True if verified, False otherwise.
        """
        if not profile.verification_token:
            return False

        # Check if token expired
        if profile.verification_token_expires and profile.verification_token_expires < timezone.now():
            return False

        # Build URL
        url = f"http://{profile.current_domain}{self.WELL_KNOWN_PATH}"

        try:
            # In production, this would use Tor proxy
            # For now, we just structure the check
            content = self._fetch_verification_file(url)
            if content and self._validate_token(content, profile.verification_token):
                self._mark_verified(profile)
                return True
            else:
                self._record_failure(profile)
                return False
        except Exception:
            self._record_failure(profile)
            return False

    def _fetch_verification_file(self, url: str) -> Optional[str]:
        """Fetch verification file content. Override for Tor in production."""
        # This is a placeholder - real implementation needs Tor proxy
        # For testing, this method can be mocked
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                return response.text
        except requests.RequestException:
            pass
        return None

    def _validate_token(self, content: str, expected_token: str) -> bool:
        """Check if content contains the expected token."""
        for line in content.strip().split('\n'):
            line = line.strip()
            if line.startswith(self.TOKEN_PREFIX):
                token = line[len(self.TOKEN_PREFIX):].strip()
                if token == expected_token:
                    return True
        return False

    def _mark_verified(self, profile: OnionProfile) -> None:
        """Mark profile as verified."""
        profile.is_verified = True
        profile.verification_fail_count = 0
        profile.save(update_fields=['is_verified', 'verification_fail_count', 'updated_at'])

    def _record_failure(self, profile: OnionProfile) -> None:
        """Record verification failure."""
        profile.verification_fail_count += 1
        if profile.verification_fail_count >= VERIFICATION_MAX_FAILURES:
            profile.is_verified = False
            profile.verification_token = ''
            profile.verification_token_expires = None
        profile.save()

    def revoke_verification(self, profile: OnionProfile) -> None:
        """Revoke verification status."""
        profile.clear_verification()
