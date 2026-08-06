import re
import time
from typing import Dict, Any, Optional, Tuple
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

from .registry import register_service


@register_service('crawler_service')
class CrawlerService:
    """Service for crawling .onion sites to extract metadata."""

    def __init__(self, tor_host: str = '127.0.0.1', tor_port: int = 9050, timeout: int = 45):
        self.tor_host = tor_host
        self.tor_port = tor_port
        self.timeout = timeout
        self.proxies = {
            'http': f'socks5h://{tor_host}:{tor_port}',
            'https': f'socks5h://{tor_host}:{tor_port}'
        }

    def _create_session(self) -> requests.Session:
        """Create a requests session with retry logic."""
        session = requests.Session()
        retry = Retry(total=2, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

    def fetch_page(self, url: str) -> Tuple[Optional[str], Optional[int]]:
        """Fetch page HTML via Tor. Returns (html, response_time_ms)."""
        try:
            session = self._create_session()
            start_time = time.time()

            response = session.get(
                url,
                proxies=self.proxies,
                timeout=self.timeout,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
                allow_redirects=True,
                verify=False
            )

            response_time_ms = int((time.time() - start_time) * 1000)

            if response.status_code < 400:
                return response.text, response_time_ms
            else:
                return None, None

        except requests.exceptions.Timeout:
            return None, None
        except requests.exceptions.ConnectionError:
            return None, None
        except Exception:
            return None, None

    def check_reachable(self, domain: str) -> Tuple[bool, Optional[int]]:
        """Quick reachability check using HEAD request."""
        try:
            session = self._create_session()
            start_time = time.time()

            # Try HTTPS first, fall back to HTTP
            for scheme in ['https', 'http']:
                try:
                    response = session.head(
                        f'{scheme}://{domain}/',
                        proxies=self.proxies,
                        timeout=self.timeout,
                        headers={'User-Agent': 'Mozilla/5.0'},
                        allow_redirects=True,
                        verify=False
                    )
                    response_time_ms = int((time.time() - start_time) * 1000)

                    if response.status_code < 500:
                        return True, response_time_ms
                except Exception:
                    continue

            return False, None
        except Exception:
            return False, None

    def extract_metadata(self, html: str) -> Dict[str, Any]:
        """Extract title, description, keywords from HTML."""
        result = {
            'title': '',
            'description': '',
            'keywords': ''
        }

        if not html:
            return result

        try:
            soup = BeautifulSoup(html, 'html.parser')

            title_tag = soup.find('title')
            if title_tag and title_tag.string:
                result['title'] = title_tag.string.strip()[:200]

            meta_desc = soup.find('meta', attrs={'name': re.compile(r'^description$', re.I)})
            if meta_desc and meta_desc.get('content'):
                result['description'] = meta_desc['content'].strip()[:500]

            meta_kw = soup.find('meta', attrs={'name': re.compile(r'^keywords$', re.I)})
            if meta_kw and meta_kw.get('content'):
                result['keywords'] = meta_kw['content'].strip()[:500]

            if not result['title']:
                h1 = soup.find('h1')
                if h1 and h1.get_text():
                    result['title'] = h1.get_text().strip()[:200]

            if not result['description']:
                p = soup.find('p')
                if p and p.get_text():
                    text = p.get_text().strip()
                    if len(text) > 20:
                        result['description'] = text[:500]

        except Exception:
            pass

        return result

    def crawl_domain(self, domain: str) -> Dict[str, Any]:
        """Crawl a .onion domain and extract metadata."""
        # Try HTTPS first, then HTTP
        html = None
        response_time_ms = None

        for scheme in ['https', 'http']:
            url = f'{scheme}://{domain}/'
            html, response_time_ms = self.fetch_page(url)
            if html:
                break

        if html:
            metadata = self.extract_metadata(html)
            metadata['crawled'] = True
            metadata['reachable'] = True
            metadata['response_time_ms'] = response_time_ms
        else:
            # Fall back to quick reachability check
            reachable, response_time_ms = self.check_reachable(domain)
            metadata = {
                'title': '',
                'description': '',
                'keywords': '',
                'crawled': True,
                'reachable': reachable,
                'response_time_ms': response_time_ms
            }

        return metadata
