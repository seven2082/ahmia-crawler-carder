import pytest
from django.utils import timezone
from datetime import timedelta

pytestmark = pytest.mark.django_db


class TestModerationService:
    def test_submit_edit(self):
        from profiles.tests.factories import OnionProfileFactory, ContributorFactory
        from profiles.services.moderation_service import ModerationService
        from profiles.constants import EditStatus

        profile = OnionProfileFactory(description='Old description')
        contributor = ContributorFactory()

        service = ModerationService()
        edit = service.submit_edit(
            profile=profile,
            field_name='description',
            new_value='New description',
            contributor=contributor
        )

        assert edit.profile == profile
        assert edit.field_name == 'description'
        assert edit.old_value == 'Old description'
        assert edit.new_value == 'New description'
        assert edit.status == EditStatus.PENDING

    def test_submit_edit_auto_approves_for_trusted(self):
        from profiles.tests.factories import OnionProfileFactory, ContributorFactory
        from profiles.services.moderation_service import ModerationService
        from profiles.constants import EditStatus, TrustLevel

        profile = OnionProfileFactory(description='Old')
        contributor = ContributorFactory(trust_level=TrustLevel.TRUSTED)

        service = ModerationService()
        edit = service.submit_edit(
            profile=profile,
            field_name='description',
            new_value='New',
            contributor=contributor
        )

        assert edit.status == EditStatus.APPROVED

    def test_submit_edit_banned_contributor_raises(self):
        from profiles.tests.factories import OnionProfileFactory, ContributorFactory
        from profiles.services.moderation_service import ModerationService
        from profiles.exceptions import ContributorBannedError

        profile = OnionProfileFactory()
        contributor = ContributorFactory(is_banned=True)

        service = ModerationService()
        with pytest.raises(ContributorBannedError):
            service.submit_edit(profile, 'description', 'New', contributor)

    def test_submit_edit_on_cooldown_raises(self):
        from profiles.tests.factories import OnionProfileFactory, ContributorFactory
        from profiles.services.moderation_service import ModerationService
        from profiles.exceptions import RateLimitExceededError

        profile = OnionProfileFactory()
        contributor = ContributorFactory(cooldown_until=timezone.now() + timedelta(hours=1))

        service = ModerationService()
        with pytest.raises(RateLimitExceededError):
            service.submit_edit(profile, 'description', 'New', contributor)

    def test_submit_edit_rate_limit_exceeded_raises(self):
        from profiles.tests.factories import (
            OnionProfileFactory, ContributorFactory, ProfileEditFactory
        )
        from profiles.services.moderation_service import ModerationService
        from profiles.exceptions import RateLimitExceededError
        from profiles.constants import RATE_LIMIT_EDITS_PER_HOUR

        profile = OnionProfileFactory()
        contributor = ContributorFactory()
        for _ in range(RATE_LIMIT_EDITS_PER_HOUR):
            ProfileEditFactory(submitted_by=contributor)

        service = ModerationService()
        with pytest.raises(RateLimitExceededError):
            service.submit_edit(profile, 'description', 'New', contributor)

    def test_approve_edit(self):
        from profiles.tests.factories import ProfileEditFactory, ContributorFactory
        from profiles.services.moderation_service import ModerationService
        from profiles.constants import EditStatus

        edit = ProfileEditFactory(field_name='description', new_value='Updated description')
        reviewer = ContributorFactory()

        service = ModerationService()
        service.approve_edit(edit, reviewer)

        edit.refresh_from_db()
        assert edit.status == EditStatus.APPROVED
        assert edit.reviewed_by == reviewer

        edit.profile.refresh_from_db()
        assert edit.profile.description == 'Updated description'

    def test_reject_edit(self):
        from profiles.tests.factories import ProfileEditFactory, ContributorFactory
        from profiles.services.moderation_service import ModerationService
        from profiles.constants import EditStatus

        edit = ProfileEditFactory()
        reviewer = ContributorFactory()

        service = ModerationService()
        service.reject_edit(edit, reviewer, notes='Not accurate')

        edit.refresh_from_db()
        assert edit.status == EditStatus.REJECTED
        assert edit.reviewed_by == reviewer
        assert edit.review_notes == 'Not accurate'

    def test_submit_migration(self):
        from profiles.tests.factories import OnionProfileFactory, ContributorFactory
        from profiles.services.moderation_service import ModerationService

        profile = OnionProfileFactory()
        contributor = ContributorFactory()

        service = ModerationService()
        report = service.submit_migration(
            old_domain=profile.current_domain,
            new_domain='newdomain567890abcdef1234567890abcdef1234567890abcdefgh.onion',
            contributor=contributor,
            evidence_url='http://example.onion/moved'
        )

        assert report.old_domain == profile.current_domain
        assert report.profile == profile

    def test_submit_migration_no_matching_profile(self):
        from profiles.tests.factories import ContributorFactory
        from profiles.services.moderation_service import ModerationService

        contributor = ContributorFactory()

        service = ModerationService()
        report = service.submit_migration(
            old_domain='unknown567890abcdef1234567890abcdef1234567890abcdefghij.onion',
            new_domain='newdomain567890abcdef1234567890abcdef1234567890abcdefgh.onion',
            contributor=contributor
        )

        assert report.profile is None

    def test_submit_migration_banned_contributor_raises(self):
        from profiles.tests.factories import ContributorFactory
        from profiles.services.moderation_service import ModerationService
        from profiles.exceptions import ContributorBannedError

        contributor = ContributorFactory(is_banned=True)

        service = ModerationService()
        with pytest.raises(ContributorBannedError):
            service.submit_migration(
                old_domain='old567890abcdef1234567890abcdef1234567890abcdefghijkl.onion',
                new_domain='new567890abcdef1234567890abcdef1234567890abcdefghijkl.onion',
                contributor=contributor
            )
