# Configuration Reference

All Ahmia configuration is done through environment variables. Copy `.env.example` to `.env` and customize.

## Environment Variables

### Elasticsearch

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ES_URL` | Yes | `https://10.0.0.2:9200/` | Elasticsearch server URL |
| `ES_USERNAME` | Yes | `elastic` | ES username |
| `ES_PASSWORD` | Yes | `password12345` | ES password |
| `ES_CA_CERTS` | No | `/etc/elasticsearch/certs/http_ca.crt` | Path to CA certificate |
| `VERIFY_CERT` | No | `False` | Verify SSL certificate |
| `ELASTICSEARCH_TIMEOUT` | No | `60` | Query timeout in seconds |

**Example:**
```bash
ES_URL=https://192.168.1.100:9200/
ES_USERNAME=elastic
ES_PASSWORD=my_secure_password
ES_CA_CERTS=/etc/ahmia/certs/http_ca.crt
VERIFY_CERT=True
ELASTICSEARCH_TIMEOUT=30
```

### Django Core

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes* | (insecure default) | Django secret key |
| `DEBUG` | No | `False` | Enable debug mode |
| `ALLOWED_HOSTS` | No | (see below) | Additional allowed hosts |

*Required for production

**Generate a secret key:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

**Default allowed hosts:**
- `127.0.0.1`, `localhost`
- `.ahmia.fi` (including subdomains)
- `.juhanurmihxlp77nkq76byazcldy2hlmovfu2epvl5ankdibsot4csyd.onion`

**Adding custom hosts:**
```bash
ALLOWED_HOSTS=mydomain.com,api.mydomain.com
```

### Database

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | No | SQLite | Full database URL |

**SQLite (default):**
No configuration needed. Database stored at `db.sqlite3`.

**PostgreSQL:**
```bash
DATABASE_URL=postgres://user:password@localhost:5432/ahmia
```

**With SSL:**
```bash
DATABASE_URL=postgres://user:password@host:5432/ahmia?sslmode=require
```

### Security

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SALT` | No | `secret_salt_value` | Salt for hashing operations |

---

## Configuration Files

### .env

Primary configuration file. Never commit to git.

```bash
# .env
ES_URL=https://localhost:9200/
ES_USERNAME=elastic
ES_PASSWORD=changeme
SECRET_KEY=your-random-key-here
DEBUG=False
```

### .env.example

Template showing all available options. Safe to commit.

### settings.py

Django settings file. Uses `python-decouple` to read from `.env`:

```python
from decouple import config

ELASTICSEARCH_SERVER = config('ES_URL', default='https://localhost:9200/')
DEBUG = config('DEBUG', default=False, cast=bool)
```

---

## Profile System Settings

These are defined in `profiles/constants.py`:

| Constant | Value | Description |
|----------|-------|-------------|
| `TRUST_LEVEL_THRESHOLD` | `5` | Approved edits needed for TRUSTED |
| `RATE_LIMIT_EDITS_PER_HOUR` | `10` | Max edits per hour per contributor |
| `COOLDOWN_HOURS` | `24` | Cooldown after rejected edits |
| `VERIFICATION_TOKEN_EXPIRY_DAYS` | `7` | Token validity period |
| `VERIFICATION_RECHECK_DAYS` | `30` | Re-verify after this period |
| `VERIFICATION_MAX_FAILURES` | `3` | Failures before token reset |
| `DEFAULT_CATEGORY_SLUG` | `'other'` | Fallback category |
| `LOGO_MAX_SIZE_BYTES` | `102400` | Max logo size (100KB) |

To change these, edit `profiles/constants.py` directly.

---

## Elasticsearch Index

The default index name is `latest-tor`. This is set in `settings.py`:

```python
ELASTICSEARCH_INDEX = 'latest-tor'
```

**Expected mapping:**

```json
{
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
}
```

---

## Logging

Django's default logging is used. To customize, add to `settings.py`:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/ahmia/django.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
        'profiles': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
```

---

## Static Files

| Setting | Default | Description |
|---------|---------|-------------|
| `STATIC_URL` | `/static/` | URL prefix for static files |
| `STATIC_ROOT` | `ahmia/staticfiles/` | Collected static files location |
| `STATICFILES_DIRS` | `ahmia/static/` | Additional static directories |

**Collect for production:**
```bash
python manage.py collectstatic
```

---

## Cron Jobs

Recommended cron schedule:

```bash
# Update profile stats daily at 3am
0 3 * * * cd /var/www/ahmia-site && venv/bin/python manage.py update_stats

# Sync new profiles weekly on Sunday at 4am
0 4 * * 0 cd /var/www/ahmia-site && venv/bin/python manage.py sync_profiles

# Check verifications daily at 5am
0 5 * * * cd /var/www/ahmia-site && venv/bin/python manage.py check_verifications
```

---

## Production Checklist

Before deploying to production:

- [ ] Set `DEBUG=False`
- [ ] Generate and set a secure `SECRET_KEY`
- [ ] Set `VERIFY_CERT=True` for Elasticsearch
- [ ] Configure `ALLOWED_HOSTS` for your domain
- [ ] Use PostgreSQL instead of SQLite for high traffic
- [ ] Set up HTTPS with valid certificates
- [ ] Configure firewall (ES port only accessible from web server)
- [ ] Set up log rotation
- [ ] Configure backups for database
- [ ] Run `collectstatic`
- [ ] Set up cron jobs for profile sync
