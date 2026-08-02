from typing import Any, Callable, Dict, Optional, Type
from functools import wraps

class ServiceRegistry:
    """
    Registry for pluggable services.

    Allows overriding default implementations for extensibility.
    Example: Replace ElasticsearchService with MockElasticsearchService for testing.
    """

    _instances: Dict[str, Any] = {}
    _factories: Dict[str, Callable[[], Any]] = {}

    def __init__(self):
        self._instances = {}
        self._factories = {}

    def register(self, name: str, factory: Callable[[], Any]) -> None:
        """Register a service factory."""
        self._factories[name] = factory
        # Clear cached instance if exists
        self._instances.pop(name, None)

    def get(self, name: str) -> Any:
        """Get service instance (lazy singleton per name)."""
        if name not in self._instances:
            if name not in self._factories:
                raise KeyError(f"Service '{name}' not registered")
            self._instances[name] = self._factories[name]()
        return self._instances[name]

    def clear(self) -> None:
        """Clear all registered services."""
        self._instances.clear()
        self._factories.clear()

    def reset_instance(self, name: str) -> None:
        """Reset cached instance, forcing re-creation on next get."""
        self._instances.pop(name, None)


# Global default registry
_default_registry = ServiceRegistry()


def register_service(
    name: str,
    registry: Optional[ServiceRegistry] = None
) -> Callable[[Type], Type]:
    """
    Decorator to register a class as a service.

    Usage:
        @register_service('profile_service')
        class ProfileService:
            ...
    """
    reg = registry or _default_registry

    def decorator(cls: Type) -> Type:
        reg.register(name, cls)
        return cls

    return decorator


def get_service(name: str, registry: Optional[ServiceRegistry] = None) -> Any:
    """Get a service by name from the registry."""
    reg = registry or _default_registry
    return reg.get(name)


def get_default_registry() -> ServiceRegistry:
    """Get the default global registry."""
    return _default_registry
