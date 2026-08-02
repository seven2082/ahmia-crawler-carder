from django.views.generic import ListView, DetailView, FormView, TemplateView
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from .mixins import ContributorMixin, TrustRequiredMixin
from ..models import OnionProfile
from ..forms import ProfileEditForm, ClaimForm
from ..services import get_service
from ..repositories import ProfileRepository


class ProfileListView(ContributorMixin, ListView):
    """Paginated directory of profiles."""

    model = OnionProfile
    template_name = 'profiles/profile_list.html'
    context_object_name = 'profiles'
    paginate_by = 24

    def get_queryset(self):
        repo = ProfileRepository()
        return repo.list_active()


class ProfileDetailView(ContributorMixin, DetailView):
    """Individual profile page with stats."""

    model = OnionProfile
    template_name = 'profiles/profile_detail.html'
    context_object_name = 'profile'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get live stats
        try:
            profile_service = get_service('profile_service')
            data = profile_service.get_profile_with_stats(self.object.slug)
            context['page_count'] = data['page_count']
            context['last_seen'] = data['last_seen']
            context['top_pages'] = data['top_pages']
        except Exception:
            context['page_count'] = self.object.page_count
            context['last_seen'] = self.object.last_seen
            context['top_pages'] = []

        # Get domain history
        context['domain_history'] = self.object.domain_history.all()[:10]

        return context


class ProfileEditView(TrustRequiredMixin, FormView):
    """Submit edit suggestions for a profile."""

    template_name = 'profiles/profile_edit.html'
    form_class = ProfileEditForm

    def get_profile(self):
        if not hasattr(self, '_profile'):
            self._profile = get_object_or_404(OnionProfile, slug=self.kwargs['slug'])
        return self._profile

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = self.get_profile()
        return context

    def get_initial(self):
        profile = self.get_profile()
        return {
            'name': profile.name,
            'description': profile.description,
            'category': profile.category,
        }

    def form_valid(self, form):
        profile = self.get_profile()
        contributor = self.get_contributor()
        moderation_service = get_service('moderation_service')

        # Submit edits for changed fields
        edits_submitted = 0
        for field in ['name', 'description']:
            new_value = form.cleaned_data.get(field)
            old_value = getattr(profile, field)
            if new_value and new_value != old_value:
                moderation_service.submit_edit(profile, field, new_value, contributor)
                edits_submitted += 1

        if edits_submitted > 0:
            messages.success(self.request, _('Your edits have been submitted for review.'))
        else:
            messages.info(self.request, _('No changes detected.'))

        return redirect('profiles:detail', slug=profile.slug)


class ProfileClaimView(ContributorMixin, FormView):
    """Claim ownership of a profile."""

    template_name = 'profiles/profile_claim.html'
    form_class = ClaimForm

    def get_profile(self):
        if not hasattr(self, '_profile'):
            self._profile = get_object_or_404(OnionProfile, slug=self.kwargs['slug'])
        return self._profile

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        context['profile'] = profile

        # Generate or get verification token
        if not profile.verification_token:
            verification_service = get_service('verification_service')
            token = verification_service.start_verification(profile)
        else:
            token = profile.verification_token

        context['verification_token'] = token
        context['well_known_path'] = '/.well-known/ahmia-verify.txt'

        return context

    def form_valid(self, form):
        profile = self.get_profile()
        verification_service = get_service('verification_service')

        if verification_service.check_verification(profile):
            # Link owner
            contributor = self.get_contributor()
            if contributor.user:
                profile.owner = contributor.user
                profile.save(update_fields=['owner'])
            messages.success(self.request, _('Your site has been verified!'))
        else:
            messages.error(self.request, _('Verification failed. Please check the file.'))

        return redirect('profiles:detail', slug=profile.slug)


class ProfileHistoryView(ContributorMixin, DetailView):
    """View profile's URL history and edit log."""

    model = OnionProfile
    template_name = 'profiles/profile_history.html'
    context_object_name = 'profile'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['domain_history'] = self.object.domain_history.all()
        context['recent_edits'] = self.object.edits.all()[:20]
        return context
