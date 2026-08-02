import uuid

from django.db import models

from profiles.models.base import BaseModel


def test_base_model_is_abstract():
    assert BaseModel._meta.abstract is True


def test_base_model_has_uuid_primary_key():
    field = BaseModel._meta.get_field('id')
    assert isinstance(field, models.UUIDField)
    assert field.primary_key is True
    assert field.default is uuid.uuid4
    assert field.editable is False


def test_base_model_has_created_at_auto_now_add():
    field = BaseModel._meta.get_field('created_at')
    assert isinstance(field, models.DateTimeField)
    assert field.auto_now_add is True


def test_base_model_has_updated_at_auto_now():
    field = BaseModel._meta.get_field('updated_at')
    assert isinstance(field, models.DateTimeField)
    assert field.auto_now is True
