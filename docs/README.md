# Ahmia Search Engine Documentation

Ahmia is a search engine for Tor hidden services (.onion sites). It provides a safe and privacy-respecting way to search the dark web.

## Documentation Index

| Document | Description |
|----------|-------------|
| [Getting Started](./GETTING_STARTED.md) | Quick start guide for developers |
| [Architecture](./ARCHITECTURE.md) | System design and components |
| [Deployment](./DEPLOYMENT.md) | Production deployment (single & two-server) |
| [Profiles System](./PROFILES.md) | Onion profile/directory feature |
| [API Reference](./API.md) | Search API documentation |
| [Configuration](./CONFIGURATION.md) | All settings and environment variables |
| [Contributing](./CONTRIBUTING.md) | How to contribute |

## Quick Links

- **Main Site:** https://ahmia.fi
- **GitHub:** https://github.com/ahmia/ahmia-site
- **Crawler:** https://github.com/ahmia/ahmia-crawler

## System Requirements

### Minimum (Development)
- Python 3.10+
- 1 GB RAM
- Elasticsearch 8.x (can be remote)

### Production (Two-Server Recommended)
- **Web Server:** 1-2 GB RAM, 10 GB disk
- **ES Server:** 8+ GB RAM, 50+ GB SSD

## License

BSD 3-Clause License
