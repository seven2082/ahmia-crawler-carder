#!/bin/bash
#
# Reset server to clean state before fresh deploy
#

set -e

echo "Stopping all services..."
supervisorctl stop all 2>/dev/null || true
systemctl stop nginx 2>/dev/null || true
systemctl stop elasticsearch 2>/dev/null || true
systemctl stop tor 2>/dev/null || true
systemctl stop privoxy 2>/dev/null || true

echo "Removing Ahmia installations..."
rm -rf /opt/ahmia
rm -rf /opt/ahmia-crawler

echo "Removing Tor data..."
rm -rf /var/lib/tor[0-9]*
rm -f /etc/tor/torrc.[0-9]*

echo "Removing Elasticsearch data..."
rm -rf /var/lib/elasticsearch/*

echo "Removing configs..."
rm -f /etc/supervisor/conf.d/ahmia.conf
rm -f /etc/nginx/sites-enabled/ahmia
rm -f /etc/nginx/sites-available/ahmia

echo "Removing logs..."
rm -f /var/log/ahmia-*.log
rm -f /var/log/tor*.log
rm -f /var/log/privoxy.log

echo "Reloading supervisor..."
supervisorctl reread 2>/dev/null || true
supervisorctl update 2>/dev/null || true

echo ""
echo "Server reset complete. Ready for fresh deploy."
echo "Run: bash deploy.sh"
