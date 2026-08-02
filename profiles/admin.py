from django.contrib import admin

from .models import (
    Category, Tag, OnionProfile, ProfileTag, DomainHistory,
    Contributor, ProfileEdit, MigrationReport
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'profile_count')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

    def profile_count(self, obj):
        return obj.profiles.count()
    profile_count.short_description = 'Profiles'


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'profile_count')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}

    def profile_count(self, obj):
        return obj.profiles.count()
    profile_count.short_description = 'Profiles'


class DomainHistoryInline(admin.TabularInline):
    model = DomainHistory
    extra = 0
    readonly_fields = ('domain', 'was_active_from', 'was_active_to', 'migration_type')


class ProfileTagInline(admin.TabularInline):
    model = ProfileTag
    extra = 1


@admin.register(OnionProfile)
class OnionProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'current_domain_short', 'category', 'status', 'is_verified', 'page_count')
    list_filter = ('status', 'is_verified', 'category')
    search_fields = ('name', 'slug', 'current_domain')
    readonly_fields = ('id', 'created_at', 'updated_at', 'page_count', 'last_seen')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [DomainHistoryInline, ProfileTagInline]

    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description', 'category')
        }),
        ('Domain', {
            'fields': ('current_domain', 'status')
        }),
        ('Ownership', {
            'fields': ('owner', 'is_verified', 'verification_token')
        }),
        ('Stats', {
            'fields': ('page_count', 'last_seen'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def current_domain_short(self, obj):
        domain = obj.current_domain
        if len(domain) > 30:
            return f'{domain[:30]}...'
        return domain
    current_domain_short.short_description = 'Domain'


@admin.register(Contributor)
class ContributorAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'trust_level', 'approved_edits', 'rejected_edits', 'is_banned')
    list_filter = ('trust_level', 'is_banned')
    search_fields = ('user__username', 'session_key')
    readonly_fields = ('session_key', 'ip_hash', 'created_at')

    fieldsets = (
        (None, {
            'fields': ('user', 'trust_level')
        }),
        ('Stats', {
            'fields': ('approved_edits', 'rejected_edits')
        }),
        ('Moderation', {
            'fields': ('is_banned', 'cooldown_until')
        }),
        ('Session', {
            'fields': ('session_key', 'ip_hash', 'created_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ProfileEdit)
class ProfileEditAdmin(admin.ModelAdmin):
    list_display = ('profile', 'field_name', 'status', 'submitted_by', 'created_at')
    list_filter = ('status', 'field_name')
    search_fields = ('profile__name', 'profile__slug')
    readonly_fields = ('profile', 'field_name', 'old_value', 'new_value', 'submitted_by', 'created_at')

    def has_add_permission(self, request):
        return False


@admin.register(MigrationReport)
class MigrationReportAdmin(admin.ModelAdmin):
    list_display = ('profile', 'old_domain_short', 'new_domain_short', 'source', 'status', 'created_at')
    list_filter = ('status', 'source')
    search_fields = ('profile__name', 'old_domain', 'new_domain')
    readonly_fields = ('profile', 'old_domain', 'new_domain', 'submitted_by', 'created_at')

    def old_domain_short(self, obj):
        return f'{obj.old_domain[:25]}...' if len(obj.old_domain) > 25 else obj.old_domain
    old_domain_short.short_description = 'Old'

    def new_domain_short(self, obj):
        return f'{obj.new_domain[:25]}...' if len(obj.new_domain) > 25 else obj.new_domain
    new_domain_short.short_description = 'New'

    def has_add_permission(self, request):
        return False
