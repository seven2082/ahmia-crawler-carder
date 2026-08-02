from django.db import models
from django.utils.text import slugify


class CategoryQuerySet(models.QuerySet):
    def annotate_profile_count(self):
        """Annotate each category with its number of related profiles."""
        return self.annotate(profile_count=models.Count('profiles'))


class TagQuerySet(models.QuerySet):
    def annotate_profile_count(self):
        """Annotate each tag with its number of related profiles."""
        return self.annotate(profile_count=models.Count('profiles', distinct=True))


class Category(models.Model):
    """Fixed taxonomy for primary categorization."""
    name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=50, unique=True)
    description = models.TextField(blank=True, default='')
    icon = models.CharField(max_length=50, blank=True, default='')
    display_order = models.IntegerField(default=0)

    objects = CategoryQuerySet.as_manager()

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Tag(models.Model):
    """Freeform tags for additional classification."""
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = TagQuerySet.as_manager()

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
