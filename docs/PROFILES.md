# Onion Profiles System

The profiles system provides a directory of .onion sites with community-driven metadata, owner verification, and moderation.

## Features

- **Auto-generated profiles** from Elasticsearch crawl data
- **Owner verification** via `.well-known/ahmia-verify.txt`
- **Community edits** with trust-based moderation
- **URL migration tracking** when sites change domains
- **SEO-friendly** profile pages at `/site/<slug>/`
- **Category/tag browsing** for discovery

## URL Structure

| URL | Description |
|-----|-------------|
| `/site/` | Profile directory listing |
| `/site/<slug>/` | Individual profile page |
| `/site/<slug>/edit/` | Suggest edits |
| `/site/<slug>/claim/` | Verify ownership |
| `/site/<slug>/history/` | Domain & edit history |
| `/site/categories/` | Browse by category |
| `/site/category/<slug>/` | Profiles in category |
| `/site/tags/` | Browse by tag |
| `/site/tag/<slug>/` | Profiles with tag |
| `/site/moderate/` | Moderation queue |

---

## How It Works

### Profile Creation

Profiles are auto-generated from crawled sites:

```bash
# Sync profiles from Elasticsearch
python manage.py sync_profiles

# Update cached stats (page count, last seen)
python manage.py update_stats
```

The sync process:
1. Queries ES for all unique domains
2. Creates a profile for each new domain
3. Extracts title/description from most common page metadata
4. Generates a unique slug

### Owner Verification

Site owners can verify ownership to gain editing privileges:

1. Visit `/site/<slug>/claim/`
2. Get a unique verification token
3. Create `/.well-known/ahmia-verify.txt` on their site containing the token
4. Click "Verify" - Ahmia fetches the file over Tor
5. If token matches, profile is marked verified

```
# Example: http://example.onion/.well-known/ahmia-verify.txt
a1b2c3d4e5f6...  (64-character hex token)
```

### Community Edits

Anyone can suggest edits to profile metadata:

1. Visit `/site/<slug>/edit/`
2. Modify name, description, or category
3. Submit for review
4. Trusted users approve/reject in moderation queue

**Rate Limits:**
- 10 edits per hour per contributor
- Cooldown after rejected edits
- Banned users cannot submit

### Trust System

Contributors earn trust through approved edits:

| Level | Name | After | Can Do |
|-------|------|-------|--------|
| 0 | Anonymous | - | Submit edits |
| 1 | New | Login | Submit edits |
| 2 | Trusted | 5 approvals | Auto-approve, review others |
| 3 | Moderator | Manual | All + ban users |

---

## Management Commands

### sync_profiles

Generate profiles from Elasticsearch crawl data.

```bash
# Full sync
python manage.py sync_profiles

# Dry run (show what would be created)
python manage.py sync_profiles --dry-run
```

### update_stats

Refresh cached statistics (page count, last seen).

```bash
# Update all profiles
python manage.py update_stats

# Update single profile
python manage.py update_stats --profile=example-site
```

### check_verifications

Verify pending ownership claims.

```bash
# Check profiles with pending tokens
python manage.py check_verifications

# Re-verify all verified profiles
python manage.py check_verifications --all

# Check specific profile
python manage.py check_verifications --profile=example-site
```

### seed_categories

Create default categories.

```bash
python manage.py seed_categories

# Force update existing
python manage.py seed_categories --force
```

**Default Categories:**
- Forum, Marketplace, News, Social
- Search, Hosting, Email, Cryptocurrency
- Wiki, Blog, Tools, Other

---

## Models

### OnionProfile

The primary model representing a .onion site.

```python
OnionProfile(
    id=UUID,
    slug='example-site',           # URL-friendly identifier
    current_domain='example.onion', # Current .onion address
    name='Example Site',
    description='A sample onion site',
    category=Category,
    is_verified=False,
    verification_token='abc123...',
    owner=User,                     # Set after verification
    page_count=42,                  # Cached from ES
    last_seen=datetime,             # Cached from ES
    status='active',                # active/offline/banned
)
```

### Category & Tag

Taxonomy for organizing profiles.

```python
Category(name='Forum', slug='forum', description='Discussion boards')
Tag(name='privacy', slug='privacy')
```

### Contributor

Tracks user trust levels and edit history.

```python
Contributor(
    user=User,                 # Optional Django user
    session_key='abc123',      # For anonymous contributors
    ip_hash='sha256...',       # Privacy-preserving rate limiting
    trust_level=TrustLevel.NEW,
    approved_edits=3,
    rejected_edits=0,
    is_banned=False,
)
```

### ProfileEdit

Pending and historical edits.

```python
ProfileEdit(
    profile=OnionProfile,
    field_name='description',
    old_value='Old text',
    new_value='New text',
    submitted_by=Contributor,
    reviewed_by=Contributor,
    status='pending',          # pending/approved/rejected
)
```

### DomainHistory

Tracks URL changes over time.

```python
DomainHistory(
    profile=OnionProfile,
    domain='oldsite.onion',
    was_active_from=datetime,
    was_active_to=datetime,
    migration_type='community',  # owner/community/crawler
)
```

---

## Services

Business logic is encapsulated in services:

### ProfileService

```python
from profiles.services import get_service

service = get_service('profile_service')

# Get profile with live ES stats
data = service.get_profile_with_stats('example-site')
# Returns: {profile, page_count, last_seen, top_pages}

# Create profile
profile = service.create_profile(domain='new.onion', name='New Site', category=cat)

# Update profile
service.update_profile(profile, name='Updated Name')
```

### VerificationService

```python
service = get_service('verification_service')

# Start verification (generates token)
token = service.start_verification(profile)

# Check verification (fetches .well-known file)
is_verified = service.check_verification(profile)

# Revoke verification
service.revoke_verification(profile)
```

### ModerationService

```python
service = get_service('moderation_service')

# Submit edit
edit = service.submit_edit(profile, 'description', 'New description', contributor)

# Approve/reject
service.approve_edit(edit, reviewer, 'Looks good')
service.reject_edit(edit, reviewer, 'Spam')

# Get pending count
count = service.count_pending()
```

### TrustService

```python
service = get_service('trust_service')

# Get/create contributor for request
contributor = service.get_or_create_contributor(request)

# Check permissions
can_edit = service.check_can_edit(contributor)
can_review = service.check_can_review(contributor)
```

### SyncService

```python
service = get_service('sync_service')

# Sync all profiles from ES
stats = service.sync_all_profiles()
# Returns: {created: 5, skipped: 100, total_domains: 105}

# Update single profile stats
service.update_profile_stats(profile)

# Update all stats
count = service.update_all_stats()
```

---

## Templates

Templates are located in `profiles/templates/profiles/`:

| Template | Purpose |
|----------|---------|
| `base_profiles.html` | Base template with nav |
| `profile_list.html` | Directory listing |
| `profile_detail.html` | Individual profile |
| `profile_edit.html` | Edit form |
| `profile_claim.html` | Verification instructions |
| `profile_history.html` | Domain & edit history |
| `category_list.html` | Category listing |
| `category_detail.html` | Profiles in category |
| `tag_list.html` | Tag cloud |
| `tag_detail.html` | Profiles with tag |
| `moderation_queue.html` | Pending edits |
| `edit_review.html` | Review single edit |
| `migration_review.html` | Review domain change |

**Partials:**
- `_profile_card.html` - Profile card component
- `_stats_box.html` - Page count, last seen
- `_domain_history.html` - URL change table
- `_edit_diff.html` - Before/after comparison

---

## Admin Interface

Access the Django admin at `/admin/` to manage:

- **Categories** - Add/edit/delete categories
- **Tags** - Manage tags
- **Profiles** - View/edit all profiles, inline domain history
- **Contributors** - Manage trust levels, bans
- **Profile Edits** - View edit history (read-only)
- **Migration Reports** - View migrations (read-only)

---

## Integration with Search

Profile links appear in search results when a domain has a profile:

```html
<!-- In search results -->
<a href="/site/example-site/">View site profile</a>
```

This is implemented via:
- `ProfileRepository.get_profiles_for_domains()` - Batch lookup
- `profile_tags.get_item` - Template filter for dict access

---

## SEO

The profiles system includes SEO features:

### Sitemap

Available at `/sitemap-profiles.xml`:
- All active profiles
- All categories
- Static pages (list, category list, tag list)

### Meta Tags

Templates include:
- `<title>` with profile/category name
- Semantic HTML structure
- Proper heading hierarchy

---

## Extensibility

The service registry pattern allows extending functionality:

```python
# Create custom service
from profiles.services import register_service

@register_service('my_service')
class MyService:
    def custom_logic(self):
        ...

# Use it
service = get_service('my_service')
```

This pattern enables:
- Swapping implementations
- Adding plugins
- Easy testing with mocks
