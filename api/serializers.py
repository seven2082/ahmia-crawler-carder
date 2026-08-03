from rest_framework import serializers
from profiles.models import OnionProfile, DomainHistory


class DomainHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DomainHistory
        fields = ['domain', 'was_active_from', 'was_active_to', 'migration_type']


class ProfileSerializer(serializers.ModelSerializer):
    domain_history = DomainHistorySerializer(many=True, read_only=True)
    category = serializers.StringRelatedField()
    tags = serializers.StringRelatedField(many=True)
    owner_username = serializers.CharField(source='owner.username', default=None)
    verified_at = serializers.SerializerMethodField()

    def get_verified_at(self, obj):
        if obj.is_verified and obj.updated_at:
            return obj.updated_at
        return None

    class Meta:
        model = OnionProfile
        fields = [
            'slug', 'current_domain', 'name', 'description', 'category',
            'is_verified', 'verified_at', 'owner_username',
            'page_count', 'last_seen', 'status', 'domain_history', 'tags',
            'is_online', 'response_time_ms', 'last_checked', 'screenshot',
            'created_at', 'updated_at'
        ]
