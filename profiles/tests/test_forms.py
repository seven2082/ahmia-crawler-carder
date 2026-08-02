import pytest

pytestmark = pytest.mark.django_db


class TestProfileEditForm:
    def test_valid_form(self):
        from profiles.forms import ProfileEditForm
        from profiles.models import Category

        Category.objects.create(name='Forum', slug='forum')

        form = ProfileEditForm(data={
            'name': 'Updated Name',
            'description': 'Updated description'
        })

        assert form.is_valid()

    def test_description_truncated(self):
        from profiles.forms import ProfileEditForm

        form = ProfileEditForm(data={
            'description': 'x' * 600
        })

        assert form.is_valid()
        assert len(form.cleaned_data['description']) == 500


class TestMigrationReportForm:
    def test_valid_form(self):
        from profiles.forms import MigrationReportForm

        form = MigrationReportForm(data={
            'old_domain': 'oldsite567890abcdef1234567890abcdef1234567890abcdefgh.onion',
            'new_url': 'http://juhanurmihxlp77nkq76byazcldy2hlmovfu2epvl5ankdibsot4csyd.onion/',
        })

        assert form.is_valid()

    def test_extracts_domain_from_url(self):
        from profiles.forms import MigrationReportForm

        form = MigrationReportForm(data={
            'old_domain': 'old.onion',
            'new_url': 'http://juhanurmihxlp77nkq76byazcldy2hlmovfu2epvl5ankdibsot4csyd.onion/path',
        })

        assert form.is_valid()
        assert form.cleaned_data['new_url'] == 'juhanurmihxlp77nkq76byazcldy2hlmovfu2epvl5ankdibsot4csyd.onion'


class TestClaimForm:
    def test_requires_confirmation(self):
        from profiles.forms import ClaimForm

        form = ClaimForm(data={})
        assert not form.is_valid()

        form = ClaimForm(data={'confirm': True})
        assert form.is_valid()
