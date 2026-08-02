# Getting Started with Ahmia

This guide will help you set up Ahmia for local development.

## Prerequisites

- Python 3.10 or higher
- Git
- Elasticsearch 8.x (local or remote)

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/ahmia/ahmia-site.git
cd ahmia-site
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate   # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```bash
# Minimum required settings
ES_URL=https://localhost:9200/
ES_USERNAME=elastic
ES_PASSWORD=your_password
DEBUG=True
```

### 5. Run Migrations

```bash
python manage.py migrate
```

### 6. Seed Initial Data

```bash
# Create default categories for profiles
python manage.py seed_categories
```

### 7. Start Development Server

```bash
python manage.py runserver
```

Visit http://127.0.0.1:8000

## Without Elasticsearch

If you don't have Elasticsearch set up yet, the site will still run but search won't work. You'll see connection errors in the console.

To set up Elasticsearch locally:

```bash
# Using Docker (easiest)
docker run -d --name elasticsearch \
  -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  docker.elastic.co/elasticsearch/elasticsearch:8.11.0
```

## Project Structure

```
ahmia-site/
├── ahmia/                 # Main Django app
│   ├── views.py          # Search views
│   ├── templates/        # HTML templates
│   └── static/           # CSS, JS, images
├── profiles/             # Onion profiles system
│   ├── models/           # Database models
│   ├── services/         # Business logic
│   ├── views/            # Profile views
│   └── templates/        # Profile templates
├── docs/                 # Documentation
├── scripts/              # Utility scripts
└── manage.py             # Django management
```

## Running Tests

```bash
# Run all tests
python -m pytest

# Run only profile tests
python -m pytest profiles/

# Run with coverage
python -m pytest --cov=profiles --cov=ahmia
```

## Common Issues

### "Connection refused" to Elasticsearch

Elasticsearch isn't running or the URL is wrong. Check:
```bash
curl -k https://localhost:9200
```

### "No module named 'elasticsearch'"

Dependencies not installed:
```bash
pip install -r requirements.txt
```

### "CSRF verification failed"

Clear your browser cookies or run with:
```bash
python manage.py runserver --insecure
```

## Next Steps

- [Architecture Overview](./ARCHITECTURE.md) - Understand the system design
- [Configuration Guide](./CONFIGURATION.md) - All available settings
- [Profiles System](./PROFILES.md) - The onion directory feature
- [Deployment Guide](./DEPLOYMENT.md) - Deploy to production
