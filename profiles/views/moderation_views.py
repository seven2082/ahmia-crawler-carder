from django.views.generic import ListView, FormView
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from .mixins import ModeratorRequiredMixin, TrustRequiredMixin
from ..models import ProfileEdit, MigrationReport
from ..forms import EditReviewForm
from ..services import get_service
from ..constants import EditStatus


class ModerationQueueView(TrustRequiredMixin, ListView):
    """Queue of pending edits and migrations."""

    template_name = 'profiles/moderation_queue.html'
    context_object_name = 'items'
    paginate_by = 50

    def get_queryset(self):
        edits = ProfileEdit.objects.filter(
            status=EditStatus.PENDING
        ).select_related('profile', 'submitted_by').order_by('-created_at')
        return edits

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pending_migrations'] = MigrationReport.objects.filter(
            status=EditStatus.PENDING
        ).select_related('profile', 'submitted_by')[:20]

        moderation_service = get_service('moderation_service')
        context['pending_count'] = moderation_service.count_pending()
        return context


class EditReviewView(TrustRequiredMixin, FormView):
    """Review a single edit."""

    template_name = 'profiles/edit_review.html'
    form_class = EditReviewForm

    def get_edit(self):
        if not hasattr(self, '_edit'):
            self._edit = get_object_or_404(ProfileEdit, id=self.kwargs['edit_id'])
        return self._edit

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['edit'] = self.get_edit()
        context['profile'] = self.get_edit().profile
        return context

    def form_valid(self, form):
        edit = self.get_edit()
        contributor = self.get_contributor()
        moderation_service = get_service('moderation_service')

        action = form.cleaned_data['action']
        notes = form.cleaned_data.get('notes', '')

        if action == 'approve':
            moderation_service.approve_edit(edit, contributor, notes)
            messages.success(self.request, _('Edit approved.'))
        else:
            moderation_service.reject_edit(edit, contributor, notes)
            messages.info(self.request, _('Edit rejected.'))

        return redirect('profiles:moderation_queue')


class MigrationReviewView(ModeratorRequiredMixin, FormView):
    """Review a migration report (moderator only)."""

    template_name = 'profiles/migration_review.html'
    form_class = EditReviewForm

    def get_migration(self):
        if not hasattr(self, '_migration'):
            self._migration = get_object_or_404(MigrationReport, id=self.kwargs['migration_id'])
        return self._migration

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['migration'] = self.get_migration()
        context['profile'] = self.get_migration().profile
        return context

    def form_valid(self, form):
        migration = self.get_migration()
        contributor = self.get_contributor()
        moderation_service = get_service('moderation_service')

        action = form.cleaned_data['action']
        notes = form.cleaned_data.get('notes', '')

        if action == 'approve':
            moderation_service.approve_migration(migration, contributor, notes)
            messages.success(self.request, _('Migration approved. Domain updated.'))
        else:
            moderation_service.reject_migration(migration, contributor, notes)
            messages.info(self.request, _('Migration rejected.'))

        return redirect('profiles:moderation_queue')
