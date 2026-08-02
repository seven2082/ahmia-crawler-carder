# Onion Profile System Design

**Date:** 2026-08-01  
**Status:** Draft  
**Author:** Claude + User

## Overview

Add a profile/directory system to Ahmia that creates one profile per onion domain, enabling:
- Auto-generated profiles from Elasticsearch crawl data
- Owner verification via `.well-known` file
- Community-submitted edits with moderation
- URL change tracking across migrations
- SEO-friendly profile pages

## Requirements Summary

| Aspect | Decision |
|--------|----------|
| Edit Access | Anyone (open wiki-style) |
| Moderation | Hybrid trust levels (auto-approve trusted contributors) |
| URL Migration Sources | All sources (owner, community, crawler) |
| Categories | Fixed taxonomy + custom freeform tags |
| URL Structure | `/site/<slug>` for SEO |
| Storage | SQLite initially (same as current), PostgreSQL-compatible design for future upgrade |
| Crawl Data Display | Hybrid (cached basic stats + live detailed queries) |
| Search UX | Both options (profile link + direct .onion link in results) |
| Auth Model | Optional accounts (anonymous allowed, accounts unlock benefits) |

## Architecture

### Approach

Separate Django app (`profiles`) within the same project. This provides:
- Clean separation from existing `ahmia` search functionality
- Shared database, templates, and deployment
- Independent testability
- Potential for future extraction if needed

### System Diagram

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  ahmia-crawler  │────▶│  Elasticsearch  │◀────│   ahmia-site    │
│  (external)     │     │  (latest-tor)   │     │                 │
└─────────────────┘     └─────────────────┘     │  ┌───────────┐  │
        │                       ▲               │  │  ahmia    │  │
        │                       │               │  │  (search) │  │
   Crawls .onion           Indexed data         │  └───────────┘  │
   sites via Tor           + migration          │        │        │
                           hints                │        ▼        │
                                                │  ┌───────────┐  │
                                                │  │ profiles  │  │
                                                │  │ (new app) │  │
                                                │  └───────────┘  │
                                                │        │        │
                                                │        ▼        │
                                                │  ┌───────────┐  │
                                                │  │  SQLite   │  │
                                                │  │(profiles) │  │
                                                │  └───────────┘  │
                                                └─────────────────┘
```

## Data Models

### OnionProfile

Primary model representing a single onion website.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `slug` | CharField(100) | URL-safe identifier, unique |
| `current_domain` | CharField(70) | Current .onion domain, unique |
| `name` | CharField(255) | Display name |
| `description` | TextField | SEO meta description |
| `category` | ForeignKey(Category) | Primary category |
| `logo` | TextField | Base64 data URI, max 100KB (optional) |
| `is_verified` | BooleanField | Owner has claimed |
| `verification_token` | CharField(64) | For .well-known verification |
| `verification_token_expires` | DateTimeField | Token expiry |
| `verification_fail_count` | IntegerField | Consecutive check failures |
| `owner` | ForeignKey(User) | Nullable, for verified sites |
| `page_count` | IntegerField | Cached from ES |
| `last_seen` | DateTimeField | Cached from ES |
| `status` | CharField(20) | active/offline/banned |
| `created_at` | DateTimeField | Auto |
| `updated_at` | DateTimeField | Auto |

### DomainHistory

Tracks URL changes over time.

| Field | Type | Description |
|-------|------|-------------|
| `id` | BigAutoField | Primary key |
| `profile` | ForeignKey(OnionProfile) | Parent profile |
| `domain` | CharField(70) | Historical domain |
| `was_active_from` | DateTimeField | When first seen |
| `was_active_to` | DateTimeField | When replaced |
| `migration_type` | CharField(20) | owner/community/crawler |

### Category

Fixed taxonomy for primary categorization.

| Field | Type | Description |
|-------|------|-------------|
| `id` | AutoField | Primary key |
| `name` | CharField(50) | Display name |
| `slug` | SlugField(50) | URL-safe, unique |
| `description` | TextField | Category description |
| `icon` | CharField(50) | Icon class or emoji |

**Initial Categories:**
- marketplace, forum, news, blog, tools, social, hosting, email, crypto, other

### Tag

Freeform tags for additional classification.

| Field | Type | Description |
|-------|------|-------------|
| `id` | AutoField | Primary key |
| `name` | CharField(50) | Tag name, unique |
| `slug` | SlugField(50) | URL-safe, unique |
| `is_approved` | BooleanField | Moderator-approved |

### ProfileTag

Many-to-many relationship between profiles and tags.

| Field | Type | Description |
|-------|------|-------------|
| `id` | BigAutoField | Primary key |
| `profile` | ForeignKey(OnionProfile) | Profile |
| `tag` | ForeignKey(Tag) | Tag |

### Contributor

Tracks edit history for trust levels.

| Field | Type | Description |
|-------|------|-------------|
| `id` | BigAutoField | Primary key |
| `user` | ForeignKey(User) | Nullable (for registered users) |
| `session_key` | CharField(64) | For anonymous contributors |
| `ip_hash` | CharField(64) | Hashed IP for rate limiting |
| `approved_edits` | IntegerField | Count of approved edits |
| `rejected_edits` | IntegerField | Count of rejected edits |
| `trust_level` | IntegerField | 0=anon, 1=new, 2=trusted, 3=mod |
| `is_banned` | BooleanField | Banned from contributing |
| `cooldown_until` | DateTimeField | Nullable, for rate limiting |
| `created_at` | DateTimeField | Auto |

### ProfileEdit

Pending and historical edits.

| Field | Type | Description |
|-------|------|-------------|
| `id` | BigAutoField | Primary key |
| `profile` | ForeignKey(OnionProfile) | Target profile |
| `field_name` | CharField(50) | Which field changed |
| `old_value` | TextField | Previous value |
| `new_value` | TextField | Proposed value |
| `submitted_by` | ForeignKey(Contributor) | Who submitted |
| `status` | CharField(20) | pending/approved/rejected |
| `reviewed_by` | ForeignKey(Contributor) | Nullable, who reviewed |
| `review_notes` | TextField | Optional moderator notes |
| `created_at` | DateTimeField | Auto |
| `reviewed_at` | DateTimeField | Nullable |

### MigrationReport

Reports of URL changes.

| Field | Type | Description |
|-------|------|-------------|
| `id` | BigAutoField | Primary key |
| `profile` | ForeignKey(OnionProfile) | Nullable, linked after approval |
| `old_domain` | CharField(70) | Previous domain |
| `new_domain` | CharField(70) | New domain |
| `source` | CharField(20) | owner/community/crawler |
| `evidence_url` | URLField | Link showing migration notice |
| `evidence_text` | TextField | Extracted text evidence |
| `status` | CharField(20) | pending/approved/rejected |
| `submitted_by` | ForeignKey(Contributor) | Nullable for crawler |
| `reviewed_by` | ForeignKey(Contributor) | Nullable |
| `created_at` | DateTimeField | Auto |
| `reviewed_at` | DateTimeField | Nullable |

## Verification Flow

### Owner Verification Process

1. Owner visits `/site/<slug>/claim/`
2. System generates unique token (64 chars, expires in 7 days)
3. Owner instructed to create `/.well-known/ahmia-verify.txt` containing:
   ```
   ahmia-token=<token>
   ```
4. Owner clicks "Verify Now" or waits for hourly check
5. System fetches file via Tor, validates token
6. On success: profile marked verified, owner account linked
7. On failure: error message shown, can retry

### Verification Maintenance

- Verified profiles re-checked every 30 days
- If file missing/invalid: increment `verification_fail_count`
- After 3 consecutive failures: profile unverified, owner notified
- Owner can re-verify at any time

### Verified Owner Privileges

- Edit profile directly (no moderation queue)
- Update URL when migrating
- Upload custom logo
- Access view count analytics

## Trust & Moderation System

### Trust Levels

| Level | Name | Requirements | Privileges |
|-------|------|--------------|------------|
| 0 | Anonymous | No account | Submit edits (queued), report migrations (queued) |
| 1 | New | Account created | Same as L0, edits tracked to account |
| 2 | Trusted | 5+ approved edits | Edits auto-approved, can approve L0/L1 edits |
| 3 | Moderator | Manually promoted | All L2 + reject, ban, manage categories |

### Moderation Queue

Edits from L0/L1 contributors enter the queue:
1. Reviewer sees diff (old value → new value)
2. Options: Approve, Reject, Flag submitter
3. Approved: applied to profile, submitter gains trust credit
4. Rejected: logged, submitter notified if has account

### Anti-Abuse Measures

| Measure | Implementation |
|---------|----------------|
| Rate limiting | Max 10 edits/hour per IP or user |
| CAPTCHA | Required for anonymous submissions |
| Cooldown | 24h cooldown after 2 rejected edits |
| Rollback | Any edit can be reverted by L2+ |
| Audit log | All actions logged with IP hash, user, timestamp |

## URL Structure

| URL | View | Description |
|-----|------|-------------|
| `/site/` | ProfileListView | Paginated directory |
| `/site/<slug>/` | ProfileDetailView | Profile page |
| `/site/<slug>/edit/` | ProfileEditView | Submit edit |
| `/site/<slug>/claim/` | ProfileClaimView | Start verification |
| `/site/<slug>/history/` | ProfileHistoryView | URL/edit history |
| `/site/category/<slug>/` | CategoryListView | By category |
| `/site/tag/<slug>/` | TagListView | By tag |
| `/site/report-migration/` | MigrationReportView | Report URL change |
| `/moderation/` | ModerationQueueView | Pending edits (L2+) |
| `/moderation/edit/<id>/` | EditReviewView | Review single edit |

## Profile Page Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  [Logo]   Site Name                            [Verified ✓]    │
│           category: marketplace | tags: crypto, escrow         │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Description text here...                                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Pages: 247   │  │ Last Seen:   │  │ Status:      │          │
│  │ (indexed)    │  │ 2 hours ago  │  │ 🟢 Active    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                 │
│  [Visit Site ↗]   [Suggest Edit]   [Report Migration]          │
│                                                                 │
│  ─────────────────────────────────────────────────────────     │
│  URL History                                                    │
│  • current: abc123...xyz.onion (since Jan 2026)                │
│  • previous: old111...aaa.onion (Jun 2025 - Jan 2026)          │
│                                                                 │
│  ─────────────────────────────────────────────────────────     │
│  Popular Pages (live from ES)                                   │
│  • /marketplace - "Main Marketplace"                           │
│  • /forum - "Community Forum"                                  │
└─────────────────────────────────────────────────────────────────┘
```

## SEO Implementation

| Element | Implementation |
|---------|----------------|
| `<title>` | `{name} - Ahmia Onion Directory` |
| `<meta description>` | Profile description (max 160 chars) |
| `<link rel="canonical">` | `/site/<slug>/` |
| Open Graph | `og:title`, `og:description`, `og:image` |
| JSON-LD | WebSite + Organization schema |
| Sitemap | Auto-generated `/sitemap-profiles.xml` |

## Auto-Generation & Sync

### Profile Creation

Hourly `sync_profiles` command:
1. Query ES for all unique domains
2. For each domain not in database:
   - Generate slug from domain (first 12 chars) or extracted name
   - Extract name from most common `<title>`
   - Extract description from most common `<meta>`
   - Set category to "other"
   - Set page_count and last_seen from aggregations
3. Create OnionProfile record

### Stats Update

Hourly `update_stats` command:
1. For each active profile:
   - Query ES for domain aggregation
   - Update page_count, last_seen
   - Set status: active (<7 days), offline (>30 days)

### Crawler Migration Detection

Daily `detect_migrations` command:
1. Query ES for documents with `detected_migration` field
2. For each detection:
   - Create MigrationReport with source="crawler"
   - Status="pending" (requires moderator approval)

## Search Results Integration

Modify `ahmia/templates/tor_results.html`:
- Add "View Profile" link next to domain
- Link to `/site/<slug>/`

Modify `ahmia/views.py` `TorResultsView`:
- Lookup profile slug for each result domain
- Pass to template context

## App Structure

```
profiles/
├── __init__.py
├── admin.py
├── apps.py
├── forms.py
├── models.py
├── urls.py
├── views.py
├── validators.py
├── services/
│   ├── __init__.py
│   ├── elasticsearch.py
│   ├── verification.py
│   ├── sync.py
│   └── slugify.py
├── management/
│   └── commands/
│       ├── sync_profiles.py
│       ├── check_verifications.py
│       ├── update_stats.py
│       ├── detect_migrations.py
│       └── cleanup_expired_tokens.py
├── templates/
│   └── profiles/
│       ├── profile_list.html
│       ├── profile_detail.html
│       ├── profile_edit.html
│       ├── profile_claim.html
│       ├── profile_history.html
│       ├── category_list.html
│       ├── moderation_queue.html
│       └── partials/
│           ├── _profile_card.html
│           └── _edit_diff.html
├── migrations/
└── tests/
    ├── test_models.py
    ├── test_views.py
    ├── test_verification.py
    └── test_sync.py
```

## Settings

Add to `ahmia/settings.py`:

```python
INSTALLED_APPS = [
    'profiles',
    'ahmia',
    ...
]

# Profile system settings
PROFILE_VERIFICATION_TOKEN_EXPIRY_DAYS = 7
PROFILE_VERIFICATION_RECHECK_DAYS = 30
PROFILE_VERIFICATION_MAX_FAILURES = 3
PROFILE_TRUST_LEVEL_THRESHOLD = 5
PROFILE_RATE_LIMIT_EDITS_PER_HOUR = 10
PROFILE_COOLDOWN_HOURS = 24
PROFILE_DEFAULT_CATEGORY = 'other'
```

## Cron Jobs

```bash
# /etc/cron.d/ahmia-profiles
0 * * * *   cd /usr/local/lib/ahmia-site && venv/bin/python manage.py sync_profiles
15 * * * *  cd /usr/local/lib/ahmia-site && venv/bin/python manage.py check_verifications
30 * * * *  cd /usr/local/lib/ahmia-site && venv/bin/python manage.py update_stats
0 3 * * *   cd /usr/local/lib/ahmia-site && venv/bin/python manage.py detect_migrations
0 4 * * *   cd /usr/local/lib/ahmia-site && venv/bin/python manage.py cleanup_expired_tokens
```

## Dependencies

Add to `requirements.txt`:
```
django-ratelimit>=4.0.0
```

## Migration Path

1. Create `profiles` app with all models
2. Run migrations
3. Run initial `sync_profiles` to populate from ES
4. Add URL routes
5. Create templates
6. Integrate with search results
7. Set up cron jobs
8. Test verification flow

## Success Criteria

- [ ] Profiles auto-generated for all crawled domains
- [ ] Profile pages render with SEO metadata
- [ ] Owner verification flow works end-to-end
- [ ] Community edits go through moderation queue
- [ ] Trust levels auto-upgrade after approved edits
- [ ] URL migrations tracked in history
- [ ] Search results link to profile pages
- [ ] Stats sync hourly from Elasticsearch
