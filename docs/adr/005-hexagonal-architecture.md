# ADR-005: Hexagonal Architecture (Ports & Adapters)

- **Date:** 2025-06-01
- **Status:** Accepted
- **Author:** Sebastián Muñoz

## Context

As an enterprise boilerplate intended to scale to large teams and long-lived projects, the
codebase architecture must:
- Keep business logic independent of web framework, database, and external services
- Allow testing business rules without spinning up infrastructure
- Enable swapping infrastructure components (e.g., PostgreSQL → MySQL, Redis → Memcached)
  without touching domain logic

## Decision

Adopt **Hexagonal Architecture** (Ports & Adapters):

```
backend/app/
├── domain/           # Core business logic (entities, ports, value objects, exceptions)
│   ├── entities/     # Domain models (NO SQLAlchemy, NO Pydantic schemas)
│   ├── ports/        # Abstract interfaces (repositories, services)
│   ├── value_objects/ # Immutable domain concepts
│   └── exceptions/   # Domain-specific errors
├── application/      # Use cases (orchestration, NO infrastructure details)
│   ├── use_cases/    # One class per business operation
│   └── services/     # Application services
├── infrastructure/   # Adapters (DB, cache, email, auth — implements ports)
│   ├── database/     # SQLAlchemy models, repositories
│   ├── auth/         # JWT, bcrypt, TOTP implementations
│   ├── cache/        # Redis adapter
│   └── ...
└── api/              # HTTP adapter (FastAPI endpoints — thin, no business logic)
    └── v1/
        ├── endpoints/  # Route handlers (validate → delegate → respond)
        └── schemas/    # Pydantic request/response models
```

**Key rule:** Endpoints are THIN — they validate input, call a use case, and return a response.
No business logic, no direct database queries, no complex conditional logic in endpoints.

## Consequences

### Positive

- **Testability** — domain and use cases tested with mocks, no DB needed
- **Framework independence** — business rules don't import FastAPI or SQLAlchemy
- **Clear boundaries** — each layer has a single responsibility
- **Onboarding** — new developers know where to put code based on what it does

### Negative

- **More files** — a simple CRUD operation touches 4+ files (endpoint, schema, use case, repository)
- **Indirection** — following a request through layers requires understanding the architecture
- **Over-engineering risk** — simple features may feel heavyweight

### Neutral

- Domain entities and SQLAlchemy models are separate (some duplication, but clear separation)
- Port interfaces defined in `domain/ports/` implemented in `infrastructure/`

## Alternatives Considered

### Traditional MVC / Fat Controllers

Put all logic in endpoint handlers. Rejected because:
- Endpoints become 200+ line monsters
- Business logic tied to HTTP concepts
- Untestable without full HTTP setup

### Clean Architecture (Uncle Bob)

Very similar to hexagonal but with stricter layer rules. Not adopted strictly because:
- The distinction between "Interface Adapters" and "Frameworks & Drivers" is overkill for this project size
- Hexagonal's port/adapter concept maps more naturally to Python's protocol/ABC pattern

### Domain-Driven Design (Full)

Full DDD with aggregates, bounded contexts, event sourcing. Rejected because:
- Over-engineering for a boilerplate project
- Adds significant complexity for marginal benefit at this scale
- Elements of DDD (entities, value objects, repositories) are adopted selectively

## References

- Alistair Cockburn: [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)
- `backend/app/domain/ports/`: Port definitions (10 port interfaces)
- `backend/app/infrastructure/`: Adapter implementations
- `backend/app/application/use_cases/`: Use case orchestrations
