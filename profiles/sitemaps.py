from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import OnionProfile, Category
from .constants import ProfileStatus


class ProfileSitemap(Sitemap):
    """Sitemap for profile detail pages."""

    changefreq = 'weekly'
    priority = 0.7

    def items(self):
        return OnionProfile.objects.filter(
            status=ProfileStatus.ACTIVE
        ).order_by('-updated_at')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('profiles:detail', kwargs={'slug': obj.slug})


class CategorySitemap(Sitemap):
    """Sitemap for category pages."""

    changefreq = 'weekly'
    priority = 0.6

    def items(self):
        return Category.objects.all()

    def location(self, obj):
        return reverse('profiles:category_detail', kwargs={'slug': obj.slug})


class ProfileStaticSitemap(Sitemap):
    """Sitemap for static profile pages."""

    changefreq = 'daily'
    priority = 0.8

    def items(self):
        return ['profiles:list', 'profiles:category_list', 'profiles:tag_list']

    def location(self, item):
        return reverse(item)
