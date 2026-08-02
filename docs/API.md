# Ahmia API Reference

Ahmia provides both a web interface and programmatic access to search results.

## Search API

### Search Onion Sites

Perform a search query against indexed .onion sites.

**Endpoint:** `GET /search/`

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | Yes | Search query |
| `p` | integer | No | Page number (default: 1) |

**Example:**
```bash
curl "https://ahmia.fi/search/?q=bitcoin&p=1"
```

**Response:** HTML page with search results.

### Search JSON (Unofficial)

For JSON responses, you can query Elasticsearch directly if you have access:

```bash
curl -X POST "https://your-es-server:9200/latest-tor/_search" \
  -H "Content-Type: application/json" \
  -u elastic:password \
  -d '{
    "query": {
      "multi_match": {
        "query": "bitcoin",
        "fields": ["title^3", "meta^2", "content"]
      }
    },
    "size": 10,
    "_source": ["url", "title", "domain", "meta"]
  }'
```

---

## Profile Endpoints

### List Profiles

**Endpoint:** `GET /site/`

Returns paginated list of all active profiles.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | integer | Page number |

### Get Profile

**Endpoint:** `GET /site/<slug>/`

Returns profile detail page with:
- Name, description, category
- Current domain
- Page count, last seen
- Verification status
- Top pages from the site
- Domain history

### Get Profile History

**Endpoint:** `GET /site/<slug>/history/`

Returns domain migration history and edit log.

### Browse by Category

**Endpoint:** `GET /site/category/<slug>/`

Returns profiles in the specified category.

### Browse by Tag

**Endpoint:** `GET /site/tag/<slug>/`

Returns profiles with the specified tag.

---

## Sitemap

### Profile Sitemap

**Endpoint:** `GET /sitemap-profiles.xml`

XML sitemap containing:
- All active profile URLs
- All category URLs
- Static profile pages

Useful for search engine indexing.

**Example entry:**
```xml
<url>
  <loc>https://ahmia.fi/site/example-site/</loc>
  <lastmod>2026-08-01</lastmod>
  <changefreq>weekly</changefreq>
  <priority>0.7</priority>
</url>
```

---

## Rate Limits

### Search
- No authentication required
- No explicit rate limit (be respectful)

### Profile Edits
- 10 edits per hour per contributor
- Cooldown period after rejected edits
- Banned users cannot submit

---

## Internal Services

For programmatic access within the Django application:

### ProfileService

```python
from profiles.services import get_service

service = get_service('profile_service')
data = service.get_profile_with_stats('example-site')
```

### ElasticsearchService

```python
service = get_service('elasticsearch_service')

# Get domain stats
stats = service.get_domain_stats('example.onion')
# Returns: {page_count: 42, last_seen: datetime}

# Get all domains
domains = service.get_all_domains()
# Returns: [{domain: 'a.onion', page_count: 10}, ...]

# Get top pages for domain
pages = service.get_top_pages('example.onion', limit=5)
# Returns: [{url: '...', title: '...'}, ...]
```

---

## Error Responses

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 302 | Redirect (after form submission) |
| 400 | Bad request |
| 403 | Forbidden (banned, insufficient trust) |
| 404 | Profile not found |
| 429 | Rate limit exceeded |
| 500 | Server error |

### Common Errors

**Profile not found:**
```
HTTP 404
Page shows: "The requested profile could not be found."
```

**Rate limit exceeded:**
```
HTTP 429 or redirect with message:
"You have exceeded the edit rate limit. Please wait before submitting again."
```

**Insufficient trust:**
```
HTTP 302 redirect with message:
"Insufficient trust level for this action."
```

---

## Webhooks (Future)

Webhook support is not currently implemented but could be added for:
- New profile created
- Profile verified
- Edit approved/rejected
- Domain migration detected

If you need webhooks, please open a GitHub issue.

---

## CORS

CORS is not enabled by default. The API is intended for server-side use.

To enable CORS for a specific use case, install `django-cors-headers`:

```bash
pip install django-cors-headers
```

Add to `settings.py`:
```python
INSTALLED_APPS = [
    ...
    'corsheaders',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    ...
]

CORS_ALLOWED_ORIGINS = [
    'https://your-frontend.com',
]
```
