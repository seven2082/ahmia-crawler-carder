"""
Minimal URL wiring used only by profile view tests.

Task 21 owns the real `profiles/urls.py` and its inclusion into
`ahmia/urls.py`. Until that lands, these tests need `/site/...` paths
and the `profiles:` namespace (used by redirects in the views) to
resolve, so we wire just enough here.
"""
from django.urls import path

from profiles.views.profile_views import (
    ProfileListView,
    ProfileDetailView,
    ProfileEditView,
    ProfileClaimView,
    ProfileHistoryView,
)
from profiles.views.directory_views import (
    CategoryListView,
    CategoryDetailView,
    TagListView,
    TagDetailView,
)
from profiles.views.moderation_views import (
    ModerationQueueView,
    EditReviewView,
    MigrationReviewView,
)

app_name = 'profiles'

urlpatterns = [
    path('categories/', CategoryListView.as_view(), name='category_list'),
    path('category/<slug:slug>/', CategoryDetailView.as_view(), name='category_detail'),
    path('tags/', TagListView.as_view(), name='tag_list'),
    path('tag/<slug:slug>/', TagDetailView.as_view(), name='tag_detail'),
    path('moderate/', ModerationQueueView.as_view(), name='moderation_queue'),
    path('moderate/edit/<int:edit_id>/', EditReviewView.as_view(), name='edit_review'),
    path(
        'moderate/migration/<int:migration_id>/',
        MigrationReviewView.as_view(),
        name='migration_review',
    ),
    path('', ProfileListView.as_view(), name='list'),
    path('<slug:slug>/', ProfileDetailView.as_view(), name='detail'),
    path('<slug:slug>/edit/', ProfileEditView.as_view(), name='edit'),
    path('<slug:slug>/claim/', ProfileClaimView.as_view(), name='claim'),
    path('<slug:slug>/history/', ProfileHistoryView.as_view(), name='history'),
]
