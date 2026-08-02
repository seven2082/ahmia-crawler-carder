from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory
from rest_framework.exceptions import AuthenticationFailed

from api.authentication import APIKeyAuthentication, APIKeyUser


class APIKeyAuthenticationTest(TestCase):
    def setUp(self):
        self.auth = APIKeyAuthentication()
        self.factory = APIRequestFactory()

    @override_settings(AHMIA_API_KEY='test-secret-key')
    def test_valid_api_key_authenticates(self):
        request = self.factory.get('/', HTTP_X_API_KEY='test-secret-key')
        result = self.auth.authenticate(request)
        self.assertIsInstance(result[0], APIKeyUser)
        self.assertTrue(result[0].is_authenticated)
        self.assertIsNone(result[1])

    @override_settings(AHMIA_API_KEY='test-secret-key')
    def test_invalid_api_key_raises_exception(self):
        request = self.factory.get('/', HTTP_X_API_KEY='wrong-key')
        with self.assertRaises(AuthenticationFailed):
            self.auth.authenticate(request)

    @override_settings(AHMIA_API_KEY='test-secret-key')
    def test_missing_api_key_returns_none(self):
        request = self.factory.get('/')
        result = self.auth.authenticate(request)
        self.assertIsNone(result)
