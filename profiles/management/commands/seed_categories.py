from django.core.management.base import BaseCommand

from profiles.models import Category


DEFAULT_CATEGORIES = [
    ('forum', 'Forum', 'Discussion boards and communities'),
    ('market', 'Marketplace', 'E-commerce and trading platforms'),
    ('news', 'News', 'News sites and journalism'),
    ('social', 'Social', 'Social networks and communication'),
    ('search', 'Search', 'Search engines and directories'),
    ('hosting', 'Hosting', 'Web hosting and infrastructure'),
    ('email', 'Email', 'Email services'),
    ('crypto', 'Cryptocurrency', 'Cryptocurrency services'),
    ('wiki', 'Wiki', 'Wikis and knowledge bases'),
    ('blog', 'Blog', 'Personal and group blogs'),
    ('tools', 'Tools', 'Utilities and tools'),
    ('other', 'Other', 'Uncategorized sites'),
]


class Command(BaseCommand):
    help = 'Seed initial categories'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Update existing categories'
        )

    def handle(self, *args, **options):
        created = 0
        updated = 0

        for slug, name, description in DEFAULT_CATEGORIES:
            if options['force']:
                category, was_created = Category.objects.update_or_create(
                    slug=slug,
                    defaults={'name': name, 'description': description}
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
            else:
                category, was_created = Category.objects.get_or_create(
                    slug=slug,
                    defaults={'name': name, 'description': description}
                )
                if was_created:
                    created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Categories seeded: {created} created, {updated} updated'
            )
        )
