# Contributing to FastAPI Enterprise Boilerplate

Thank you for considering contributing! This document provides guidelines.

## Development Setup

1. Fork and clone the repository
2. Install dependencies:

   ```bash
   make install
   ```

3. Start development servers:

   ```bash
   make dev
   ```

## Code Standards

### Python (Backend)

- Follow PEP 8 (enforced by Ruff)
- Type hints required
- Docstrings for public functions (Google style)
- 100 character line limit

### TypeScript (Frontend)

- ESLint + Prettier for formatting
- Prefer functional components
- TypeScript strict mode

## Testing

- Write tests for new features
- Maintain >80% coverage
- Run tests before submitting:

  ```bash
  make test
  ```

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```text
type(scope): description

feat(auth): add password reset endpoint
fix(api): handle null values in response
docs(readme): update installation instructions
test(users): add unit tests for user service
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

## Pull Request Process

1. Create a feature branch from `develop`
2. Make your changes with tests
3. Ensure all checks pass
4. Submit PR to `develop` branch
5. Wait for review

## Questions?

Open an issue or discussion for questions.
