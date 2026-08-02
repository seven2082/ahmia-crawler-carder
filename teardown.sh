#!/bin/bash
#
# Ahmia Tor Search Platform - Teardown Script
# Stops all services and optionally exports data before server destruction
#
# Usage: ./teardown.sh [--export]
#   --export: Backup Elasticsearch data before stopping
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"; }

EXPORT_DATA=false
[[ "$1" == "--export" ]] && EXPORT_DATA=true

log "Stopping Ahmia Tor Search Platform..."

# Export data if requested
if $EXPORT_DATA; then
    log "Exporting Elasticsearch data..."
    EXPORT_FILE="/tmp/ahmia-export-$(date +%Y%m%d-%H%M%S).json"

    # Get total docs
    TOTAL=$(curl -s 'http://localhost:9200/ahmia-pages/_count' | grep -o '"count":[0-9]*' | cut -d: -f2)
    log "Exporting ${TOTAL} documents..."

    # Export using scroll API
    curl -s -X POST "http://localhost:9200/ahmia-pages/_search?scroll=5m" \
        -H 'Content-Type: application/json' \
        -d '{"size": 10000, "query": {"match_all": {}}}' > "$EXPORT_FILE"

    log "Data exported to: $EXPORT_FILE"
    ls -lh "$EXPORT_FILE"
fi

# Stop supervisor services
log "Stopping supervisor services..."
supervisorctl stop all 2>/dev/null || true

# Stop system services
log "Stopping system services..."
systemctl stop nginx 2>/dev/null || true
systemctl stop elasticsearch 2>/dev/null || true
systemctl stop supervisor 2>/dev/null || true

# Show final stats
log "Final Statistics:"
if [[ -f /var/log/ahmia-crawler.log ]]; then
    PAGES=$(grep -c "Stored page" /var/log/ahmia-crawler.log 2>/dev/null || echo "0")
    echo "  Pages crawled this session: $PAGES"
fi

echo ""
echo -e "${GREEN}Teardown complete. Server ready for destruction.${NC}"
echo ""
if $EXPORT_DATA; then
    echo "Don't forget to download: $EXPORT_FILE"
fi
