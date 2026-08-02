"""
Root URLconf used only by profile view tests (via @pytest.mark.urls).

Mounts the test-only `profiles.tests.test_views.urls` under `/site/`
so `Client.get('/site/...')` and `reverse('profiles:...')` work in
`test_profile_views.py` ahead of Task 21's real URL wiring.
"""
from django.http import HttpResponse
from django.urls import include, path


def _home(request):
    """Stand-in for the real `home` URL (defined in ahmia/urls.py) so
    TrustRequiredMixin's `redirect('home')` has somewhere to resolve to."""
    return HttpResponse('home')


urlpatterns = [
    path('', _home, name='home'),
    path('site/', include('profiles.tests.test_views.urls')),
]
