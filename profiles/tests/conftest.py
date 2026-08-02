import pytest
from django.test import RequestFactory


@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.fixture
def anonymous_request(request_factory):
    request = request_factory.get('/')
    request.session = {}
    return request
