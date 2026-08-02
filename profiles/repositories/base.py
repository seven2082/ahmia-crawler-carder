from typing import TypeVar, Generic, Optional, List
from django.db.models import Model, QuerySet

T = TypeVar('T', bound=Model)


class BaseRepository(Generic[T]):
    """Abstract base repository with common CRUD operations."""

    model: type[T]

    def get_queryset(self) -> QuerySet[T]:
        """Return base queryset. Override for default filters."""
        return self.model.objects.all()

    def get_by_id(self, id) -> T:
        """Get by primary key or raise DoesNotExist."""
        return self.get_queryset().get(pk=id)

    def get_by_id_or_none(self, id) -> Optional[T]:
        """Get by primary key or return None."""
        try:
            return self.get_by_id(id)
        except self.model.DoesNotExist:
            return None

    def list_all(self) -> QuerySet[T]:
        """Return all records."""
        return self.get_queryset()

    def create(self, **kwargs) -> T:
        """Create and return new record."""
        return self.model.objects.create(**kwargs)

    def update(self, instance: T, **kwargs) -> T:
        """Update instance with kwargs."""
        for key, value in kwargs.items():
            setattr(instance, key, value)
        instance.save()
        return instance

    def delete(self, instance: T) -> None:
        """Delete instance."""
        instance.delete()

    def exists(self, **kwargs) -> bool:
        """Check if record exists."""
        return self.get_queryset().filter(**kwargs).exists()

    def count(self) -> int:
        """Count all records."""
        return self.get_queryset().count()
