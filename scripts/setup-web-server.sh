#!/bin/bash
# Ahmia Web Server Setup Script
# Run this on Server A (the lightweight web server)

set -e

echo "=== Ahmia Web Server Setup ==="
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found!"
    echo "Copy .env.example to .env and configure it first:"
    echo "  cp .env.example .env"
    echo "  nano .env"
    exit 1
fi

# Create virtual environment if needed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate and install dependencies
echo "Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Run migrations
echo "Running database migrations..."
python manage.py migrate

# Seed categories for profiles
echo "Seeding profile categories..."
python manage.py seed_categories

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Test ES connection
echo ""
echo "Testing Elasticsearch connection..."
python -c "
from ahmia.views import es_client
try:
    info = es_client.info()
    print('SUCCESS: Connected to Elasticsearch')
    print(f'  Cluster: {info[\"cluster_name\"]}')
    print(f'  Version: {info[\"version\"][\"number\"]}')
except Exception as e:
    print(f'WARNING: Could not connect to Elasticsearch: {e}')
    print('  Search will not work until ES is configured correctly.')
"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Configure Nginx (see docs/DEPLOYMENT.md)"
echo "  2. Set up systemd service for Gunicorn"
echo "  3. Run: python manage.py sync_profiles (to generate profiles from ES)"
echo ""
echo "To run development server:"
echo "  source venv/bin/activate"
echo "  python manage.py runserver"
