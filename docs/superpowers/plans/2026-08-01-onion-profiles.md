# Onion Profile System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a modular, extensible profile/directory system for Ahmia that auto-generates profiles from ES crawl data, supports owner verification, community edits with trust-based moderation, and URL migration tracking.

**Architecture:** Separate Django app (`profiles`) with layered architecture: models → repositories → services → views. Each layer has single responsibility. Services are pluggable via registry pattern for extensibility. All business logic in services, views are thin.

**Tech Stack:** Django 5.2, SQLite (PostgreSQL-compatible), Elasticsearch 8.x, django-ratelimit

## Global Constraints

- Python 3.10+, Django 5.2+
- All models use UUID primary keys for portability
- No raw SQL — use Django ORM exclusively
- All user input sanitized via Django forms
- Rate limiting on all public write endpoints
- Tests required before implementation (TDD)
- Commits after each task completion

---

## File Structure

```
profiles/
├── __init__.py
├── apps.py
├── constants.py                    # Enums, choices, magic values
├── exceptions.py                   # Custom exceptions
├── models/
│   ├── __init__.py                 # Re-exports all models
│   ├── base.py                     # Abstract base models
│   ├── profile.py                  # OnionProfile, DomainHistory
│   ├── taxonomy.py                 # Category, Tag, ProfileTag
│   ├── contributor.py              # Contributor, trust system
│   └── moderation.py               # ProfileEdit, MigrationReport
├── repositories/
│   ├── __init__.py
│   ├── base.py                     # Abstract repository
│   ├── profile_repository.py       # Profile CRUD + queries
│   ├── contributor_repository.py   # Contributor lookups
│   └── moderation_repository.py    # Edit/migration queues
├── services/
│   ├── __init__.py
│   ├── registry.py                 # Service registry for plugins
│   ├── profile_service.py          # Profile business logic
│   ├── verification_service.py     # Owner verification
│   ├── moderation_service.py       # Edit approval workflow
│   ├── trust_service.py            # Trust level calculations
│   ├── sync_service.py             # ES → DB sync
│   ├── slug_service.py             # Slug generation
│   └── elasticsearch_service.py    # ES queries
├── forms/
│   ├── __init__.py
│   ├── profile_forms.py            # Edit, claim forms
│   └── moderation_forms.py         # Review forms
├── views/
│   ├── __init__.py
│   ├── mixins.py                   # Shared view mixins
│   ├── profile_views.py            # List, detail, edit, claim
│   ├── directory_views.py          # Category, tag browsing
│   └── moderation_views.py         # Queue, review
├── urls.py
├── admin.py
├── signals.py                      # Post-save hooks
├── middleware.py                   # Contributor tracking
├── management/
│   └── commands/
│       ├── sync_profiles.py
│       ├── update_stats.py
│       ├── check_verifications.py
│       ├── detect_migrations.py
│       └── seed_categories.py
├── templates/profiles/
│   ├── base_profiles.html
│   ├── profile_list.html
│   ├── profile_detail.html
│   ├── profile_edit.html
│   ├── profile_claim.html
│   ├── profile_history.html
│   ├── category_list.html
│   ├── moderation_queue.html
│   ├── edit_review.html
│   └── partials/
│       ├── _profile_card.html
│       ├── _stats_box.html
│       ├── _edit_diff.html
│       └── _pagination.html
├── migrations/
└── tests/
    ├── __init__.py
    ├── conftest.py                 # Pytest fixtures
    ├── factories.py                # Model factories
    ├── test_models/
    ├── test_repositories/
    ├── test_services/
    ├── test_views/
    └── test_commands/
```

---

## Task 1: App Scaffold & Base Models

**Files:**
- Create: `profiles/__init__.py`
- Create: `profiles/apps.py`
- Create: `profiles/constants.py`
- Create: `profiles/exceptions.py`
- Create: `profiles/models/__init__.py`
- Create: `profiles/models/base.py`
- Modify: `ahmia/settings.py` (add to INSTALLED_APPS)
- Test: `profiles/tests/__init__.py`
- Test: `profiles/tests/conftest.py`

**Interfaces:**
- Produces: `BaseModel` abstract class with `id` (UUID), `created_at`, `updated_at`
- Produces: `constants.TrustLevel` enum (ANONYMOUS=0, NEW=1, TRUSTED=2, MODERATOR=3)
- Produces: `constants.ProfileStatus` enum (ACTIVE, OFFLINE, BANNED)
- Produces: `constants.EditStatus` enum (PENDING, APPROVED, REJECTED)
- Produces: `constants.MigrationSource` enum (OWNER, COMMUNITY, CRAWLER)

- [ ] **Step 1: Create app directory structure**

```bash
mkdir -p profiles/models profiles/repositories profiles/services profiles/forms profiles/views profiles/management/commands profiles/templates/profiles/partials profiles/tests/test_models profiles/tests/test_repositories profiles/tests/test_services profiles/tests/test_views profiles/tests/test_commands
touch profiles/__init__.py profiles/models/__init__.py profiles/repositories/__init__.py profiles/services/__init__.py profiles/forms/__init__.py profiles/views/__init__.py profiles/tests/__init__.py
```

- [ ] **Step 2: Write constants.py**

```python
# profiles/constants.py
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
```

- [ ] **Step 3: Write exceptions.py**

```python
# profiles/exceptions.py
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
```

- [ ] **Step 4: Write base model**

```python
# profiles/models/base.py
import uuid
from django.db import models

class BaseModel(models.Model):
    """Abstract base for all profile models."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
```

- [ ] **Step 5: Write apps.py**

```python
# profiles/apps.py
from django.apps import AppConfig

class ProfilesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'profiles'
    verbose_name = 'Onion Profiles'

    def ready(self):
        from . import signals  # noqa: F401
```

- [ ] **Step 6: Create empty signals.py**

```python
# profiles/signals.py
# Signal handlers will be added in later tasks
```

- [ ] **Step 7: Write conftest.py with basic fixtures**

```python
# profiles/tests/conftest.py
import pytest
from django.test import RequestFactory

@pytest.fixture
def request_factory():
    return RequestFactory()

@pytest.fixture
def anonymous_request(request_factory):
    request = request_factory.get('/')
    request.session = {}
    return request
```

- [ ] **Step 8: Update settings.py**

Add to `ahmia/settings.py` INSTALLED_APPS:

```python
INSTALLED_APPS = [
    'profiles.apps.ProfilesConfig',
    'ahmia',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]
```

- [ ] **Step 9: Write test for constants**

```python
# profiles/tests/test_models/test_constants.py
from profiles.constants import TrustLevel, ProfileStatus, EditStatus

def test_trust_level_ordering():
    assert TrustLevel.ANONYMOUS < TrustLevel.NEW
    assert TrustLevel.NEW < TrustLevel.TRUSTED
    assert TrustLevel.TRUSTED < TrustLevel.MODERATOR

def test_profile_status_choices():
    slugs = [c[0] for c in ProfileStatus.CHOICES]
    assert 'active' in slugs
    assert 'offline' in slugs
    assert 'banned' in slugs

def test_edit_status_choices():
    slugs = [c[0] for c in EditStatus.CHOICES]
    assert 'pending' in slugs
    assert 'approved' in slugs
    assert 'rejected' in slugs
```

- [ ] **Step 10: Run tests**

```bash
cd /home/this/dev/others/crawler/ahmia-site
python -m pytest profiles/tests/test_models/test_constants.py -v
```

- [ ] **Step 11: Commit**

```bash
git add profiles/ ahmia/settings.py
git commit -m "feat(profiles): scaffold app with base models and constants"
```

---

## Task 2: Category & Tag Models

**Files:**
- Create: `profiles/models/taxonomy.py`
- Modify: `profiles/models/__init__.py`
- Test: `profiles/tests/test_models/test_taxonomy.py`
- Test: `profiles/tests/factories.py`

**Interfaces:**
- Consumes: `BaseModel` from `profiles.models.base`
- Produces: `Category` model with `name`, `slug`, `description`, `icon`
- Produces: `Tag` model with `name`, `slug`, `is_approved`
- Produces: `CategoryFactory`, `TagFactory` for testing

- [ ] **Step 1: Write failing test for Category**

```python
# profiles/tests/test_models/test_taxonomy.py
import pytest
from django.db import IntegrityError

pytestmark = pytest.mark.django_db

class TestCategory:
    def test_category_creation(self):
        from profiles.models import Category
        cat = Category.objects.create(
            name='Marketplace',
            slug='marketplace',
            description='Buy and sell goods',
            icon='🛒'
        )
        assert cat.name == 'Marketplace'
        assert cat.slug == 'marketplace'
        assert str(cat) == 'Marketplace'

    def test_category_slug_unique(self):
        from profiles.models import Category
        Category.objects.create(name='Forum', slug='forum')
        with pytest.raises(IntegrityError):
            Category.objects.create(name='Forum 2', slug='forum')

class TestTag:
    def test_tag_creation(self):
        from profiles.models import Tag
        tag = Tag.objects.create(name='crypto', slug='crypto')
        assert tag.name == 'crypto'
        assert tag.is_approved is False
        assert str(tag) == 'crypto'

    def test_tag_approval(self):
        from profiles.models import Tag
        tag = Tag.objects.create(name='escrow', slug='escrow', is_approved=True)
        assert tag.is_approved is True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest profiles/tests/test_models/test_taxonomy.py -v
```
Expected: FAIL with "cannot import name 'Category'"

- [ ] **Step 3: Write taxonomy models**

```python
# profiles/models/taxonomy.py
from django.db import models
from django.utils.text import slugify

class Category(models.Model):
    """Fixed taxonomy for primary categorization."""
    name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=50, unique=True)
    description = models.TextField(blank=True, default='')
    icon = models.CharField(max_length=50, blank=True, default='')
    display_order = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Tag(models.Model):
    """Freeform tags for additional classification."""
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
```

- [ ] **Step 4: Update models __init__.py**

```python
# profiles/models/__init__.py
from .base import BaseModel
from .taxonomy import Category, Tag

__all__ = ['BaseModel', 'Category', 'Tag']
```

- [ ] **Step 5: Create factories.py**

```python
# profiles/tests/factories.py
import factory
from profiles.models import Category, Tag

class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f'Category {n}')
    slug = factory.Sequence(lambda n: f'category-{n}')
    description = factory.Faker('sentence')
    icon = '📁'

class TagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tag

    name = factory.Sequence(lambda n: f'tag-{n}')
    slug = factory.Sequence(lambda n: f'tag-{n}')
    is_approved = False
```

- [ ] **Step 6: Run tests**

```bash
python -m pytest profiles/tests/test_models/test_taxonomy.py -v
```

- [ ] **Step 7: Create migration**

```bash
python manage.py makemigrations profiles
```

- [ ] **Step 8: Commit**

```bash
git add profiles/
git commit -m "feat(profiles): add Category and Tag models"
```

---

## Task 3: OnionProfile & DomainHistory Models

**Files:**
- Create: `profiles/models/profile.py`
- Modify: `profiles/models/__init__.py`
- Test: `profiles/tests/test_models/test_profile.py`
- Update: `profiles/tests/factories.py`

**Interfaces:**
- Consumes: `BaseModel`, `Category` from `profiles.models`
- Produces: `OnionProfile` model with all fields from spec
- Produces: `DomainHistory` model for URL tracking
- Produces: `OnionProfileFactory`, `DomainHistoryFactory`

- [ ] **Step 1: Write failing test for OnionProfile**

```python
# profiles/tests/test_models/test_profile.py
import pytest
from django.utils import timezone
from datetime import timedelta

pytestmark = pytest.mark.django_db

class TestOnionProfile:
    def test_profile_creation(self):
        from profiles.models import OnionProfile, Category
        cat = Category.objects.create(name='Other', slug='other')
        profile = OnionProfile.objects.create(
            slug='test-site',
            current_domain='testsite1234567890abcdef1234567890abcdef1234567890abcdefgh.onion',
            name='Test Site',
            description='A test onion site',
            category=cat
        )
        assert profile.slug == 'test-site'
        assert profile.is_verified is False
        assert profile.status == 'active'
        assert str(profile) == 'Test Site'

    def test_profile_domain_unique(self):
        from profiles.models import OnionProfile, Category
        from django.db import IntegrityError
        cat = Category.objects.create(name='Other', slug='other')
        domain = 'unique12345678901234567890123456789012345678901234567890ab.onion'
        OnionProfile.objects.create(slug='site-1', current_domain=domain, name='Site 1', category=cat)
        with pytest.raises(IntegrityError):
            OnionProfile.objects.create(slug='site-2', current_domain=domain, name='Site 2', category=cat)

    def test_profile_verification_token_generation(self):
        from profiles.models import OnionProfile, Category
        cat = Category.objects.create(name='Other', slug='other')
        profile = OnionProfile.objects.create(
            slug='verify-test',
            current_domain='verifytest234567890abcdef1234567890abcdef1234567890abcd.onion',
            name='Verify Test',
            category=cat
        )
        token = profile.generate_verification_token()
        assert len(token) == 64
        assert profile.verification_token == token
        assert profile.verification_token_expires > timezone.now()


class TestDomainHistory:
    def test_domain_history_creation(self):
        from profiles.models import OnionProfile, DomainHistory, Category
        cat = Category.objects.create(name='Other', slug='other')
        profile = OnionProfile.objects.create(
            slug='history-test',
            current_domain='historytest34567890abcdef1234567890abcdef1234567890abc.onion',
            name='History Test',
            category=cat
        )
        history = DomainHistory.objects.create(
            profile=profile,
            domain='oldhistory234567890abcdef1234567890abcdef1234567890abcde.onion',
            was_active_from=timezone.now() - timedelta(days=365),
            was_active_to=timezone.now() - timedelta(days=30),
            migration_type='community'
        )
        assert history.profile == profile
        assert history.migration_type == 'community'
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest profiles/tests/test_models/test_profile.py -v
```

- [ ] **Step 3: Write profile models**

```python
# profiles/models/profile.py
import secrets
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from .base import BaseModel
from .taxonomy import Category, Tag
from ..constants import ProfileStatus, MigrationSource, VERIFICATION_TOKEN_EXPIRY_DAYS

User = get_user_model()


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
```

- [ ] **Step 4: Update models __init__.py**

```python
# profiles/models/__init__.py
from .base import BaseModel
from .taxonomy import Category, Tag
from .profile import OnionProfile, ProfileTag, DomainHistory

__all__ = [
    'BaseModel',
    'Category', 'Tag',
    'OnionProfile', 'ProfileTag', 'DomainHistory',
]
```

- [ ] **Step 5: Update factories.py**

```python
# profiles/tests/factories.py (add to existing)
from profiles.models import OnionProfile, DomainHistory

class OnionProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OnionProfile

    slug = factory.Sequence(lambda n: f'site-{n}')
    current_domain = factory.Sequence(
        lambda n: f'site{n:04d}test567890abcdef1234567890abcdef1234567890abcdef.onion'
    )
    name = factory.Sequence(lambda n: f'Test Site {n}')
    description = factory.Faker('paragraph')
    category = factory.SubFactory(CategoryFactory)
    status = 'active'

class DomainHistoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DomainHistory

    profile = factory.SubFactory(OnionProfileFactory)
    domain = factory.Sequence(
        lambda n: f'old{n:04d}site567890abcdef1234567890abcdef1234567890abcdef.onion'
    )
    was_active_from = factory.Faker('date_time_this_year', tzinfo=timezone.utc)
    was_active_to = factory.LazyAttribute(
        lambda o: o.was_active_from + timedelta(days=30)
    )
    migration_type = 'community'
```

- [ ] **Step 6: Run tests**

```bash
python -m pytest profiles/tests/test_models/test_profile.py -v
```

- [ ] **Step 7: Create migration**

```bash
python manage.py makemigrations profiles
```

- [ ] **Step 8: Commit**

```bash
git add profiles/
git commit -m "feat(profiles): add OnionProfile and DomainHistory models"
```

---

## Task 4: Contributor Model

**Files:**
- Create: `profiles/models/contributor.py`
- Modify: `profiles/models/__init__.py`
- Test: `profiles/tests/test_models/test_contributor.py`
- Update: `profiles/tests/factories.py`

**Interfaces:**
- Consumes: `TrustLevel`, `TRUST_LEVEL_THRESHOLD` from `constants`
- Produces: `Contributor` model with trust level logic
- Produces: `Contributor.get_or_create_for_request(request)` class method
- Produces: `Contributor.can_auto_approve` property
- Produces: `ContributorFactory`

- [ ] **Step 1: Write failing test**

```python
# profiles/tests/test_models/test_contributor.py
import pytest
from django.utils import timezone
from datetime import timedelta

pytestmark = pytest.mark.django_db

class TestContributor:
    def test_contributor_creation_anonymous(self):
        from profiles.models import Contributor
        from profiles.constants import TrustLevel
        contrib = Contributor.objects.create(
            session_key='abc123session',
            ip_hash='hashedipabc123'
        )
        assert contrib.trust_level == TrustLevel.ANONYMOUS
        assert contrib.user is None
        assert contrib.can_auto_approve is False

    def test_contributor_trust_upgrade(self):
        from profiles.models import Contributor
        from profiles.constants import TrustLevel, TRUST_LEVEL_THRESHOLD
        contrib = Contributor.objects.create(
            session_key='upgrade123',
            ip_hash='hashedip456',
            approved_edits=TRUST_LEVEL_THRESHOLD
        )
        contrib.recalculate_trust_level()
        assert contrib.trust_level == TrustLevel.TRUSTED
        assert contrib.can_auto_approve is True

    def test_contributor_cooldown(self):
        from profiles.models import Contributor
        contrib = Contributor.objects.create(
            session_key='cooldown123',
            ip_hash='hashedip789',
            cooldown_until=timezone.now() + timedelta(hours=12)
        )
        assert contrib.is_on_cooldown is True

    def test_contributor_not_on_cooldown(self):
        from profiles.models import Contributor
        contrib = Contributor.objects.create(
            session_key='nocooldown',
            ip_hash='hashedip000'
        )
        assert contrib.is_on_cooldown is False
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest profiles/tests/test_models/test_contributor.py -v
```

- [ ] **Step 3: Write contributor model**

```python
# profiles/models/contributor.py
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
        """Update trust level based on approved edits."""
        if self.trust_level == TrustLevel.MODERATOR:
            return  # Moderators are manually promoted
        
        if self.user and self.approved_edits >= TRUST_LEVEL_THRESHOLD:
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
```

- [ ] **Step 4: Update models __init__.py**

```python
# profiles/models/__init__.py
from .base import BaseModel
from .taxonomy import Category, Tag
from .profile import OnionProfile, ProfileTag, DomainHistory
from .contributor import Contributor

__all__ = [
    'BaseModel',
    'Category', 'Tag',
    'OnionProfile', 'ProfileTag', 'DomainHistory',
    'Contributor',
]
```

- [ ] **Step 5: Update factories.py**

```python
# profiles/tests/factories.py (add)
from profiles.models import Contributor
from profiles.constants import TrustLevel

class ContributorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Contributor

    session_key = factory.Sequence(lambda n: f'session-{n:08d}')
    ip_hash = factory.Sequence(lambda n: f'iphash-{n:08d}')
    trust_level = TrustLevel.ANONYMOUS
```

- [ ] **Step 6: Run tests**

```bash
python -m pytest profiles/tests/test_models/test_contributor.py -v
```

- [ ] **Step 7: Create migration**

```bash
python manage.py makemigrations profiles
```

- [ ] **Step 8: Commit**

```bash
git add profiles/
git commit -m "feat(profiles): add Contributor model with trust system"
```

---

## Task 5: ProfileEdit & MigrationReport Models

**Files:**
- Create: `profiles/models/moderation.py`
- Modify: `profiles/models/__init__.py`
- Test: `profiles/tests/test_models/test_moderation.py`
- Update: `profiles/tests/factories.py`

**Interfaces:**
- Consumes: `OnionProfile`, `Contributor` from `profiles.models`
- Consumes: `EditStatus`, `MigrationSource` from `constants`
- Produces: `ProfileEdit` model with `apply()` method
- Produces: `MigrationReport` model with `apply()` method
- Produces: `ProfileEditFactory`, `MigrationReportFactory`

- [ ] **Step 1: Write failing test**

```python
# profiles/tests/test_models/test_moderation.py
import pytest
from django.utils import timezone

pytestmark = pytest.mark.django_db

class TestProfileEdit:
    def test_edit_creation(self):
        from profiles.tests.factories import OnionProfileFactory, ContributorFactory
        from profiles.models import ProfileEdit
        from profiles.constants import EditStatus
        
        profile = OnionProfileFactory()
        contrib = ContributorFactory()
        
        edit = ProfileEdit.objects.create(
            profile=profile,
            field_name='description',
            old_value='Old description',
            new_value='New description',
            submitted_by=contrib
        )
        assert edit.status == EditStatus.PENDING
        assert edit.reviewed_by is None

    def test_edit_apply(self):
        from profiles.tests.factories import OnionProfileFactory, ContributorFactory
        from profiles.models import ProfileEdit
        from profiles.constants import EditStatus
        
        profile = OnionProfileFactory(description='Original')
        contrib = ContributorFactory()
        reviewer = ContributorFactory()
        
        edit = ProfileEdit.objects.create(
            profile=profile,
            field_name='description',
            old_value='Original',
            new_value='Updated description',
            submitted_by=contrib
        )
        edit.approve(reviewer)
        
        profile.refresh_from_db()
        assert profile.description == 'Updated description'
        assert edit.status == EditStatus.APPROVED
        assert edit.reviewed_by == reviewer


class TestMigrationReport:
    def test_migration_creation(self):
        from profiles.tests.factories import OnionProfileFactory, ContributorFactory
        from profiles.models import MigrationReport
        from profiles.constants import MigrationSource
        
        profile = OnionProfileFactory()
        contrib = ContributorFactory()
        
        report = MigrationReport.objects.create(
            profile=profile,
            old_domain=profile.current_domain,
            new_domain='newdomain567890abcdef1234567890abcdef1234567890abcdefgh.onion',
            source=MigrationSource.COMMUNITY,
            submitted_by=contrib
        )
        assert report.status == 'pending'
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest profiles/tests/test_models/test_moderation.py -v
```

- [ ] **Step 3: Write moderation models**

```python
# profiles/models/moderation.py
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
```

- [ ] **Step 4: Update models __init__.py**

```python
# profiles/models/__init__.py
from .base import BaseModel
from .taxonomy import Category, Tag
from .profile import OnionProfile, ProfileTag, DomainHistory
from .contributor import Contributor
from .moderation import ProfileEdit, MigrationReport

__all__ = [
    'BaseModel',
    'Category', 'Tag',
    'OnionProfile', 'ProfileTag', 'DomainHistory',
    'Contributor',
    'ProfileEdit', 'MigrationReport',
]
```

- [ ] **Step 5: Update factories.py**

```python
# profiles/tests/factories.py (add)
from profiles.models import ProfileEdit, MigrationReport
from profiles.constants import EditStatus, MigrationSource

class ProfileEditFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProfileEdit

    profile = factory.SubFactory(OnionProfileFactory)
    field_name = 'description'
    old_value = 'Old value'
    new_value = 'New value'
    submitted_by = factory.SubFactory(ContributorFactory)
    status = EditStatus.PENDING

class MigrationReportFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MigrationReport

    profile = factory.SubFactory(OnionProfileFactory)
    old_domain = factory.LazyAttribute(lambda o: o.profile.current_domain)
    new_domain = factory.Sequence(
        lambda n: f'newsite{n:04d}567890abcdef1234567890abcdef1234567890abcde.onion'
    )
    source = MigrationSource.COMMUNITY
    submitted_by = factory.SubFactory(ContributorFactory)
    status = EditStatus.PENDING
```

- [ ] **Step 6: Run tests**

```bash
python -m pytest profiles/tests/test_models/test_moderation.py -v
```

- [ ] **Step 7: Create migration**

```bash
python manage.py makemigrations profiles
```

- [ ] **Step 8: Commit**

```bash
git add profiles/
git commit -m "feat(profiles): add ProfileEdit and MigrationReport models"
```

---

## Task 6: Base Repository Pattern

**Files:**
- Create: `profiles/repositories/base.py`
- Create: `profiles/repositories/profile_repository.py`
- Test: `profiles/tests/test_repositories/test_profile_repository.py`

**Interfaces:**
- Produces: `BaseRepository[T]` abstract class with CRUD methods
- Produces: `ProfileRepository` with `get_by_slug()`, `get_by_domain()`, `search()`, `list_by_category()`

- [ ] **Step 1: Write failing test**

```python
# profiles/tests/test_repositories/test_profile_repository.py
import pytest

pytestmark = pytest.mark.django_db

class TestProfileRepository:
    def test_get_by_slug(self):
        from profiles.tests.factories import OnionProfileFactory
        from profiles.repositories import ProfileRepository
        
        profile = OnionProfileFactory(slug='test-repo-slug')
        repo = ProfileRepository()
        
        found = repo.get_by_slug('test-repo-slug')
        assert found.id == profile.id

    def test_get_by_slug_not_found(self):
        from profiles.repositories import ProfileRepository
        from profiles.exceptions import ProfileNotFoundError
        
        repo = ProfileRepository()
        with pytest.raises(ProfileNotFoundError):
            repo.get_by_slug('nonexistent')

    def test_get_by_domain(self):
        from profiles.tests.factories import OnionProfileFactory
        from profiles.repositories import ProfileRepository
        
        domain = 'repodomain567890abcdef1234567890abcdef1234567890abcdefgh.onion'
        profile = OnionProfileFactory(current_domain=domain)
        repo = ProfileRepository()
        
        found = repo.get_by_domain(domain)
        assert found.id == profile.id

    def test_list_by_category(self):
        from profiles.tests.factories import OnionProfileFactory, CategoryFactory
        from profiles.repositories import ProfileRepository
        
        cat = CategoryFactory(slug='test-cat')
        OnionProfileFactory(category=cat)
        OnionProfileFactory(category=cat)
        OnionProfileFactory()  # Different category
        
        repo = ProfileRepository()
        results = repo.list_by_category('test-cat')
        
        assert len(results) == 2
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest profiles/tests/test_repositories/test_profile_repository.py -v
```

- [ ] **Step 3: Write base repository**

```python
# profiles/repositories/base.py
from typing import TypeVar, Generic, Optional, List
from django.db.models import Model, QuerySet

T = TypeVar('T', bound=Model)


class BaseRepository(Generic[T]):
    """Abstract base repository with common CRUD operations."""
    
    model: type[T]
    
    def get_queryset(self) -> QuerySet[T]:
        """Return base queryset. Override for default filters."""
        return self.model.objects.all()

    def get_by_id(self, id) -> T:
        """Get by primary key or raise DoesNotExist."""
        return self.get_queryset().get(pk=id)

    def get_by_id_or_none(self, id) -> Optional[T]:
        """Get by primary key or return None."""
        try:
            return self.get_by_id(id)
        except self.model.DoesNotExist:
            return None

    def list_all(self) -> QuerySet[T]:
        """Return all records."""
        return self.get_queryset()

    def create(self, **kwargs) -> T:
        """Create and return new record."""
        return self.model.objects.create(**kwargs)

    def update(self, instance: T, **kwargs) -> T:
        """Update instance with kwargs."""
        for key, value in kwargs.items():
            setattr(instance, key, value)
        instance.save()
        return instance

    def delete(self, instance: T) -> None:
        """Delete instance."""
        instance.delete()

    def exists(self, **kwargs) -> bool:
        """Check if record exists."""
        return self.get_queryset().filter(**kwargs).exists()

    def count(self) -> int:
        """Count all records."""
        return self.get_queryset().count()
```

- [ ] **Step 4: Write profile repository**

```python
# profiles/repositories/profile_repository.py
from typing import Optional, List
from django.db.models import QuerySet, Q

from .base import BaseRepository
from ..models import OnionProfile, Category
from ..exceptions import ProfileNotFoundError
from ..constants import ProfileStatus


class ProfileRepository(BaseRepository[OnionProfile]):
    """Repository for OnionProfile operations."""
    
    model = OnionProfile

    def get_queryset(self) -> QuerySet[OnionProfile]:
        """Default queryset excludes banned profiles."""
        return super().get_queryset().exclude(status=ProfileStatus.BANNED)

    def get_by_slug(self, slug: str) -> OnionProfile:
        """Get profile by slug or raise ProfileNotFoundError."""
        try:
            return self.get_queryset().get(slug=slug)
        except OnionProfile.DoesNotExist:
            raise ProfileNotFoundError(f"Profile with slug '{slug}' not found")

    def get_by_slug_or_none(self, slug: str) -> Optional[OnionProfile]:
        """Get profile by slug or return None."""
        try:
            return self.get_by_slug(slug)
        except ProfileNotFoundError:
            return None

    def get_by_domain(self, domain: str) -> OnionProfile:
        """Get profile by current domain or raise ProfileNotFoundError."""
        try:
            return self.get_queryset().get(current_domain=domain)
        except OnionProfile.DoesNotExist:
            raise ProfileNotFoundError(f"Profile with domain '{domain}' not found")

    def get_by_domain_or_none(self, domain: str) -> Optional[OnionProfile]:
        """Get profile by domain or return None."""
        try:
            return self.get_by_domain(domain)
        except ProfileNotFoundError:
            return None

    def list_by_category(self, category_slug: str) -> QuerySet[OnionProfile]:
        """List profiles in a category."""
        return self.get_queryset().filter(category__slug=category_slug)

    def list_by_tag(self, tag_slug: str) -> QuerySet[OnionProfile]:
        """List profiles with a specific tag."""
        return self.get_queryset().filter(tags__slug=tag_slug)

    def list_verified(self) -> QuerySet[OnionProfile]:
        """List verified profiles."""
        return self.get_queryset().filter(is_verified=True)

    def list_active(self) -> QuerySet[OnionProfile]:
        """List active profiles."""
        return self.get_queryset().filter(status=ProfileStatus.ACTIVE)

    def search(self, query: str) -> QuerySet[OnionProfile]:
        """Search profiles by name or description."""
        return self.get_queryset().filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )

    def get_domain_to_slug_map(self, domains: List[str]) -> dict:
        """Get mapping of domain -> slug for multiple domains."""
        profiles = self.model.objects.filter(
            current_domain__in=domains
        ).values('current_domain', 'slug')
        return {p['current_domain']: p['slug'] for p in profiles}
```

- [ ] **Step 5: Update repositories __init__.py**

```python
# profiles/repositories/__init__.py
from .base import BaseRepository
from .profile_repository import ProfileRepository

__all__ = ['BaseRepository', 'ProfileRepository']
```

- [ ] **Step 6: Run tests**

```bash
python -m pytest profiles/tests/test_repositories/test_profile_repository.py -v
```

- [ ] **Step 7: Commit**

```bash
git add profiles/
git commit -m "feat(profiles): add repository pattern with ProfileRepository"
```

---

## Task 7: Moderation Repository

**Files:**
- Create: `profiles/repositories/moderation_repository.py`
- Modify: `profiles/repositories/__init__.py`
- Test: `profiles/tests/test_repositories/test_moderation_repository.py`

**Interfaces:**
- Consumes: `BaseRepository`, `ProfileEdit`, `MigrationReport`
- Produces: `ModerationRepository.get_pending_edits()`, `get_pending_migrations()`
- Produces: `ModerationRepository.get_edits_for_profile(profile_id)`

- [ ] **Step 1: Write failing test**

```python
# profiles/tests/test_repositories/test_moderation_repository.py
import pytest

pytestmark = pytest.mark.django_db

class TestModerationRepository:
    def test_get_pending_edits(self):
        from profiles.tests.factories import ProfileEditFactory
        from profiles.repositories import ModerationRepository
        from profiles.constants import EditStatus
        
        ProfileEditFactory(status=EditStatus.PENDING)
        ProfileEditFactory(status=EditStatus.PENDING)
        ProfileEditFactory(status=EditStatus.APPROVED)
        
        repo = ModerationRepository()
        pending = repo.get_pending_edits()
        
        assert pending.count() == 2

    def test_get_pending_migrations(self):
        from profiles.tests.factories import MigrationReportFactory
        from profiles.repositories import ModerationRepository
        from profiles.constants import EditStatus
        
        MigrationReportFactory(status=EditStatus.PENDING)
        MigrationReportFactory(status=EditStatus.REJECTED)
        
        repo = ModerationRepository()
        pending = repo.get_pending_migrations()
        
        assert pending.count() == 1

    def test_get_edits_for_profile(self):
        from profiles.tests.factories import ProfileEditFactory, OnionProfileFactory
        from profiles.repositories import ModerationRepository
        
        profile = OnionProfileFactory()
        ProfileEditFactory(profile=profile)
        ProfileEditFactory(profile=profile)
        ProfileEditFactory()  # Different profile
        
        repo = ModerationRepository()
        edits = repo.get_edits_for_profile(profile.id)
        
        assert edits.count() == 2
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest profiles/tests/test_repositories/test_moderation_repository.py -v
```

- [ ] **Step 3: Write moderation repository**

```python
# profiles/repositories/moderation_repository.py
from typing import Optional
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
```

- [ ] **Step 4: Update repositories __init__.py**

```python
# profiles/repositories/__init__.py
from .base import BaseRepository
from .profile_repository import ProfileRepository
from .moderation_repository import ModerationRepository

__all__ = ['BaseRepository', 'ProfileRepository', 'ModerationRepository']
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest profiles/tests/test_repositories/test_moderation_repository.py -v
```

- [ ] **Step 6: Commit**

```bash
git add profiles/
git commit -m "feat(profiles): add ModerationRepository"
```

---

## Task 8: Service Registry (Extensibility Pattern)

**Files:**
- Create: `profiles/services/registry.py`
- Test: `profiles/tests/test_services/test_registry.py`

**Interfaces:**
- Produces: `ServiceRegistry` singleton for registering/retrieving services
- Produces: `@register_service(name)` decorator
- Produces: `get_service(name)` function

- [ ] **Step 1: Write failing test**

```python
# profiles/tests/test_services/test_registry.py
import pytest

class TestServiceRegistry:
    def test_register_and_get_service(self):
        from profiles.services.registry import ServiceRegistry, register_service, get_service
        
        registry = ServiceRegistry()
        
        @register_service('test_service', registry=registry)
        class TestService:
            def do_something(self):
                return 'done'
        
        service = get_service('test_service', registry=registry)
        assert service.do_something() == 'done'

    def test_get_unregistered_service_raises(self):
        from profiles.services.registry import ServiceRegistry, get_service
        
        registry = ServiceRegistry()
        with pytest.raises(KeyError):
            get_service('nonexistent', registry=registry)

    def test_override_service(self):
        from profiles.services.registry import ServiceRegistry, register_service, get_service
        
        registry = ServiceRegistry()
        
        @register_service('overridable', registry=registry)
        class OriginalService:
            def value(self):
                return 'original'
        
        @register_service('overridable', registry=registry)
        class OverrideService:
            def value(self):
                return 'override'
        
        service = get_service('overridable', registry=registry)
        assert service.value() == 'override'
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest profiles/tests/test_services/test_registry.py -v
```

- [ ] **Step 3: Write service registry**

```python
# profiles/services/registry.py
from typing import Any, Callable, Dict, Optional, Type
from functools import wraps

class ServiceRegistry:
    """
    Registry for pluggable services.
    
    Allows overriding default implementations for extensibility.
    Example: Replace ElasticsearchService with MockElasticsearchService for testing.
    """
    
    _instances: Dict[str, Any] = {}
    _factories: Dict[str, Callable[[], Any]] = {}

    def __init__(self):
        self._instances = {}
        self._factories = {}

    def register(self, name: str, factory: Callable[[], Any]) -> None:
        """Register a service factory."""
        self._factories[name] = factory
        # Clear cached instance if exists
        self._instances.pop(name, None)

    def get(self, name: str) -> Any:
        """Get service instance (lazy singleton per name)."""
        if name not in self._instances:
            if name not in self._factories:
                raise KeyError(f"Service '{name}' not registered")
            self._instances[name] = self._factories[name]()
        return self._instances[name]

    def clear(self) -> None:
        """Clear all registered services."""
        self._instances.clear()
        self._factories.clear()

    def reset_instance(self, name: str) -> None:
        """Reset cached instance, forcing re-creation on next get."""
        self._instances.pop(name, None)


# Global default registry
_default_registry = ServiceRegistry()


def register_service(
    name: str,
    registry: Optional[ServiceRegistry] = None
) -> Callable[[Type], Type]:
    """
    Decorator to register a class as a service.
    
    Usage:
        @register_service('profile_service')
        class ProfileService:
            ...
    """
    reg = registry or _default_registry
    
    def decorator(cls: Type) -> Type:
        reg.register(name, cls)
        return cls
    
    return decorator


def get_service(name: str, registry: Optional[ServiceRegistry] = None) -> Any:
    """Get a service by name from the registry."""
    reg = registry or _default_registry
    return reg.get(name)


def get_default_registry() -> ServiceRegistry:
    """Get the default global registry."""
    return _default_registry
```

- [ ] **Step 4: Update services __init__.py**

```python
# profiles/services/__init__.py
from .registry import ServiceRegistry, register_service, get_service, get_default_registry

__all__ = ['ServiceRegistry', 'register_service', 'get_service', 'get_default_registry']
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest profiles/tests/test_services/test_registry.py -v
```

- [ ] **Step 6: Commit**

```bash
git add profiles/
git commit -m "feat(profiles): add pluggable service registry pattern"
```

---

## Task 9: Slug Service

**Files:**
- Create: `profiles/services/slug_service.py`
- Modify: `profiles/services/__init__.py`
- Test: `profiles/tests/test_services/test_slug_service.py`

**Interfaces:**
- Produces: `SlugService.generate_slug(name: str, domain: str) -> str`
- Produces: `SlugService.ensure_unique(slug: str) -> str`

- [ ] **Step 1: Write failing test**

```python
# profiles/tests/test_services/test_slug_service.py
import pytest

pytestmark = pytest.mark.django_db

class TestSlugService:
    def test_generate_from_name(self):
        from profiles.services.slug_service import SlugService
        
        service = SlugService()
        slug = service.generate_slug(name='Dread Forum', domain='abc123.onion')
        
        assert slug == 'dread-forum'

    def test_generate_from_domain_when_no_name(self):
        from profiles.services.slug_service import SlugService
        
        service = SlugService()
        domain = 'dreadytofatroptsdj6io7l3xptbet6onoyno2yv7jicoxknyazubrad.onion'
        slug = service.generate_slug(name='', domain=domain)
        
        assert slug == 'dreadytofatr'  # First 12 chars

    def test_ensure_unique_no_collision(self):
        from profiles.services.slug_service import SlugService
        
        service = SlugService()
        slug = service.ensure_unique('unique-slug')
        
        assert slug == 'unique-slug'

    def test_ensure_unique_with_collision(self):
        from profiles.tests.factories import OnionProfileFactory
        from profiles.services.slug_service import SlugService
        
        OnionProfileFactory(slug='taken-slug')
        
        service = SlugService()
        slug = service.ensure_unique('taken-slug')
        
        assert slug == 'taken-slug-2'

    def test_ensure_unique_multiple_collisions(self):
        from profiles.tests.factories import OnionProfileFactory
        from profiles.services.slug_service import SlugService
        
        OnionProfileFactory(slug='popular')
        OnionProfileFactory(slug='popular-2')
        OnionProfileFactory(slug='popular-3')
        
        service = SlugService()
        slug = service.ensure_unique('popular')
        
        assert slug == 'popular-4'
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest profiles/tests/test_services/test_slug_service.py -v
```

- [ ] **Step 3: Write slug service**

```python
# profiles/services/slug_service.py
import re
from django.utils.text import slugify

from .registry import register_service
from ..models import OnionProfile


@register_service('slug_service')
class SlugService:
    """Service for generating unique profile slugs."""

    def generate_slug(self, name: str, domain: str) -> str:
        """
        Generate a slug from name or domain.
        
        Priority:
        1. Slugified name if provided
        2. First 12 chars of domain (without .onion)
        """
        if name and name.strip():
            base_slug = slugify(name.strip())
            if base_slug:
                return self.ensure_unique(base_slug[:100])
        
        # Extract domain name without .onion
        domain_name = domain.replace('.onion', '')
        base_slug = domain_name[:12].lower()
        # Ensure only valid slug characters
        base_slug = re.sub(r'[^a-z0-9-]', '', base_slug)
        
        return self.ensure_unique(base_slug)

    def ensure_unique(self, base_slug: str) -> str:
        """
        Ensure slug is unique by appending suffix if needed.
        
        Examples:
            'my-site' -> 'my-site' (if unique)
            'my-site' -> 'my-site-2' (if 'my-site' exists)
            'my-site' -> 'my-site-3' (if 'my-site' and 'my-site-2' exist)
        """
        if not OnionProfile.objects.filter(slug=base_slug).exists():
            return base_slug
        
        counter = 2
        while True:
            candidate = f"{base_slug}-{counter}"
            if not OnionProfile.objects.filter(slug=candidate).exists():
                return candidate
            counter += 1
            if counter > 1000:  # Safety limit
                raise ValueError(f"Could not generate unique slug for '{base_slug}'")
```

- [ ] **Step 4: Update services __init__.py**

```python
# profiles/services/__init__.py
from .registry import ServiceRegistry, register_service, get_service, get_default_registry
from .slug_service import SlugService

__all__ = [
    'ServiceRegistry', 'register_service', 'get_service', 'get_default_registry',
    'SlugService',
]
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest profiles/tests/test_services/test_slug_service.py -v
```

- [ ] **Step 6: Commit**

```bash
git add profiles/
git commit -m "feat(profiles): add SlugService for unique slug generation"
```

---

## Task 10: Elasticsearch Service

**Files:**
- Create: `profiles/services/elasticsearch_service.py`
- Modify: `profiles/services/__init__.py`
- Test: `profiles/tests/test_services/test_elasticsearch_service.py`

**Interfaces:**
- Consumes: ES client from `ahmia.views`
- Produces: `ElasticsearchService.get_domain_stats(domain: str) -> dict`
- Produces: `ElasticsearchService.get_all_domains() -> List[dict]`
- Produces: `ElasticsearchService.get_top_pages(domain: str, limit: int) -> List[dict]`

- [ ] **Step 1: Write failing test with mock**

```python
# profiles/tests/test_services/test_elasticsearch_service.py
import pytest
from unittest.mock import MagicMock, patch

class TestElasticsearchService:
    def test_get_domain_stats(self):
        from profiles.services.elasticsearch_service import ElasticsearchService
        
        mock_client = MagicMock()
        mock_client.search.return_value = {
            'aggregations': {
                'page_count': {'value': 42},
                'last_seen': {'value_as_string': '2026-07-31T10:00:00'}
            }
        }
        
        service = ElasticsearchService(es_client=mock_client)
        stats = service.get_domain_stats('example.onion')
        
        assert stats['page_count'] == 42
        assert stats['last_seen'] is not None

    def test_get_all_domains(self):
        from profiles.services.elasticsearch_service import ElasticsearchService
        
        mock_client = MagicMock()
        mock_client.search.return_value = {
            'aggregations': {
                'domains': {
                    'buckets': [
                        {'key': 'site1.onion', 'doc_count': 100},
                        {'key': 'site2.onion', 'doc_count': 50},
                    ]
                }
            }
        }
        
        service = ElasticsearchService(es_client=mock_client)
        domains = service.get_all_domains()
        
        assert len(domains) == 2
        assert domains[0]['domain'] == 'site1.onion'
        assert domains[0]['page_count'] == 100

    def test_get_top_pages(self):
        from profiles.services.elasticsearch_service import ElasticsearchService
        
        mock_client = MagicMock()
        mock_client.search.return_value = {
            'hits': {
                'hits': [
                    {'_source': {'url': 'http://x.onion/', 'title': 'Home'}},
                    {'_source': {'url': 'http://x.onion/about', 'title': 'About'}},
                ]
            }
        }
        
        service = ElasticsearchService(es_client=mock_client)
        pages = service.get_top_pages('x.onion', limit=5)
        
        assert len(pages) == 2
        assert pages[0]['title'] == 'Home'
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest profiles/tests/test_services/test_elasticsearch_service.py -v
```

- [ ] **Step 3: Write elasticsearch service**

```python
# profiles/services/elasticsearch_service.py
from typing import List, Dict, Optional, Any
from datetime import datetime
from django.conf import settings

from .registry import register_service


@register_service('elasticsearch_service')
class ElasticsearchService:
    """Service for querying Elasticsearch crawl data."""

    def __init__(self, es_client=None):
        self._client = es_client

    @property
    def client(self):
        """Lazy-load ES client."""
        if self._client is None:
            from elasticsearch import Elasticsearch
            self._client = Elasticsearch(
                hosts=[settings.ELASTICSEARCH_SERVER],
                http_auth=(settings.ELASTICSEARCH_USERNAME, settings.ELASTICSEARCH_PASSWORD),
                ca_certs=settings.ELASTICSEARCH_CA_CERTS,
                verify_certs=settings.VERIFY_CERT,
                ssl_show_warn=settings.VERIFY_CERT,
                timeout=settings.ELASTICSEARCH_TIMEOUT
            )
        return self._client

    @property
    def index(self) -> str:
        return settings.ELASTICSEARCH_INDEX

    def get_domain_stats(self, domain: str) -> Dict[str, Any]:
        """Get page count and last seen for a domain."""
        response = self.client.search(
            index=self.index,
            body={
                'size': 0,
                'query': {
                    'bool': {
                        'must': [{'term': {'domain': domain}}],
                        'must_not': [{'term': {'is_banned': True}}]
                    }
                },
                'aggs': {
                    'page_count': {'value_count': {'field': 'url'}},
                    'last_seen': {'max': {'field': 'updated_on'}}
                }
            }
        )
        
        aggs = response.get('aggregations', {})
        page_count = int(aggs.get('page_count', {}).get('value', 0))
        last_seen_str = aggs.get('last_seen', {}).get('value_as_string')
        last_seen = None
        if last_seen_str:
            try:
                last_seen = datetime.fromisoformat(last_seen_str.replace('Z', '+00:00'))
            except ValueError:
                pass
        
        return {
            'page_count': page_count,
            'last_seen': last_seen
        }

    def get_all_domains(self, exclude_banned: bool = True) -> List[Dict[str, Any]]:
        """Get all unique domains with page counts."""
        must_not = [{'term': {'is_banned': True}}] if exclude_banned else []
        
        response = self.client.search(
            index=self.index,
            body={
                'size': 0,
                'query': {'bool': {'must_not': must_not}} if must_not else {'match_all': {}},
                'aggs': {
                    'domains': {
                        'terms': {
                            'field': 'domain',
                            'size': 300000
                        }
                    }
                }
            }
        )
        
        buckets = response.get('aggregations', {}).get('domains', {}).get('buckets', [])
        return [
            {'domain': b['key'], 'page_count': b['doc_count']}
            for b in buckets
        ]

    def get_top_pages(self, domain: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top pages for a domain (by relevance/recency)."""
        response = self.client.search(
            index=self.index,
            body={
                'size': limit,
                'query': {
                    'bool': {
                        'must': [{'term': {'domain': domain}}],
                        'must_not': [{'term': {'is_banned': True}}]
                    }
                },
                'sort': [{'updated_on': 'desc'}],
                '_source': ['url', 'title', 'meta', 'updated_on']
            }
        )
        
        hits = response.get('hits', {}).get('hits', [])
        return [hit['_source'] for hit in hits]

    def get_domain_metadata(self, domain: str) -> Dict[str, Any]:
        """Extract most common title and description for a domain."""
        response = self.client.search(
            index=self.index,
            body={
                'size': 0,
                'query': {
                    'bool': {
                        'must': [{'term': {'domain': domain}}],
                        'must_not': [{'term': {'is_banned': True}}]
                    }
                },
                'aggs': {
                    'titles': {
                        'terms': {'field': 'title.keyword', 'size': 5}
                    },
                    'descriptions': {
                        'terms': {'field': 'meta.keyword', 'size': 5}
                    }
                }
            }
        )
        
        aggs = response.get('aggregations', {})
        titles = aggs.get('titles', {}).get('buckets', [])
        descriptions = aggs.get('descriptions', {}).get('buckets', [])
        
        # Filter out generic titles
        generic_titles = {'home', 'index', 'welcome', 'untitled', ''}
        best_title = ''
        for t in titles:
            if t['key'].lower().strip() not in generic_titles:
                best_title = t['key']
                break
        
        best_description = descriptions[0]['key'] if descriptions else ''
        
        return {
            'title': best_title,
            'description': best_description[:500] if best_description else ''
        }
```

- [ ] **Step 4: Update services __init__.py**

```python
# profiles/services/__init__.py
from .registry import ServiceRegistry, register_service, get_service, get_default_registry
from .slug_service import SlugService
from .elasticsearch_service import ElasticsearchService

__all__ = [
    'ServiceRegistry', 'register_service', 'get_service', 'get_default_registry',
    'SlugService', 'ElasticsearchService',
]
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest profiles/tests/test_services/test_elasticsearch_service.py -v
```

- [ ] **Step 6: Commit**

```bash
git add profiles/
git commit -m "feat(profiles): add ElasticsearchService for crawl data queries"
```

---

## Remaining Tasks (Summary)

Due to length, the following tasks are outlined. Each follows the same TDD pattern:

### Task 11: Profile Service
- `ProfileService.create_profile()`, `update_profile()`, `get_profile_with_stats()`
- Coordinates repository + ES service

### Task 12: Verification Service
- `VerificationService.start_verification()`, `check_verification()`, `revoke_verification()`
- Tor fetch for `.well-known/ahmia-verify.txt`

### Task 13: Moderation Service
- `ModerationService.submit_edit()`, `approve_edit()`, `reject_edit()`
- Rate limiting, trust checks

### Task 14: Trust Service
- `TrustService.get_contributor()`, `check_can_edit()`, `check_can_review()`

### Task 15: Sync Service
- `SyncService.sync_all_profiles()`, `update_stats()`
- For management commands

### Task 16: Forms
- `ProfileEditForm`, `MigrationReportForm`, `ClaimForm`

### Task 17: View Mixins
- `ContributorMixin`, `TrustRequiredMixin`, `RateLimitMixin`

### Task 18: Profile Views
- `ProfileListView`, `ProfileDetailView`, `ProfileEditView`, `ProfileClaimView`

### Task 19: Directory Views
- `CategoryListView`, `TagListView`

### Task 20: Moderation Views
- `ModerationQueueView`, `EditReviewView`

### Task 21: URL Configuration
- Wire all views in `profiles/urls.py`
- Include in main `ahmia/urls.py`

### Task 22: Templates (Base + List)
- `base_profiles.html`, `profile_list.html`, `_profile_card.html`

### Task 23: Templates (Detail + Edit)
- `profile_detail.html`, `profile_edit.html`, `_stats_box.html`

### Task 24: Templates (Moderation)
- `moderation_queue.html`, `edit_review.html`, `_edit_diff.html`

### Task 25: Management Command - sync_profiles
- Auto-generate profiles from ES

### Task 26: Management Command - update_stats
- Refresh cached stats

### Task 27: Management Command - check_verifications
- Verify `.well-known` files

### Task 28: Management Command - seed_categories
- Initial category data

### Task 29: Admin Configuration
- Register models in `admin.py`

### Task 30: Search Results Integration
- Modify `ahmia/views.py` and `tor_results.html`

### Task 31: Sitemap Generation
- SEO sitemap for profiles

### Task 32: Final Integration Testing
- End-to-end tests

---

**Plan complete and saved to `docs/superpowers/plans/2026-08-01-onion-profiles.md`.**

**Two execution options:**

1. **Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

2. **Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**