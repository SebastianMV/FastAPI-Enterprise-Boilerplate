# Contributing to FastAPI-Enterprise-Boilerplate

Thank you for considering contributing! This document provides guidelines.

## Contributor License Agreement (CLA)

**All contributors must sign the CLA before their first PR can be merged.**

The CLA grants the project maintainer the right to relicense contributions
(e.g., to a more permissive license) while you retain copyright of your work.

### How to sign:

1. Read the [CLA](CLA.md)
2. Add your name and GitHub username to [`.github/CLA-SIGNATORIES.md`](.github/CLA-SIGNATORIES.md)
3. Include that change in your first PR (or submit a separate PR)

A GitHub Action will verify your signature automatically on every PR.

> **Why a CLA?** The CLA ensures we can adjust the project license in the
> future without needing to contact every contributor individually.

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

1. **Sign the CLA** (one-time — see above)
2. Create a feature branch from `develop`
3. Make your changes with tests
4. Ensure all checks pass (CI + CLA verification)
5. Submit PR to `develop` branch
6. Wait for review

## Questions?

Open an issue or discussion for questions.
