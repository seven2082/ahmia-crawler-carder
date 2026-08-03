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

            es_url = getattr(settings, 'ELASTICSEARCH_SERVER', 'http://127.0.0.1:9200')
            use_ssl = es_url.startswith('https://')

            es_user = getattr(settings, 'ELASTICSEARCH_USERNAME', '')
            es_pass = getattr(settings, 'ELASTICSEARCH_PASSWORD', '')

            if use_ssl and es_user and es_pass:
                self._client = Elasticsearch(
                    hosts=[es_url],
                    basic_auth=(es_user, es_pass),
                    ca_certs=getattr(settings, 'ELASTICSEARCH_CA_CERTS', None),
                    verify_certs=getattr(settings, 'VERIFY_CERT', False),
                    ssl_show_warn=False,
                    timeout=getattr(settings, 'ELASTICSEARCH_TIMEOUT', 60)
                )
            elif use_ssl:
                self._client = Elasticsearch(
                    hosts=[es_url],
                    verify_certs=False,
                    ssl_show_warn=False,
                    timeout=getattr(settings, 'ELASTICSEARCH_TIMEOUT', 60)
                )
            else:
                self._client = Elasticsearch(
                    hosts=[es_url],
                    timeout=getattr(settings, 'ELASTICSEARCH_TIMEOUT', 60)
                )
        return self._client

    @property
    def index(self) -> str:
        return getattr(settings, 'ELASTICSEARCH_INDEX', 'ahmia-pages')

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
        """Extract best title and description for a domain, filtering spam/generic."""
        response = self.client.search(
            index=self.index,
            body={
                'size': 50,
                'query': {
                    'bool': {
                        'must': [{'term': {'domain': domain}}],
                        'must_not': [{'term': {'is_banned': True}}]
                    }
                },
                '_source': ['title', 'meta'],
                'sort': [{'updated_on': 'desc'}]
            }
        )

        hits = response.get('hits', {}).get('hits', [])

        titles = {}
        descriptions = {}
        for hit in hits:
            src = hit.get('_source', {})
            t = src.get('title', '').strip()
            d = src.get('meta', '').strip()
            if t:
                titles[t] = titles.get(t, 0) + 1
            if d:
                descriptions[d] = descriptions.get(d, 0) + 1

        generic_titles = {
            'home', 'index', 'welcome', 'untitled', '', 'loading', 'error',
            '404', 'not found', 'page not found', 'access denied', 'forbidden',
            'coming soon', 'under construction', 'maintenance', 'offline'
        }

        spam_patterns = [
            'child porn', 'child sex', 'child abuse', 'child nude', 'child naked',
            'cp porn', 'kids porn', 'kiddie porn', 'kiddie',
            'pedo', 'pedophil',
            'loli porn', 'loli hentai', 'lolibooru', 'lolicon', 'lolihub',
            'preteen porn', 'preteen sex', 'preteen nude', 'preteens',
            'jailbait', 'underage',
            'young nude', 'young porn', 'young sex', 'youngandcute',
            'cphub', 'boyslove', 'girlslove', 'boylove', 'girllove',
            'toddlercon', 'shotacon', 'shota',
            'baby slut', 'baby porn', 'baby sex',
            'bestiality', 'zoophilia', 'animal sex', 'zoo porn', 'zoo sex', 'zoo teen',
            'real child', 'real kids', 'real cp',
            'hardcore cp', 'hurtcore', 'hardcore baby',
            'little angel', 'little girl', 'little boy', 'small girl', 'small boy',
            'children porn', 'childrens porn', 'nice children',
            'young cam', 'underage cam', 'teen cam',
            'nn model', 'cp cp', 'cp |', '| cp'
        ]

        def is_spam(text):
            lower = text.lower()
            return any(p in lower for p in spam_patterns)

        def is_generic(text):
            return text.lower().strip() in generic_titles

        best_title = ''
        sorted_titles = sorted(titles.items(), key=lambda x: (-x[1], -len(x[0])))
        for title, count in sorted_titles:
            if title and not is_generic(title) and not is_spam(title):
                best_title = title
                break

        best_description = ''
        sorted_descs = sorted(descriptions.items(), key=lambda x: (-x[1], -len(x[0])))
        for desc, count in sorted_descs:
            if desc and not is_spam(desc):
                best_description = desc
                break

        if not best_title:
            domain_prefix = domain.replace('.onion', '')[:16]
            best_title = domain_prefix

        return {
            'title': best_title[:200],
            'description': best_description[:500] if best_description else ''
        }
