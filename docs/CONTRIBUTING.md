# Contributing to Ahmia

Thank you for your interest in contributing to Ahmia! This document provides guidelines for contributing.

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- No harassment or discrimination
- Respect privacy and security concerns

## Getting Started

1. Fork the repository
2. Clone your fork
3. Set up the development environment (see [Getting Started](./GETTING_STARTED.md))
4. Create a feature branch

```bash
git checkout -b feature/your-feature-name
```

## Development Workflow

### 1. Find or Create an Issue

- Check existing issues for something to work on
- Create a new issue for bugs or feature requests
- Wait for feedback before starting major work

### 2. Write Code

Follow these guidelines:

**Python Style:**
- Follow PEP 8
- Use type hints where helpful
- Keep functions focused and small
- Write docstrings for public APIs

**Django Conventions:**
- Fat models, thin views
- Business logic in services
- Use Django forms for validation

**Testing:**
- Write tests first (TDD encouraged)
- All new features need tests
- Maintain or improve coverage

### 3. Test Your Changes

```bash
# Run all tests
python -m pytest

# Run specific tests
python -m pytest profiles/tests/test_services/

# Run with coverage
python -m pytest --cov=profiles --cov-report=html
```

### 4. Commit Your Changes

Write clear commit messages:

```
feat(profiles): add domain migration tracking

- Add MigrationReport model
- Add migration detection service
- Add community reporting form

Closes #123
```

**Commit types:**
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `test:` Tests
- `refactor:` Code refactoring
- `style:` Formatting, no code change
- `chore:` Build, tooling, dependencies

### 5. Submit a Pull Request

- Push your branch to your fork
- Open a PR against `master`
- Fill in the PR template
- Wait for review

## Pull Request Guidelines

### What to Include

- Clear description of changes
- Link to related issue(s)
- Test plan or evidence of testing
- Screenshots for UI changes

### What We Look For

- Tests pass
- Code follows style guidelines
- No security vulnerabilities
- Documentation updated if needed
- Backwards compatible (or migration plan)

### Review Process

1. Automated checks run (tests, linting)
2. Maintainer reviews code
3. Feedback addressed
4. Approval and merge

---

## Project Structure

Understanding the codebase:

```
ahmia-site/
├── ahmia/           # Main search app
├── profiles/        # Profile directory system
│   ├── models/     # Database models
│   ├── services/   # Business logic
│   ├── views/      # HTTP handlers
│   └── tests/      # Test suite
├── docs/           # Documentation
└── scripts/        # Utility scripts
```

**Key patterns:**
- Service registry for business logic
- Repository pattern for data access
- Mixin-based views for shared behavior

---

## Testing Guidelines

### Test Structure

```
profiles/tests/
├── test_models/        # Model unit tests
├── test_services/      # Service unit tests
├── test_views/         # View integration tests
├── test_commands/      # Management command tests
├── test_integration/   # End-to-end tests
├── factories.py        # Test data factories
└── conftest.py         # Pytest fixtures
```

### Writing Tests

```python
import pytest
from profiles.tests.factories import OnionProfileFactory

pytestmark = pytest.mark.django_db


class TestProfileService:
    def test_get_profile_returns_stats(self):
        # Arrange
        profile = OnionProfileFactory(slug='test-site')
        service = get_service('profile_service')
        
        # Act
        result = service.get_profile_with_stats('test-site')
        
        # Assert
        assert result['profile'] == profile
        assert 'page_count' in result
```

### Test Categories

- **Unit tests:** Test single functions/methods in isolation
- **Integration tests:** Test components working together
- **E2E tests:** Test full user flows

---

## Documentation

### When to Update Docs

- New features need documentation
- API changes need reference updates
- Complex code needs inline comments
- Configuration changes need CONFIGURATION.md updates

### Documentation Style

- Use clear, simple language
- Include code examples
- Keep it concise
- Use tables for reference material

---

## Security

### Reporting Vulnerabilities

**Do NOT open public issues for security vulnerabilities.**

Email security concerns to the maintainers directly.

### Security Guidelines

- Never commit secrets or credentials
- Validate all user input
- Use parameterized queries (Django ORM)
- Escape output in templates
- Follow OWASP guidelines

---

## Questions?

- Open a GitHub issue for bugs/features
- Check existing documentation
- Look at similar PRs for examples

Thank you for contributing to Ahmia!
