from enum import IntEnum


class TrustLevel(IntEnum):
    ANONYMOUS = 0
    NEW = 1
    TRUSTED = 2
    MODERATOR = 3


class ProfileStatus:
    ACTIVE = 'active'
    OFFLINE = 'offline'
    BANNED = 'banned'

    CHOICES = [
        (ACTIVE, 'Active'),
        (OFFLINE, 'Offline'),
        (BANNED, 'Banned'),
    ]


class EditStatus:
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'

    CHOICES = [
        (PENDING, 'Pending'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
    ]


class MigrationSource:
    OWNER = 'owner'
    COMMUNITY = 'community'
    CRAWLER = 'crawler'

    CHOICES = [
        (OWNER, 'Owner'),
        (COMMUNITY, 'Community'),
        (CRAWLER, 'Crawler'),
    ]


TRUST_LEVEL_THRESHOLD = 5
RATE_LIMIT_EDITS_PER_HOUR = 10
COOLDOWN_HOURS = 24
VERIFICATION_TOKEN_EXPIRY_DAYS = 7
VERIFICATION_RECHECK_DAYS = 30
VERIFICATION_MAX_FAILURES = 3
DEFAULT_CATEGORY_SLUG = 'other'
LOGO_MAX_SIZE_BYTES = 100 * 1024  # 100KB
