# Ahmia Two-Server Deployment Guide

This guide explains how to run Ahmia on two servers: a lightweight web server and a dedicated Elasticsearch server.

## Architecture

```
┌─────────────────────────────────┐     ┌─────────────────────────────────┐
│  WEB SERVER (Server A)          │     │  ES SERVER (Server B)           │
│                                 │     │                                 │
│  - Django/Gunicorn              │     │  - Elasticsearch 8.x            │
│  - Nginx (reverse proxy)        │     │  - 8+ GB RAM recommended        │
│  - PostgreSQL/SQLite            │     │  - Ahmia crawler (optional)     │
│  - 1-2 GB RAM sufficient        │     │                                 │
│                                 │     │                                 │
│  Ports: 80, 443 (public)        │     │  Port: 9200 (private)           │
└─────────────────────────────────┘     └─────────────────────────────────┘
              │                                       │
              └───────── HTTPS (internal) ───────────┘
```

## Server A: Web Server Setup

### 1. Install Dependencies

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.10 python3.10-venv python3-pip nginx

# Clone and setup
git clone https://github.com/ahmia/ahmia-site.git
cd ahmia-site
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file in the project root:

```bash
# .env (Server A - Web Server)

# Elasticsearch - Point to Server B
ES_URL=https://YOUR_ES_SERVER_IP:9200/
ES_USERNAME=elastic
ES_PASSWORD=your_secure_password
ES_CA_CERTS=/path/to/http_ca.crt
VERIFY_CERT=True

# Django
SECRET_KEY=your-very-long-random-secret-key-here
DEBUG=False
ALLOWED_HOSTS=ahmia.fi,www.ahmia.fi,your-onion-domain.onion

# Database (optional - for PostgreSQL instead of SQLite)
# DATABASE_URL=postgres://user:pass@localhost:5432/ahmia
```

### 3. Copy ES Certificate

Copy the Elasticsearch CA certificate from Server B:

```bash
# On Server B
sudo cat /etc/elasticsearch/certs/http_ca.crt

# On Server A - save to file
sudo mkdir -p /etc/ahmia/certs
sudo nano /etc/ahmia/certs/http_ca.crt  # paste certificate
sudo chmod 644 /etc/ahmia/certs/http_ca.crt
```

Update `.env`:
```
ES_CA_CERTS=/etc/ahmia/certs/http_ca.crt
```

### 4. Run Migrations

```bash
source venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput

# Seed profile categories
python manage.py seed_categories
```

### 5. Configure Gunicorn

Create `/etc/systemd/system/ahmia.service`:

```ini
[Unit]
Description=Ahmia Django Application
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/ahmia-site
Environment="PATH=/var/www/ahmia-site/venv/bin"
EnvironmentFile=/var/www/ahmia-site/.env
ExecStart=/var/www/ahmia-site/venv/bin/gunicorn \
    --workers 3 \
    --bind unix:/run/ahmia.sock \
    ahmia.wsgi:application

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable ahmia
sudo systemctl start ahmia
```

### 6. Configure Nginx

Create `/etc/nginx/sites-available/ahmia`:

```nginx
server {
    listen 80;
    server_name ahmia.fi www.ahmia.fi;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ahmia.fi www.ahmia.fi;

    ssl_certificate /etc/letsencrypt/live/ahmia.fi/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ahmia.fi/privkey.pem;

    location /static/ {
        alias /var/www/ahmia-site/static/;
    }

    location / {
        proxy_pass http://unix:/run/ahmia.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/ahmia /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## Server B: Elasticsearch Setup

### 1. Install Elasticsearch

```bash
# Import Elasticsearch GPG key
wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo gpg --dearmor -o /usr/share/keyrings/elasticsearch-keyring.gpg

# Add repository
echo "deb [signed-by=/usr/share/keyrings/elasticsearch-keyring.gpg] https://artifacts.elastic.co/packages/8.x/apt stable main" | sudo tee /etc/apt/sources.list.d/elastic-8.x.list

# Install
sudo apt update
sudo apt install elasticsearch
```

### 2. Configure Elasticsearch

Edit `/etc/elasticsearch/elasticsearch.yml`:

```yaml
# Cluster name
cluster.name: ahmia-cluster
node.name: ahmia-es-1

# Network - bind to private IP for remote access
network.host: 0.0.0.0
http.port: 9200

# Security
xpack.security.enabled: true
xpack.security.transport.ssl.enabled: true
xpack.security.http.ssl.enabled: true
xpack.security.http.ssl.keystore.path: certs/http.p12

# Memory - adjust based on your RAM (50% of total, max 32g)
# Set in /etc/elasticsearch/jvm.options.d/heap.options
```

Create `/etc/elasticsearch/jvm.options.d/heap.options`:

```
# For 16GB RAM server, use 8GB heap
-Xms8g
-Xmx8g

# For 8GB RAM server, use 4GB heap
# -Xms4g
# -Xmx4g
```

### 3. Firewall - Allow Only Web Server

```bash
# Ubuntu UFW
sudo ufw allow from YOUR_WEB_SERVER_IP to any port 9200
sudo ufw deny 9200
sudo ufw enable

# Or iptables
sudo iptables -A INPUT -p tcp -s YOUR_WEB_SERVER_IP --dport 9200 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 9200 -j DROP
```

### 4. Start Elasticsearch

```bash
sudo systemctl enable elasticsearch
sudo systemctl start elasticsearch

# Get the elastic user password (shown on first start)
sudo /usr/share/elasticsearch/bin/elasticsearch-reset-password -u elastic
```

### 5. Create Ahmia Index

```bash
curl -X PUT "https://localhost:9200/latest-tor" \
  -u elastic:YOUR_PASSWORD \
  --cacert /etc/elasticsearch/certs/http_ca.crt \
  -H 'Content-Type: application/json' \
  -d '{
    "settings": {
      "number_of_shards": 1,
      "number_of_replicas": 0
    },
    "mappings": {
      "properties": {
        "domain": { "type": "keyword" },
        "url": { "type": "keyword" },
        "title": { "type": "text", "fields": {"keyword": {"type": "keyword"}} },
        "meta": { "type": "text", "fields": {"keyword": {"type": "keyword"}} },
        "content": { "type": "text" },
        "updated_on": { "type": "date" },
        "is_banned": { "type": "boolean" }
      }
    }
  }'
```

---

## Testing the Connection

From Server A (web server):

```bash
# Test ES connection
curl -u elastic:YOUR_PASSWORD \
  --cacert /etc/ahmia/certs/http_ca.crt \
  https://YOUR_ES_SERVER_IP:9200/_cluster/health

# Test Django can reach ES
source venv/bin/activate
python manage.py shell
>>> from ahmia.views import es_client
>>> es_client.info()
```

---

## Cost Estimates

| Provider | Web Server (1-2GB) | ES Server (8GB) | Total/month |
|----------|-------------------|-----------------|-------------|
| DigitalOcean | $6 (1GB) | $48 (8GB) | ~$54 |
| Vultr | $6 (1GB) | $48 (8GB) | ~$54 |
| Hetzner | €4 (2GB) | €15 (8GB) | ~€19 |
| Contabo | $7 (4GB) | $15 (16GB) | ~$22 |

**Tip:** Hetzner or Contabo offer the best value for RAM-heavy workloads like Elasticsearch.

---

## Optional: Managed Elasticsearch

Instead of running your own ES server, use a managed service:

| Service | Free Tier | Paid |
|---------|-----------|------|
| Elastic Cloud | 14-day trial | From $95/mo |
| AWS OpenSearch | 750 hrs/mo free tier | From $25/mo |
| Bonsai | 10k docs free | From $10/mo |

For Bonsai (cheap option):
```
ES_URL=https://user:pass@your-cluster.bonsaisearch.net:443/
VERIFY_CERT=True
ES_CA_CERTS=  # Leave empty for public CA
```

---

## Sync Profiles from Elasticsearch

Once both servers are running:

```bash
# On Server A
source venv/bin/activate

# Generate profiles from crawled domains
python manage.py sync_profiles

# Update stats periodically (add to cron)
python manage.py update_stats
```

Add to crontab:
```bash
# Update profile stats daily at 3am
0 3 * * * cd /var/www/ahmia-site && venv/bin/python manage.py update_stats
```
