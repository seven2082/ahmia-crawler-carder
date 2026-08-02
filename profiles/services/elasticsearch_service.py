from typing import List, Dict, Optional, Any
from datetime import datetime
from django.conf import settings

from .registry import register_service


@register_service('elasticsearch_service')
class ElasticsearchService:
    """Service for querying Elasticsearch crawl data."""

    def __init__(self, es_client=None):
        self._client = es_client

    @property
    def client(self):
        """Lazy-load ES client."""
        if self._client is None:
            from elasticsearch import Elasticsearch
            self._client = Elasticsearch(
                hosts=[settings.ELASTICSEARCH_SERVER],
                http_auth=(settings.ELASTICSEARCH_USERNAME, settings.ELASTICSEARCH_PASSWORD),
                ca_certs=settings.ELASTICSEARCH_CA_CERTS,
                verify_certs=settings.VERIFY_CERT,
                ssl_show_warn=settings.VERIFY_CERT,
                timeout=settings.ELASTICSEARCH_TIMEOUT
            )
        return self._client

    @property
    def index(self) -> str:
        return settings.ELASTICSEARCH_INDEX

    def get_domain_stats(self, domain: str) -> Dict[str, Any]:
        """Get page count and last seen for a domain."""
        response = self.client.search(
            index=self.index,
            body={
                'size': 0,
                'query': {
                    'bool': {
                        'must': [{'term': {'domain': domain}}],
                        'must_not': [{'term': {'is_banned': True}}]
                    }
                },
                'aggs': {
                    'page_count': {'value_count': {'field': 'url'}},
                    'last_seen': {'max': {'field': 'updated_on'}}
                }
            }
        )

        aggs = response.get('aggregations', {})
        page_count = int(aggs.get('page_count', {}).get('value', 0))
        last_seen_str = aggs.get('last_seen', {}).get('value_as_string')
        last_seen = None
        if last_seen_str:
            try:
                last_seen = datetime.fromisoformat(last_seen_str.replace('Z', '+00:00'))
            except ValueError:
                pass

        return {
            'page_count': page_count,
            'last_seen': last_seen
        }

    def get_all_domains(self, exclude_banned: bool = True) -> List[Dict[str, Any]]:
        """Get all unique domains with page counts."""
        must_not = [{'term': {'is_banned': True}}] if exclude_banned else []

        response = self.client.search(
            index=self.index,
            body={
                'size': 0,
                'query': {'bool': {'must_not': must_not}} if must_not else {'match_all': {}},
                'aggs': {
                    'domains': {
                        'terms': {
                            'field': 'domain',
                            'size': 300000
                        }
                    }
                }
            }
        )

        buckets = response.get('aggregations', {}).get('domains', {}).get('buckets', [])
        return [
            {'domain': b['key'], 'page_count': b['doc_count']}
            for b in buckets
        ]

    def get_top_pages(self, domain: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top pages for a domain (by relevance/recency)."""
        response = self.client.search(
            index=self.index,
            body={
                'size': limit,
                'query': {
                    'bool': {
                        'must': [{'term': {'domain': domain}}],
                        'must_not': [{'term': {'is_banned': True}}]
                    }
                },
                'sort': [{'updated_on': 'desc'}],
                '_source': ['url', 'title', 'meta', 'updated_on']
            }
        )

        hits = response.get('hits', {}).get('hits', [])
        return [hit['_source'] for hit in hits]

    def get_domain_metadata(self, domain: str) -> Dict[str, Any]:
        """Extract most common title and description for a domain."""
        response = self.client.search(
            index=self.index,
            body={
                'size': 0,
                'query': {
                    'bool': {
                        'must': [{'term': {'domain': domain}}],
                        'must_not': [{'term': {'is_banned': True}}]
                    }
                },
                'aggs': {
                    'titles': {
                        'terms': {'field': 'title.keyword', 'size': 5}
                    },
                    'descriptions': {
                        'terms': {'field': 'meta.keyword', 'size': 5}
                    }
                }
            }
        )

        aggs = response.get('aggregations', {})
        titles = aggs.get('titles', {}).get('buckets', [])
        descriptions = aggs.get('descriptions', {}).get('buckets', [])

        # Filter out generic titles
        generic_titles = {'home', 'index', 'welcome', 'untitled', ''}
        best_title = ''
        for t in titles:
            if t['key'].lower().strip() not in generic_titles:
                best_title = t['key']
                break

        best_description = descriptions[0]['key'] if descriptions else ''

        return {
            'title': best_title,
            'description': best_description[:500] if best_description else ''
        }
