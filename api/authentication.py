from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings


class APIKeyUser:
    """Sentinel user object for API key authentication."""
    is_authenticated = True


class APIKeyAuthentication(BaseAuthentication):
    """
    API key authentication via X-API-Key header.
    Returns (APIKeyUser, None) on success for IsAuthenticated compatibility.
    """

    def authenticate(self, request):
        api_key = request.headers.get('X-API-Key')

        if not api_key:
            return None

        if api_key != settings.AHMIA_API_KEY:
            raise AuthenticationFailed('Invalid API key')

        return (APIKeyUser(), None)
