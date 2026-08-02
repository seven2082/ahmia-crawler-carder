from django.urls import path

from .views import (
    ProfileListView, ProfileDetailView, ProfileEditView,
    ProfileClaimView, ProfileHistoryView,
    CategoryListView, CategoryDetailView,
    TagListView, TagDetailView,
    ModerationQueueView, EditReviewView, MigrationReviewView,
)

app_name = 'profiles'

urlpatterns = [
    # Directory
    path('', ProfileListView.as_view(), name='list'),
    path('categories/', CategoryListView.as_view(), name='category_list'),
    path('category/<slug:slug>/', CategoryDetailView.as_view(), name='category_detail'),
    path('tags/', TagListView.as_view(), name='tag_list'),
    path('tag/<slug:slug>/', TagDetailView.as_view(), name='tag_detail'),

    # Moderation
    path('moderate/', ModerationQueueView.as_view(), name='moderation_queue'),
    path('moderate/edit/<int:edit_id>/', EditReviewView.as_view(), name='edit_review'),
    path('moderate/migration/<int:migration_id>/', MigrationReviewView.as_view(), name='migration_review'),

    # Profile pages (must be last - slug catch-all)
    path('<slug:slug>/', ProfileDetailView.as_view(), name='detail'),
    path('<slug:slug>/edit/', ProfileEditView.as_view(), name='edit'),
    path('<slug:slug>/claim/', ProfileClaimView.as_view(), name='claim'),
    path('<slug:slug>/history/', ProfileHistoryView.as_view(), name='history'),
]
