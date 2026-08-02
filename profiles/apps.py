from django.apps import AppConfig


class ProfilesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'profiles'
    verbose_name = 'Onion Profiles'

    def ready(self):
        from . import signals  # noqa: F401
