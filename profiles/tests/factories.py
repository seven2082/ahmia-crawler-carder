from datetime import timedelta, timezone

import factory

from profiles.models import (
    Category, Tag, OnionProfile, DomainHistory, Contributor,
    ProfileEdit, MigrationReport,
)
from profiles.constants import TrustLevel, EditStatus, MigrationSource

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

class ContributorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Contributor

    session_key = factory.Sequence(lambda n: f'session-{n:08d}')
    ip_hash = factory.Sequence(lambda n: f'iphash-{n:08d}')
    trust_level = TrustLevel.ANONYMOUS

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
