import base64
import io
import os
from typing import Optional

from .registry import register_service


@register_service('screenshot_service')
class ScreenshotService:
    """Service for capturing screenshots of .onion sites via Tor."""

    def __init__(self, tor_host: str = '127.0.0.1', tor_port: int = 9050):
        self.tor_host = tor_host
        self.tor_port = tor_port
        self.width = 1280
        self.height = 800
        self.thumb_width = 320
        self.thumb_height = 200

    def _get_driver(self):
        """Create headless Firefox driver with Tor proxy."""
        from selenium import webdriver
        from selenium.webdriver.firefox.options import Options
        from selenium.webdriver.firefox.service import Service

        options = Options()
        options.add_argument('--headless')
        options.set_preference('network.proxy.type', 1)
        options.set_preference('network.proxy.socks', self.tor_host)
        options.set_preference('network.proxy.socks_port', self.tor_port)
        options.set_preference('network.proxy.socks_remote_dns', True)
        options.set_preference('javascript.enabled', False)
        options.set_preference('permissions.default.image', 2)

        driver = webdriver.Firefox(options=options)
        driver.set_window_size(self.width, self.height)
        driver.set_page_load_timeout(30)
        return driver

    def capture(self, domain: str) -> Optional[str]:
        """Capture screenshot and return base64 PNG thumbnail."""
        driver = None
        try:
            driver = self._get_driver()
            url = f'http://{domain}/'
            driver.get(url)

            png_data = driver.get_screenshot_as_png()

            from PIL import Image
            img = Image.open(io.BytesIO(png_data))
            img.thumbnail((self.thumb_width, self.thumb_height), Image.Resampling.LANCZOS)

            buffer = io.BytesIO()
            img.save(buffer, format='PNG', optimize=True)
            buffer.seek(0)

            b64 = base64.b64encode(buffer.read()).decode('utf-8')
            return f'data:image/png;base64,{b64}'

        except Exception:
            return None

        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

    def capture_batch(self, domains: list, max_workers: int = 3) -> dict:
        """Capture screenshots for multiple domains. Returns {domain: base64_or_none}."""
        results = {}
        for domain in domains:
            results[domain] = self.capture(domain)
        return results
