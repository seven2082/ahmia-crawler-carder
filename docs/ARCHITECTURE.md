# Ahmia Architecture

## System Overview

Ahmia consists of three main components that work together:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AHMIA ECOSYSTEM                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐     ┌─────────────────┐     ┌─────────────────────────┐   │
│  │   CRAWLER   │────▶│  ELASTICSEARCH  │◀────│      AHMIA SITE         │   │
│  │             │     │                 │     │                         │   │
│  │ - Discovers │     │ - Stores pages  │     │ - Search interface      │   │
│  │ - Fetches   │     │ - Full-text     │     │ - Profile directory     │   │
│  │ - Indexes   │     │ - Aggregations  │     │ - Moderation queue      │   │
│  └─────────────┘     └─────────────────┘     └─────────────────────────┘   │
│                                                                             │
│       (ahmia-crawler)        (Elastic 8.x)         (this repository)       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Ahmia Crawler (External)

Repository: [ahmia-crawler](https://github.com/ahmia/ahmia-crawler)

- Discovers .onion sites via various sources
- Fetches page content over Tor
- Indexes documents into Elasticsearch
- Runs continuously on a schedule

### 2. Elasticsearch

The data layer storing all crawled content.

**Index: `latest-tor`**

```json
{
  "domain": "example.onion",
  "url": "http://example.onion/page",
  "title": "Page Title",
  "meta": "Page description",
  "content": "Full page text content...",
  "updated_on": "2026-08-01T12:00:00Z",
  "is_banned": false
}
```

**Key Queries:**
- Full-text search on `content`, `title`, `meta`
- Domain aggregations for site listings
- Date filtering for freshness

### 3. Ahmia Site (This Repository)

The Django web application providing:

- **Search Interface** - Query ES and display results
- **Profile Directory** - Browse/edit site profiles
- **Moderation** - Community edit review
- **Admin** - Django admin for management

---

## Ahmia Site Architecture

### Layered Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          PRESENTATION LAYER                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │
│  │   Views     │  │  Templates  │  │   Forms     │  │   Admin    │  │
│  └──────┬──────┘  └─────────────┘  └──────┬──────┘  └────────────┘  │
│         │                                  │                         │
├─────────┼──────────────────────────────────┼─────────────────────────┤
│         ▼          SERVICE LAYER           ▼                         │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    Service Registry                          │    │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐ │    │
│  │  │ProfileService│ │ TrustService │ │ ModerationService    │ │    │
│  │  │VerifyService │ │ SyncService  │ │ ElasticsearchService │ │    │
│  │  └──────────────┘ └──────────────┘ └──────────────────────┘ │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                │                                     │
├────────────────────────────────┼─────────────────────────────────────┤
│         DATA ACCESS LAYER      ▼                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                     Repositories                             │    │
│  │  ┌──────────────────┐  ┌────────────────────────────────┐   │    │
│  │  │ ProfileRepository│  │ ModerationRepository           │   │    │
│  │  └──────────────────┘  └────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                │                                     │
├────────────────────────────────┼─────────────────────────────────────┤
│          DATA LAYER            ▼                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                        Models                                │    │
│  │  OnionProfile │ Category │ Contributor │ ProfileEdit │ ...  │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                │                                     │
│  ┌─────────────────────────────┴───────────────────────────────┐    │
│  │           Django ORM (SQLite / PostgreSQL)                   │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
ahmia-site/
├── ahmia/                      # Main search application
│   ├── views.py               # Search views (ES queries)
│   ├── templates/             # Search templates
│   │   ├── core.html         # Base template
│   │   ├── index.html        # Homepage
│   │   └── ahmia/            # Search result templates
│   ├── static/               # CSS, JS, images
│   └── template_tags.py      # Custom template tags
│
├── profiles/                  # Onion profiles system
│   ├── models/               # Django models
│   │   ├── base.py          # Abstract base (UUID pk)
│   │   ├── profile.py       # OnionProfile, DomainHistory
│   │   ├── taxonomy.py      # Category, Tag
│   │   ├── contributor.py   # User trust system
│   │   └── moderation.py    # ProfileEdit, MigrationReport
│   │
│   ├── repositories/         # Data access layer
│   │   ├── base.py          # BaseRepository pattern
│   │   ├── profile_repository.py
│   │   └── moderation_repository.py
│   │
│   ├── services/             # Business logic layer
│   │   ├── registry.py      # Pluggable service registry
│   │   ├── profile_service.py
│   │   ├── verification_service.py
│   │   ├── moderation_service.py
│   │   ├── trust_service.py
│   │   ├── sync_service.py
│   │   ├── slug_service.py
│   │   └── elasticsearch_service.py
│   │
│   ├── views/                # Django views
│   │   ├── mixins.py        # ContributorMixin, TrustRequiredMixin
│   │   ├── profile_views.py # List, detail, edit, claim
│   │   ├── directory_views.py # Category, tag browsing
│   │   └── moderation_views.py # Review queue
│   │
│   ├── forms/               # Django forms
│   ├── templates/profiles/  # Profile templates
│   ├── management/commands/ # CLI commands
│   ├── admin.py            # Django admin config
│   ├── urls.py             # URL routing
│   └── sitemaps.py         # SEO sitemaps
│
├── docs/                    # Documentation
├── scripts/                 # Deployment scripts
└── manage.py
```

---

## Data Flow

### Search Flow

```
User searches "bitcoin"
        │
        ▼
┌─────────────────┐
│ OnionListView   │
│ (ahmia/views.py)│
└────────┬────────┘
         │ Query: {"query": {"multi_match": {"query": "bitcoin", ...}}}
         ▼
┌─────────────────┐
│ Elasticsearch   │
│ (latest-tor)    │
└────────┬────────┘
         │ Results: [{url, title, domain, snippet}, ...]
         ▼
┌─────────────────┐
│ tor_results.html│
│ (template)      │
└────────┬────────┘
         │ + Profile links if domain has profile
         ▼
    HTML Response
```

### Profile Edit Flow

```
User submits edit
        │
        ▼
┌─────────────────┐
│ ProfileEditView │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ModerationService│
│ .submit_edit()  │
└────────┬────────┘
         │ Check: rate limit, banned, trust level
         ▼
┌─────────────────┐
│ ProfileEdit     │
│ (status=PENDING)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ModerationQueue  │◀─── Trusted users review
└────────┬────────┘
         │ approve / reject
         ▼
┌─────────────────┐
│ModerationService│
│ .approve_edit() │
└────────┬────────┘
         │ Apply change, update trust
         ▼
    Profile Updated
```

---

## Service Registry Pattern

Services are registered and retrieved via a central registry, enabling:
- Dependency injection
- Easy testing with mocks
- Plugin extensibility

```python
# Registration (in service file)
from .registry import register_service

@register_service('profile_service')
class ProfileService:
    def get_profile_with_stats(self, slug):
        ...

# Usage (in views/other services)
from profiles.services import get_service

profile_service = get_service('profile_service')
data = profile_service.get_profile_with_stats('example-site')
```

---

## Trust System

Contributors earn trust through approved edits:

| Level | Name | Value | Capabilities |
|-------|------|-------|--------------|
| 0 | ANONYMOUS | 0 | Submit edits (queued) |
| 1 | NEW | 1 | Submit edits (queued) |
| 2 | TRUSTED | 2 | Auto-approve edits, review others |
| 3 | MODERATOR | 3 | All permissions, manage bans |

**Trust Progression:**
- Start at ANONYMOUS (session-based) or NEW (logged in)
- Reach TRUSTED after 5 approved edits
- MODERATOR is manually assigned

---

## Database Schema

### Core Tables

```
┌─────────────────┐       ┌─────────────────┐
│    Category     │       │      Tag        │
├─────────────────┤       ├─────────────────┤
│ id (UUID)       │       │ id (UUID)       │
│ name            │       │ name            │
│ slug            │       │ slug            │
│ description     │       └────────┬────────┘
└────────┬────────┘                │
         │                         │ M:N
         │ 1:N                     │
         ▼                         ▼
┌─────────────────────────────────────────┐
│              OnionProfile               │
├─────────────────────────────────────────┤
│ id (UUID)                               │
│ slug (unique)                           │
│ current_domain (unique)                 │
│ name, description                       │
│ category_id (FK)                        │
│ owner_id (FK to User, nullable)         │
│ is_verified, verification_token         │
│ page_count, last_seen (cached from ES)  │
│ status (active/offline/banned)          │
│ created_at, updated_at                  │
└────────┬────────────────────────────────┘
         │
         │ 1:N
         ▼
┌─────────────────────────────────────────┐
│            DomainHistory                │
├─────────────────────────────────────────┤
│ profile_id (FK)                         │
│ domain                                  │
│ was_active_from, was_active_to          │
│ migration_type                          │
└─────────────────────────────────────────┘

┌─────────────────┐       ┌─────────────────┐
│   Contributor   │       │   ProfileEdit   │
├─────────────────┤       ├─────────────────┤
│ id              │◀──────│ submitted_by    │
│ user_id (FK)    │       │ reviewed_by     │
│ session_key     │       │ profile_id      │
│ trust_level     │       │ field_name      │
│ approved_edits  │       │ old/new_value   │
│ is_banned       │       │ status          │
└─────────────────┘       └─────────────────┘
```

---

## Security Considerations

### Input Validation
- All user input through Django forms
- Rate limiting on edit submissions
- Trust-based access control

### Authentication
- Session-based contributor tracking
- Optional Django user accounts
- IP hashing for rate limiting (privacy-preserving)

### Tor Integration
- Verification fetches `.well-known/ahmia-verify.txt` over Tor
- No clearnet requests for onion content

### Data Protection
- No logging of search queries
- Minimal PII collection
- Session keys hashed before storage
