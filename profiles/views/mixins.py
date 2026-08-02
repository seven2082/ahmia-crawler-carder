from django.http import HttpResponseForbidden
from django.contrib import messages
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _

from ..models import Contributor
from ..services import get_service
from ..constants import TrustLevel


class ContributorMixin:
    """Mixin that adds contributor to view context."""

    def get_contributor(self):
        """Get or create contributor for current request."""
        if not hasattr(self, '_contributor'):
            trust_service = get_service('trust_service')
            self._contributor = trust_service.get_or_create_contributor(self.request)
        return self._contributor

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['contributor'] = self.get_contributor()
        return context


class TrustRequiredMixin(ContributorMixin):
    """Mixin that requires minimum trust level."""

    required_trust_level = TrustLevel.NEW

    def dispatch(self, request, *args, **kwargs):
        contributor = self.get_contributor()

        if contributor.is_banned:
            messages.error(request, _('You are banned from contributing.'))
            return redirect('home')

        if contributor.trust_level < self.required_trust_level:
            messages.error(request, _('Insufficient trust level for this action.'))
            return redirect('home')

        return super().dispatch(request, *args, **kwargs)


class ModeratorRequiredMixin(TrustRequiredMixin):
    """Mixin that requires moderator trust level."""

    required_trust_level = TrustLevel.MODERATOR


class ProfileOwnerMixin(ContributorMixin):
    """Mixin that allows verified profile owner or moderator."""

    def dispatch(self, request, *args, **kwargs):
        contributor = self.get_contributor()
        profile = self.get_object()

        # Allow moderators
        if contributor.is_moderator:
            return super().dispatch(request, *args, **kwargs)

        # Allow verified owners
        if profile.is_verified and profile.owner == contributor.user:
            return super().dispatch(request, *args, **kwargs)

        messages.error(request, _('You must be the verified owner of this site.'))
        return redirect('profiles:detail', slug=profile.slug)
