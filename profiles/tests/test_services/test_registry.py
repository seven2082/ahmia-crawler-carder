import pytest


class TestServiceRegistry:
    def test_register_and_get_service(self):
        from profiles.services.registry import ServiceRegistry, register_service, get_service

        registry = ServiceRegistry()

        @register_service('test_service', registry=registry)
        class TestService:
            def do_something(self):
                return 'done'

        service = get_service('test_service', registry=registry)
        assert service.do_something() == 'done'

    def test_get_unregistered_service_raises(self):
        from profiles.services.registry import ServiceRegistry, get_service

        registry = ServiceRegistry()
        with pytest.raises(KeyError):
            get_service('nonexistent', registry=registry)

    def test_override_service(self):
        from profiles.services.registry import ServiceRegistry, register_service, get_service

        registry = ServiceRegistry()

        @register_service('overridable', registry=registry)
        class OriginalService:
            def value(self):
                return 'original'

        @register_service('overridable', registry=registry)
        class OverrideService:
            def value(self):
                return 'override'

        service = get_service('overridable', registry=registry)
        assert service.value() == 'override'
