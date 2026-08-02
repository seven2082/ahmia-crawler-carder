from django.views.generic import ListView, DetailView

from .mixins import ContributorMixin
from ..models import Category, Tag, OnionProfile


class CategoryListView(ContributorMixin, ListView):
    """List all categories."""

    model = Category
    template_name = 'profiles/category_list.html'
    context_object_name = 'categories'

    def get_queryset(self):
        return Category.objects.annotate_profile_count().order_by('name')


class CategoryDetailView(ContributorMixin, DetailView):
    """Profiles in a category."""

    model = Category
    template_name = 'profiles/category_detail.html'
    context_object_name = 'category'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profiles'] = OnionProfile.objects.filter(
            category=self.object
        ).select_related('category')[:50]
        return context


class TagListView(ContributorMixin, ListView):
    """List all tags."""

    model = Tag
    template_name = 'profiles/tag_list.html'
    context_object_name = 'tags'

    def get_queryset(self):
        return Tag.objects.annotate_profile_count().order_by('-profile_count')[:100]


class TagDetailView(ContributorMixin, DetailView):
    """Profiles with a tag."""

    model = Tag
    template_name = 'profiles/tag_detail.html'
    context_object_name = 'tag'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profiles'] = self.object.profiles.all()[:50]
        return context
