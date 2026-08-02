import pytest
from unittest.mock import MagicMock, patch


class TestElasticsearchService:
    def test_get_domain_stats(self):
        from profiles.services.elasticsearch_service import ElasticsearchService

        mock_client = MagicMock()
        mock_client.search.return_value = {
            'aggregations': {
                'page_count': {'value': 42},
                'last_seen': {'value_as_string': '2026-07-31T10:00:00'}
            }
        }

        service = ElasticsearchService(es_client=mock_client)
        stats = service.get_domain_stats('example.onion')

        assert stats['page_count'] == 42
        assert stats['last_seen'] is not None

    def test_get_domain_stats_missing_aggregations(self):
        from profiles.services.elasticsearch_service import ElasticsearchService

        mock_client = MagicMock()
        mock_client.search.return_value = {'aggregations': {}}

        service = ElasticsearchService(es_client=mock_client)
        stats = service.get_domain_stats('example.onion')

        assert stats['page_count'] == 0
        assert stats['last_seen'] is None

    def test_get_all_domains(self):
        from profiles.services.elasticsearch_service import ElasticsearchService

        mock_client = MagicMock()
        mock_client.search.return_value = {
            'aggregations': {
                'domains': {
                    'buckets': [
                        {'key': 'site1.onion', 'doc_count': 100},
                        {'key': 'site2.onion', 'doc_count': 50},
                    ]
                }
            }
        }

        service = ElasticsearchService(es_client=mock_client)
        domains = service.get_all_domains()

        assert len(domains) == 2
        assert domains[0]['domain'] == 'site1.onion'
        assert domains[0]['page_count'] == 100

    def test_get_top_pages(self):
        from profiles.services.elasticsearch_service import ElasticsearchService

        mock_client = MagicMock()
        mock_client.search.return_value = {
            'hits': {
                'hits': [
                    {'_source': {'url': 'http://x.onion/', 'title': 'Home'}},
                    {'_source': {'url': 'http://x.onion/about', 'title': 'About'}},
                ]
            }
        }

        service = ElasticsearchService(es_client=mock_client)
        pages = service.get_top_pages('x.onion', limit=5)

        assert len(pages) == 2
        assert pages[0]['title'] == 'Home'

    def test_get_domain_metadata_skips_generic_titles(self):
        from profiles.services.elasticsearch_service import ElasticsearchService

        mock_client = MagicMock()
        mock_client.search.return_value = {
            'aggregations': {
                'titles': {
                    'buckets': [
                        {'key': 'Home', 'doc_count': 5},
                        {'key': 'Best Market', 'doc_count': 3},
                    ]
                },
                'descriptions': {
                    'buckets': [
                        {'key': 'A great market for things', 'doc_count': 4},
                    ]
                }
            }
        }

        service = ElasticsearchService(es_client=mock_client)
        metadata = service.get_domain_metadata('x.onion')

        assert metadata['title'] == 'Best Market'
        assert metadata['description'] == 'A great market for things'

    def test_client_property_lazy_loads_from_settings(self):
        from profiles.services.elasticsearch_service import ElasticsearchService

        service = ElasticsearchService()

        with patch('elasticsearch.Elasticsearch') as mock_es_cls:
            mock_es_cls.return_value = MagicMock()
            client = service.client

            assert client is mock_es_cls.return_value
            mock_es_cls.assert_called_once()
            # Cached on subsequent access
            assert service.client is client

    def test_registered_in_service_registry(self):
        from profiles.services.elasticsearch_service import ElasticsearchService
        from profiles.services.registry import get_default_registry

        registry = get_default_registry()
        assert registry._factories.get('elasticsearch_service') is ElasticsearchService
