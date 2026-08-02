import pytest
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory

from profiles.admin import (
    CategoryAdmin, OnionProfileAdmin, ContributorAdmin,
    ProfileEditAdmin, MigrationReportAdmin
)
from profiles.models import Category, OnionProfile, Contributor, ProfileEdit, MigrationReport

pytestmark = pytest.mark.django_db


class TestAdminRegistration:
    def test_category_admin_registered(self):
        site = AdminSite()
        admin = CategoryAdmin(Category, site)
        assert admin is not None

    def test_profile_admin_registered(self):
        site = AdminSite()
        admin = OnionProfileAdmin(OnionProfile, site)
        assert admin is not None

    def test_contributor_admin_registered(self):
        site = AdminSite()
        admin = ContributorAdmin(Contributor, site)
        assert admin is not None

    def test_profile_edit_admin_no_add(self):
        site = AdminSite()
        admin = ProfileEditAdmin(ProfileEdit, site)
        factory = RequestFactory()
        request = factory.get('/')
        assert admin.has_add_permission(request) is False

    def test_migration_report_admin_no_add(self):
        site = AdminSite()
        admin = MigrationReportAdmin(MigrationReport, site)
        factory = RequestFactory()
        request = factory.get('/')
        assert admin.has_add_permission(request) is False
