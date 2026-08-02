#!/bin/bash
#
# Ahmia Tor Search Platform - One-Click Deploy Script
# Deploys: Elasticsearch + Django API + Scrapy Crawler + Tor Fleet
#
# Usage: ./deploy.sh [API_KEY]
#   If API_KEY not provided, generates random one
#
# Requirements: Ubuntu 22.04+ with root access
# Tested on: DigitalOcean 4GB RAM droplet
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')] WARNING:${NC} $1"; }
error() { echo -e "${RED}[$(date '+%H:%M:%S')] ERROR:${NC} $1"; exit 1; }

# Configuration
API_KEY="${1:-$(openssl rand -hex 32)}"
AHMIA_DIR="/opt/ahmia"
CRAWLER_DIR="/opt/ahmia-crawler"
TOR_INSTANCES=5
ES_HEAP="512m"
REPO_URL="https://github.com/seven2082/ahmia-crawler-carder.git"

log "Starting Ahmia Tor Search Platform deployment..."
log "API Key: $API_KEY"

# Check root
[[ $EUID -ne 0 ]] && error "Must run as root"

# System updates
log "Updating system packages..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get upgrade -y -qq

# Install dependencies
log "Installing dependencies..."
apt-get install -y -qq \
    python3 python3-pip python3-venv \
    git curl wget gnupg2 \
    supervisor nginx \
    tor privoxy \
    openjdk-17-jre-headless

# Install Elasticsearch
log "Installing Elasticsearch 8.x..."
if ! dpkg -l | grep -q elasticsearch; then
    wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | gpg --dearmor -o /usr/share/keyrings/elasticsearch-keyring.gpg 2>/dev/null || true
    echo "deb [signed-by=/usr/share/keyrings/elasticsearch-keyring.gpg] https://artifacts.elastic.co/packages/8.x/apt stable main" > /etc/apt/sources.list.d/elastic-8.x.list
    apt-get update -qq
    apt-get install -y -qq elasticsearch
fi

# Configure Elasticsearch (reduced memory, security disabled for local-only)
log "Configuring Elasticsearch..."
mkdir -p /etc/elasticsearch/jvm.options.d
cat > /etc/elasticsearch/jvm.options.d/heap.options << EOF
-Xms${ES_HEAP}
-Xmx${ES_HEAP}
EOF

cat > /etc/elasticsearch/elasticsearch.yml << 'EOF'
cluster.name: ahmia
node.name: ahmia-node-1
path.data: /var/lib/elasticsearch
path.logs: /var/log/elasticsearch
network.host: 127.0.0.1
http.port: 9200
xpack.security.enabled: false
xpack.security.enrollment.enabled: false
xpack.security.http.ssl.enabled: false
xpack.security.transport.ssl.enabled: false
EOF

chown -R elasticsearch:elasticsearch /etc/elasticsearch
chown -R elasticsearch:elasticsearch /var/lib/elasticsearch
chown -R elasticsearch:elasticsearch /var/log/elasticsearch

systemctl daemon-reload
systemctl enable elasticsearch
systemctl start elasticsearch

# Wait for Elasticsearch
log "Waiting for Elasticsearch to start..."
for i in {1..60}; do
    if curl -s http://localhost:9200 > /dev/null 2>&1; then
        log "Elasticsearch is running"
        break
    fi
    if [[ $i -eq 60 ]]; then
        error "Elasticsearch failed to start. Check: journalctl -u elasticsearch"
    fi
    sleep 2
done

# Clone Ahmia site from GitHub
log "Cloning Ahmia site from GitHub..."
rm -rf "$AHMIA_DIR"
git clone --depth 1 "$REPO_URL" "$AHMIA_DIR"

cd "$AHMIA_DIR"

# Python venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
pip install gunicorn -q

# Ahmia configuration (HTTP ES - no SSL)
cat > "$AHMIA_DIR/ahmia/.env" << EOF
# Elasticsearch (local HTTP, no auth)
ES_URL=http://127.0.0.1:9200/
ES_USERNAME=
ES_PASSWORD=
ES_CA_CERTS=
VERIFY_CERT=False
ELASTICSEARCH_TIMEOUT=60
ELASTICSEARCH_INDEX=ahmia-pages

# Django
SECRET_KEY=$(openssl rand -hex 32)
DEBUG=False
ALLOWED_HOSTS=*

# Security
SALT=$(openssl rand -hex 16)

# API
AHMIA_API_KEY=${API_KEY}
EOF

# Fix settings.py to use ahmia-pages index
sed -i "s/ELASTICSEARCH_INDEX = 'latest-tor'/ELASTICSEARCH_INDEX = config('ELASTICSEARCH_INDEX', default='ahmia-pages')/" "$AHMIA_DIR/ahmia/settings.py"

# Run migrations
log "Running Django migrations..."
python manage.py migrate --noinput 2>/dev/null || true

# Collect static
python manage.py collectstatic --noinput 2>/dev/null || true

# Seed categories
log "Seeding profile categories..."
python manage.py seed_categories 2>/dev/null || true

deactivate

# Patch elasticsearch_service.py for HTTP (no SSL)
log "Patching elasticsearch_service.py for HTTP..."
cat > "$AHMIA_DIR/profiles/services/elasticsearch_service.py" << 'ES_SERVICE_EOF'
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
ES_SERVICE_EOF

# Create Elasticsearch index
log "Creating Elasticsearch index..."
curl -s -X PUT "http://localhost:9200/ahmia-pages" -H 'Content-Type: application/json' -d '{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "index.mapping.total_fields.limit": 2000
  },
  "mappings": {
    "properties": {
      "domain": { "type": "keyword" },
      "url": { "type": "keyword" },
      "title": { "type": "text", "analyzer": "standard" },
      "content": { "type": "text", "analyzer": "standard" },
      "content_type": { "type": "keyword" },
      "updated_on": { "type": "date" },
      "crawled_on": { "type": "date" },
      "status": { "type": "keyword" },
      "h1": { "type": "text" },
      "description": { "type": "text" },
      "keywords": { "type": "text" },
      "links": { "type": "keyword" }
    }
  }
}' 2>/dev/null || true

echo ""

# Clone Crawler from upstream
log "Setting up Ahmia Crawler..."
rm -rf "$CRAWLER_DIR"
git clone --depth 1 https://github.com/ahmia/ahmia-crawler.git "$CRAWLER_DIR" 2>/dev/null

cd "$CRAWLER_DIR"

# Crawler venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install scrapy Twisted cryptography pyOpenSSL "elasticsearch>=8.0.0,<9.0.0" requests python-decouple html2text -q
deactivate

# Crawler settings
cat > "$CRAWLER_DIR/ahmia/settings_local.py" << EOF
# Elasticsearch - HTTP no auth
ELASTICSEARCH_SERVER = 'http://127.0.0.1:9200'
ELASTICSEARCH_SERVERS = ['http://127.0.0.1:9200']
ELASTICSEARCH_INDEX = 'ahmia-pages'
ELASTICSEARCH_USERNAME = ''
ELASTICSEARCH_PASSWORD = ''

# Tor proxy (via Privoxy)
HTTP_PROXY = 'http://127.0.0.1:8118'
HTTPS_PROXY = 'http://127.0.0.1:8118'

# Crawl settings
CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 4
DOWNLOAD_DELAY = 1
RANDOMIZE_DOWNLOAD_DELAY = True
DOWNLOAD_TIMEOUT = 30
RETRY_TIMES = 2

LOG_LEVEL = 'INFO'
COOKIES_ENABLED = False
TELNETCONSOLE_ENABLED = False
EOF

# Patch pipelines.py for HTTP ES (no SSL)
cat > "$CRAWLER_DIR/ahmia/ahmia/pipelines.py" << 'PIPELINES_EOF'
# -*- coding: utf-8 -*-
"""Pipelines - Patched for HTTP Elasticsearch"""
import hashlib
import logging
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from .items import DocumentItem

logger = logging.getLogger(__name__)

class CustomElasticSearchPipeline:
    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def __init__(self, settings):
        self.settings = settings
        self.items_buffer = []

        es_server = settings.get("ELASTICSEARCH_SERVER", "http://127.0.0.1:9200")
        es_servers = settings.getlist("ELASTICSEARCH_SERVERS", [])
        if es_servers:
            es_server = es_servers[0]

        es_user = settings.get("ELASTICSEARCH_USERNAME", "")
        es_pass = settings.get("ELASTICSEARCH_PASSWORD", "")

        use_ssl = es_server.startswith("https://")

        if es_user and es_pass and use_ssl:
            self.es = Elasticsearch(
                hosts=[es_server],
                basic_auth=(es_user, es_pass),
                verify_certs=False,
                ssl_show_warn=False,
                max_retries=5,
                request_timeout=60,
            )
        elif use_ssl:
            self.es = Elasticsearch(
                hosts=[es_server],
                verify_certs=False,
                ssl_show_warn=False,
                max_retries=5,
                request_timeout=60,
            )
        else:
            self.es = Elasticsearch(
                hosts=[es_server],
                max_retries=5,
                request_timeout=60,
            )

        self.index_name = self.settings.get("ELASTICSEARCH_INDEX", "ahmia-pages")
        logger.info(f"Connecting to ES: {es_server}")
        try:
            logger.info(f"Elasticsearch available: {self.es.info()}")
        except Exception as e:
            logger.error(f"ES connection failed: {e}")

    def process_item(self, item):
        self.index_item(item)
        return item

    def index_item(self, item):
        doc_id = hashlib.sha1(item["url"].encode("utf-8")).hexdigest()

        if isinstance(item, DocumentItem):
            action = {
                "_index": self.index_name,
                "_id": doc_id,
                "_source": dict(item)
            }
        else:
            logger.error(f"Unknown item type: {item.__class__.__name__}")
            return

        self.items_buffer.append(action)

        if len(self.items_buffer) >= self.settings.get("ELASTICSEARCH_BUFFER_LENGTH", 100):
            self.send_items()

    def send_items(self):
        try:
            success, _ = bulk(self.es, self.items_buffer,
                              index=self.index_name,
                              raise_on_error=True)
            logger.info(f"Successfully indexed {success} items.")
        except Exception as e:
            logger.error(f"Error indexing items: {e}")
        finally:
            self.items_buffer = []

    def close_spider(self, spider):
        if self.items_buffer:
            self.send_items()
PIPELINES_EOF

# Custom middleware for Tor proxy
cat > "$CRAWLER_DIR/ahmia/ahmia/middlewares.py" << 'MIDDLEWARE_EOF'
# -*- coding: utf-8 -*-
"""Custom middlewares for Ahmia crawler"""
import logging

logger = logging.getLogger(__name__)

class TorProxyMiddleware:
    """Middleware to route all requests through Tor proxy"""

    def __init__(self):
        self.proxy = "http://127.0.0.1:8118"
        logger.info(f"TorProxyMiddleware initialized with proxy: {self.proxy}")

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_request(self, request, spider):
        request.meta["proxy"] = self.proxy
        request.meta["download_timeout"] = 60
        return None
MIDDLEWARE_EOF

# Custom settings.py with local seedlist support
cat > "$CRAWLER_DIR/ahmia/ahmia/settings.py" << 'SETTINGS_EOF'
# -*- coding: utf-8 -*-
"""Scrapy settings - Local config with Tor proxy"""
import os

BOT_NAME = "ahmia"
SPIDER_MODULES = ["ahmia.spiders"]
NEWSPIDER_MODULE = "ahmia.spiders"

ROBOTSTXT_OBEY = False
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/115.0"

# Middleware - our custom Tor proxy injector
DOWNLOADER_MIDDLEWARES = {
    "ahmia.middlewares.TorProxyMiddleware": 100,
}

# Elasticsearch
ITEM_PIPELINES = {
    "ahmia.pipelines.CustomElasticSearchPipeline": 300,
}

# Crawl settings
CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 2
DOWNLOAD_DELAY = 2
RANDOMIZE_DOWNLOAD_DELAY = True
DOWNLOAD_TIMEOUT = 60
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

LOG_LEVEL = "INFO"
COOKIES_ENABLED = False
TELNETCONSOLE_ENABLED = False

# Memory
MEMUSAGE_ENABLED = True
MEMUSAGE_LIMIT_MB = 512
MEMUSAGE_WARNING_MB = 400

# Load local seedlist
SEEDLIST = []
seedlist_path = os.path.join(os.path.dirname(__file__), "seedlist.txt")
if os.path.exists(seedlist_path):
    with open(seedlist_path, "r") as f:
        for line in f:
            url = line.strip()
            if url and url.startswith("http"):
                SEEDLIST.append(url)

print(f"\n settings.py loaded: SEEDLIST with {len(SEEDLIST)} onion addresses\n")

# Import local settings
try:
    from settings_local import *
except ImportError:
    pass
SETTINGS_EOF

# Fetch initial seedlist from ahmia.fi onion
log "Fetching initial seedlist..."
cat > "$CRAWLER_DIR/ahmia/ahmia/seedlist.txt" << 'SEEDLIST_EOF'
http://juhanurmihxlp77nkq76byazcldy2hlmovfu2epvl5ankdibsot4csyd.onion/
http://duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion/
SEEDLIST_EOF

# Setup Tor fleet
log "Setting up Tor fleet (${TOR_INSTANCES} instances)..."
systemctl stop tor 2>/dev/null || true
mkdir -p /var/log/tor
chown debian-tor:debian-tor /var/log/tor

for i in $(seq 1 $TOR_INSTANCES); do
    TOR_PORT=$((9050 + $i - 1))
    CONTROL_PORT=$((9150 + $i - 1))
    DATA_DIR="/var/lib/tor${i}"

    rm -rf "$DATA_DIR"
    mkdir -p "$DATA_DIR"
    chown debian-tor:debian-tor "$DATA_DIR"
    chmod 700 "$DATA_DIR"

    cat > "/etc/tor/torrc.${i}" << EOF
SocksPort ${TOR_PORT}
ControlPort ${CONTROL_PORT}
DataDirectory ${DATA_DIR}
Log notice file /var/log/tor/tor${i}.log
RunAsDaemon 0
EOF
    chown debian-tor:debian-tor "/etc/tor/torrc.${i}"
done

# Setup Privoxy
log "Configuring Privoxy..."
systemctl stop privoxy 2>/dev/null || true

# Disable AppArmor for privoxy if blocking
if command -v aa-status &> /dev/null; then
    if aa-status 2>/dev/null | grep -q privoxy; then
        aa-disable /usr/sbin/privoxy 2>/dev/null || true
    fi
fi

cat > /etc/privoxy/config << EOF
# Privoxy config for Ahmia crawler
listen-address 127.0.0.1:8118
toggle 0
enable-remote-toggle 0
enable-remote-http-toggle 0
enable-edit-actions 0
buffer-limit 4096

# Forward ALL traffic through Tor SOCKS5 (primary instance)
# This ensures .onion DNS resolution works properly
forward-socks5t / 127.0.0.1:9050 .
EOF

# Supervisor configuration
log "Configuring Supervisor..."
rm -f /etc/supervisor/conf.d/ahmia.conf

cat > /etc/supervisor/conf.d/ahmia.conf << EOF
[program:ahmia-web]
command=${AHMIA_DIR}/venv/bin/gunicorn ahmia.wsgi:application -b 127.0.0.1:8000 -w 2 --timeout 120
directory=${AHMIA_DIR}
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/ahmia-web.log
environment=AHMIA_API_KEY="${API_KEY}"

[program:privoxy]
command=/usr/sbin/privoxy --no-daemon /etc/privoxy/config
user=privoxy
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/privoxy.log
EOF

# Tor instances in supervisor
for i in $(seq 1 $TOR_INSTANCES); do
    cat >> /etc/supervisor/conf.d/ahmia.conf << EOF

[program:tor${i}]
command=/usr/bin/tor -f /etc/tor/torrc.${i}
user=debian-tor
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/tor${i}.log
EOF
done

# Crawler supervisor
cat >> /etc/supervisor/conf.d/ahmia.conf << EOF

[program:ahmia-crawler]
command=${CRAWLER_DIR}/venv/bin/scrapy crawl ahmia-tor
directory=${CRAWLER_DIR}/ahmia
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/ahmia-crawler.log
startsecs=30
stopwaitsecs=30
EOF

# Nginx configuration
log "Configuring Nginx..."
cat > /etc/nginx/sites-available/ahmia << 'EOF'
server {
    listen 80 default_server;
    server_name _;

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
    }

    location /static/ {
        alias /opt/ahmia/static/;
        expires 30d;
    }
}
EOF

rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/ahmia /etc/nginx/sites-enabled/

nginx -t || error "Nginx config test failed"

# Set permissions
chown -R www-data:www-data "$AHMIA_DIR"
chown -R www-data:www-data "$CRAWLER_DIR"

# Start services
log "Starting all services..."
systemctl restart nginx
supervisorctl reread
supervisorctl update
sleep 3
supervisorctl restart all || true

# Wait and verify
log "Waiting for services to stabilize..."
sleep 15

log "Verifying deployment..."
echo ""
echo "============================================"
echo "Service Status:"
echo "============================================"

FAILED=0

# Check Elasticsearch
if curl -s http://localhost:9200 > /dev/null 2>&1; then
    echo -e "Elasticsearch:  ${GREEN}RUNNING${NC}"
else
    echo -e "Elasticsearch:  ${RED}FAILED${NC}"
    FAILED=1
fi

# Check Ahmia web
if curl -s http://localhost:8000 > /dev/null 2>&1; then
    echo -e "Ahmia Web:      ${GREEN}RUNNING${NC}"
else
    echo -e "Ahmia Web:      ${RED}FAILED${NC}"
    FAILED=1
fi

# Check Tor instances
TOR_RUNNING=0
for i in $(seq 1 $TOR_INSTANCES); do
    if supervisorctl status tor${i} 2>/dev/null | grep -q RUNNING; then
        ((TOR_RUNNING++))
    fi
done
if [[ $TOR_RUNNING -eq $TOR_INSTANCES ]]; then
    echo -e "Tor Fleet:      ${GREEN}${TOR_RUNNING}/${TOR_INSTANCES} RUNNING${NC}"
else
    echo -e "Tor Fleet:      ${YELLOW}${TOR_RUNNING}/${TOR_INSTANCES} RUNNING${NC}"
fi

# Check Privoxy
if supervisorctl status privoxy 2>/dev/null | grep -q RUNNING; then
    echo -e "Privoxy:        ${GREEN}RUNNING${NC}"
else
    echo -e "Privoxy:        ${RED}FAILED${NC}"
    FAILED=1
fi

# Check Crawler
CRAWLER_STATUS=$(supervisorctl status ahmia-crawler 2>/dev/null)
if echo "$CRAWLER_STATUS" | grep -q RUNNING; then
    echo -e "Crawler:        ${GREEN}RUNNING${NC}"
elif echo "$CRAWLER_STATUS" | grep -q STARTING; then
    echo -e "Crawler:        ${YELLOW}STARTING...${NC}"
else
    echo -e "Crawler:        ${RED}FAILED${NC}"
    FAILED=1
fi

# Check Nginx
if systemctl is-active nginx > /dev/null 2>&1; then
    echo -e "Nginx:          ${GREEN}RUNNING${NC}"
else
    echo -e "Nginx:          ${RED}FAILED${NC}"
    FAILED=1
fi

# Get public IP
PUBLIC_IP=$(curl -s --connect-timeout 5 ifconfig.me 2>/dev/null || curl -s --connect-timeout 5 icanhazip.com 2>/dev/null || echo 'YOUR_IP')

echo ""
echo "============================================"
if [[ $FAILED -eq 0 ]]; then
    echo -e "${GREEN}Deployment Complete!${NC}"
else
    echo -e "${YELLOW}Deployment Complete (with warnings)${NC}"
fi
echo "============================================"
echo ""
echo "API URL:     http://${PUBLIC_IP}/api/v1"
echo "API Key:     ${API_KEY}"
echo ""
echo "Test commands:"
echo "  curl http://localhost:9200/_cat/indices"
echo "  curl -H 'X-API-Key: ${API_KEY}' http://localhost/api/v1/stats/"
echo ""
echo "Monitor:"
echo "  tail -f /var/log/ahmia-crawler.log"
echo "  tail -f /var/log/ahmia-web.log"
echo "  supervisorctl status"
echo ""
echo "Check indexed pages:"
echo "  curl 'http://localhost:9200/ahmia-pages/_count'"
echo ""
echo "============================================"
echo "XenForo AhmiaSync Options:"
echo "============================================"
echo "  API URL: http://${PUBLIC_IP}/api/v1"
echo "  API Key: ${API_KEY}"
echo ""

# Save credentials
cat > /root/ahmia-credentials.txt << EOF
Ahmia Tor Search Platform Credentials
======================================
Generated: $(date)

API URL: http://${PUBLIC_IP}/api/v1
API Key: ${API_KEY}

Elasticsearch: http://127.0.0.1:9200 (local only, no auth)

Logs:
  /var/log/ahmia-web.log
  /var/log/ahmia-crawler.log
  /var/log/tor*.log
  /var/log/privoxy.log

Commands:
  supervisorctl status
  supervisorctl restart all
  curl http://localhost:9200/ahmia-pages/_count
EOF

chmod 600 /root/ahmia-credentials.txt
echo "Credentials saved to: /root/ahmia-credentials.txt"

# Create deploy-pull.sh
log "Creating deploy scripts..."
mkdir -p "$AHMIA_DIR/logs"

cat > "$AHMIA_DIR/deploy-pull.sh" << 'DEPLOY_EOF'
#!/bin/bash
set -e

BRANCH="main"
PROJECT_DIR="/opt/ahmia"
CRAWLER_DIR="/opt/ahmia-crawler"
LOG_DIR="${LOG_DIR:-$PROJECT_DIR/logs}"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/deploy.log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo ""
echo "=== Deploy started at $TIMESTAMP ==="

echo "[1/7] Pulling latest code..."
cd "$PROJECT_DIR"
git stash 2>/dev/null || true
git pull origin "$BRANCH"

echo "[2/7] Activating venv..."
source "$PROJECT_DIR/venv/bin/activate"

echo "[3/7] Installing Python dependencies..."
pip install -r requirements.txt -q

echo "[4/7] Running migrations..."
python manage.py migrate --noinput

echo "[5/7] Collecting static files..."
python manage.py collectstatic --noinput 2>/dev/null || true

deactivate

echo "[6/7] Updating crawler..."
cd "$CRAWLER_DIR"
git stash 2>/dev/null || true
git pull origin master 2>/dev/null || true
source "$CRAWLER_DIR/venv/bin/activate"
pip install -q scrapy Twisted cryptography pyOpenSSL elasticsearch requests python-decouple html2text
deactivate

echo "[7/7] Restarting services..."
supervisorctl restart ahmia-web
supervisorctl restart ahmia-crawler

echo "=== Deploy completed at $(date '+%Y-%m-%d %H:%M:%S') ==="
echo ""
DEPLOY_EOF

chmod +x "$AHMIA_DIR/deploy-pull.sh"

# Create auto-deploy.sh
cat > "$AHMIA_DIR/auto-deploy.sh" << 'AUTO_EOF'
#!/bin/bash
set -e

BRANCH="main"
PROJECT_DIR="/opt/ahmia"
LOG_DIR="${LOG_DIR:-$PROJECT_DIR/logs}"

mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/auto-deploy.log"

cd "$PROJECT_DIR"

git fetch origin "$BRANCH" --quiet

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse "origin/$BRANCH")

if [ "$LOCAL" = "$REMOTE" ]; then
    exit 0
fi

echo "" >> "$LOG_FILE"
echo "=== Auto-deploy started at $(date '+%Y-%m-%d %H:%M:%S') ===" >> "$LOG_FILE"
echo "Local:  $LOCAL" >> "$LOG_FILE"
echo "Remote: $REMOTE" >> "$LOG_FILE"

exec >> "$LOG_FILE" 2>&1

git stash 2>/dev/null || true
git pull origin "$BRANCH"

source "$PROJECT_DIR/venv/bin/activate"

if git diff HEAD@{1} --name-only 2>/dev/null | grep -q "requirements.txt"; then
    echo "Installing updated dependencies..."
    pip install -r requirements.txt -q
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput 2>/dev/null || true

deactivate

supervisorctl restart ahmia-web
supervisorctl restart ahmia-crawler

echo "=== Auto-deploy completed at $(date '+%Y-%m-%d %H:%M:%S') ==="
AUTO_EOF

chmod +x "$AHMIA_DIR/auto-deploy.sh"

# Setup cron for auto-deploy (every 2 minutes)
log "Setting up auto-deploy cron..."
CRON_JOB="*/2 * * * * /bin/bash $AHMIA_DIR/auto-deploy.sh 2>&1"

# Remove existing ahmia cron entries and add new one
(crontab -l 2>/dev/null | grep -v "auto-deploy.sh" || true; echo "$CRON_JOB") | crontab -

echo ""
echo "============================================"
echo "Auto-Deploy Configured:"
echo "============================================"
echo "  Manual:  bash $AHMIA_DIR/deploy-pull.sh"
echo "  Auto:    Cron runs every 2 minutes"
echo "  Logs:    tail -f $AHMIA_DIR/logs/auto-deploy.log"
echo ""
echo "Verify cron:"
echo "  crontab -l"
echo ""
