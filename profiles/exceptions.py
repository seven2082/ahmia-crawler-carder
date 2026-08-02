class ProfileException(Exception):
    """Base exception for profile system."""
    pass


class ProfileNotFoundError(ProfileException):
    """Profile does not exist."""
    pass


class DuplicateProfileError(ProfileException):
    """Profile with this domain already exists."""
    pass


class VerificationError(ProfileException):
    """Verification process failed."""
    pass


class RateLimitExceededError(ProfileException):
    """User exceeded rate limit."""
    pass


class InsufficientTrustError(ProfileException):
    """User lacks required trust level."""
    pass


class ContributorBannedError(ProfileException):
    """Contributor is banned."""
    pass


class InvalidLogoError(ProfileException):
    """Logo validation failed."""
    pass
