from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils.dateparse import parse_datetime
from django.conf import settings

from profiles.models import OnionProfile
from profiles.constants import ProfileStatus
from .serializers import ProfileSerializer
from .authentication import APIKeyAuthentication


class ProfileListView(generics.ListAPIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileSerializer

    def get_queryset(self):
        qs = OnionProfile.objects.select_related(
            'category', 'owner'
        ).prefetch_related(
            'tags', 'domain_history'
        )

        updated_since = self.request.query_params.get('updated_since')
        if updated_since:
            dt = parse_datetime(updated_since)
            if dt:
                qs = qs.filter(updated_at__gte=dt)

        return qs.order_by('-updated_at')


class ProfileDetailView(generics.RetrieveAPIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileSerializer
    lookup_field = 'slug'
    queryset = OnionProfile.objects.select_related(
        'category', 'owner'
    ).prefetch_related(
        'tags', 'domain_history'
    )


class ProfileByDomainView(generics.RetrieveAPIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileSerializer
    lookup_field = 'current_domain'
    lookup_url_kwarg = 'domain'
    queryset = OnionProfile.objects.select_related(
        'category', 'owner'
    ).prefetch_related(
        'tags', 'domain_history'
    )


class StatsView(APIView):
    """GET /api/v1/stats/ - Platform statistics"""
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        total_profiles = OnionProfile.objects.filter(
            status=ProfileStatus.ACTIVE
        ).count()

        verified_profiles = OnionProfile.objects.filter(
            status=ProfileStatus.ACTIVE,
            is_verified=True
        ).count()

        # Get indexed pages from Elasticsearch
        indexed_pages = 0
        try:
            from elasticsearch import Elasticsearch
            es_url = getattr(settings, 'ELASTICSEARCH_SERVER', 'http://127.0.0.1:9200')
            es = Elasticsearch(hosts=[es_url], timeout=10)
            count = es.count(index='ahmia-pages')
            indexed_pages = count.get('count', 0)
        except Exception:
            pass

        return Response({
            'total_profiles': total_profiles,
            'verified_profiles': verified_profiles,
            'indexed_pages': indexed_pages,
        })
