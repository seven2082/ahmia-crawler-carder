import re
import socket
import time
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlparse
import socks
from bs4 import BeautifulSoup

from .registry import register_service


@register_service('crawler_service')
class CrawlerService:
    """Service for crawling .onion sites to extract metadata."""

    def __init__(self, tor_host: str = '127.0.0.1', tor_port: int = 9050, timeout: int = 15):
        self.tor_host = tor_host
        self.tor_port = tor_port
        self.timeout = timeout

    def _create_tor_socket(self):
        """Create a socket that routes through Tor SOCKS proxy."""
        s = socks.socksocket()
        s.set_proxy(socks.SOCKS5, self.tor_host, self.tor_port)
        s.settimeout(self.timeout)
        return s

    def fetch_page(self, url: str) -> Tuple[Optional[str], Optional[int]]:
        """Fetch page HTML via Tor. Returns (html, response_time_ms)."""
        try:
            parsed = urlparse(url)
            host = parsed.netloc or parsed.path.split('/')[0]
            port = 80
            path = parsed.path or '/'
            if not path.startswith('/'):
                path = '/' + path

            start_time = time.time()
            sock = self._create_tor_socket()
            sock.connect((host, port))

            request = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\nUser-Agent: Mozilla/5.0\r\n\r\n"
            sock.send(request.encode())

            response = b''
            while True:
                chunk = sock.recv(8192)
                if not chunk:
                    break
                response += chunk
                if len(response) > 1024 * 1024:  # 1MB limit
                    break

            sock.close()
            response_time_ms = int((time.time() - start_time) * 1000)

            try:
                header_end = response.find(b'\r\n\r\n')
                if header_end > 0:
                    body = response[header_end + 4:]
                else:
                    body = response

                try:
                    return body.decode('utf-8', errors='replace'), response_time_ms
                except:
                    return body.decode('latin-1', errors='replace'), response_time_ms
            except:
                return None, None

        except Exception:
            return None, None

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
        url = f'http://{domain}/'
        html, response_time_ms = self.fetch_page(url)

        if html:
            metadata = self.extract_metadata(html)
            metadata['crawled'] = True
            metadata['reachable'] = True
            metadata['response_time_ms'] = response_time_ms
        else:
            metadata = {
                'title': '',
                'description': '',
                'keywords': '',
                'crawled': True,
                'reachable': False,
                'response_time_ms': None
            }

        return metadata
