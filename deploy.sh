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

# Django
SECRET_KEY=$(openssl rand -hex 32)
DEBUG=False
ALLOWED_HOSTS=*

# Security
SALT=$(openssl rand -hex 16)

# API
AHMIA_API_KEY=${API_KEY}
EOF

# Run migrations
log "Running Django migrations..."
python manage.py migrate --noinput 2>/dev/null || true

# Collect static
python manage.py collectstatic --noinput 2>/dev/null || true

deactivate

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
pip install scrapy Twisted cryptography pyOpenSSL elasticsearch requests python-decouple html2text -q
deactivate

# Crawler settings
cat > "$CRAWLER_DIR/ahmia/settings_local.py" << EOF
# Elasticsearch
ELASTICSEARCH_SERVERS = ['http://127.0.0.1:9200']
ELASTICSEARCH_INDEX = 'ahmia-pages'

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
listen-address 127.0.0.1:8118
toggle 0
enable-remote-toggle 0
enable-remote-http-toggle 0
enable-edit-actions 0
buffer-limit 4096
forwarded-connect-retries 0
accept-intercepted-requests 0
allow-cgi-request-crunching 0
split-large-forms 0
keep-alive-timeout 5
tolerate-pipelining 1
socket-timeout 60
EOF

# Round-robin Tor forwarding
for i in $(seq 1 $TOR_INSTANCES); do
    TOR_PORT=$((9050 + $i - 1))
    echo "forward-socks5 .onion 127.0.0.1:${TOR_PORT} ." >> /etc/privoxy/config
done

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
supervisorctl restart all

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
