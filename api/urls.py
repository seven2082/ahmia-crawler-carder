from django.urls import path
from .views import ProfileListView, ProfileDetailView, ProfileByDomainView, StatsView

app_name = 'api'

urlpatterns = [
    path('profiles/', ProfileListView.as_view(), name='profile_list'),
    path('profiles/<slug:slug>/', ProfileDetailView.as_view(), name='profile_detail'),
    path('profiles/by-domain/<str:domain>/', ProfileByDomainView.as_view(), name='profile_by_domain'),
    path('stats/', StatsView.as_view(), name='stats'),
]
