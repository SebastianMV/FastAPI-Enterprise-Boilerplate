# Architecture Overview

> 📖 For a comprehensive technical overview including architecture, features, and validation results, see [TECHNICAL_OVERVIEW.md](./TECHNICAL_OVERVIEW.md)

## Hexagonal Architecture (Ports & Adapters)

This project follows **Hexagonal Architecture** to achieve:

- **Testability**: Business logic can be tested without infrastructure
- **Flexibility**: Easy to swap providers (database, cache, email)
- **Maintainability**: Clear boundaries between layers

## Layer Structure

```text
┌─────────────────────────────────────────────────────────────┐
│                       API Layer                              │
│         (FastAPI endpoints, middleware, schemas)             │
│                                                              │
│  Responsibilities:                                           │
│  - HTTP request/response handling                            │
│  - Input validation (Pydantic schemas)                       │
│  - Authentication middleware                                 │
│  - Rate limiting                                             │
│  - Error response formatting                                 │
└─────────────────────────┬───────────────────────────────────┘
                          │ Calls
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   Application Layer                          │
│            (Use Cases, Application Services)                 │
│                                                              │
│  Responsibilities:                                           │
│  - Orchestrate domain logic                                  │
│  - Transaction management                                    │
│  - Call external services (via ports)                        │
│  - Emit domain events                                        │
└─────────────────────────┬───────────────────────────────────┘
                          │ Uses
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                     Domain Layer                             │
│     (Entities, Value Objects, Business Rules, Ports)        │
│                                                              │
│  Responsibilities:                                           │
│  - Core business logic                                       │
│  - Domain validation                                         │
│  - Define repository interfaces (ports)                      │
│  - NO external dependencies                                  │
└─────────────────────────┬───────────────────────────────────┘
                          │ Implemented by
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  Infrastructure Layer                        │
│    (Database, Cache, Email, External APIs, Adapters)        │
│                                                              │
│  Responsibilities:                                           │
│  - Implement repository interfaces                           │
│  - Database operations (SQLAlchemy)                          │
│  - External service integrations                             │
│  - Caching (Redis)                                           │
│  - Authentication (JWT)                                      │
└─────────────────────────────────────────────────────────────┘
```

## Dependency Rule

> **Dependencies always point inward**

```text
Infrastructure → Application → Domain ← Application ← Infrastructure
                                 ↑
                              (Pure)
```

- Domain layer has **NO dependencies** on other layers
- Application layer depends **only** on Domain
- Infrastructure implements interfaces defined in Domain

## Directory Mapping

```text
backend/app/
├── api/                    # API Layer
│   ├── v1/
│   │   └── endpoints/      # Route handlers
│   ├── middleware/         # HTTP middleware
│   └── deps.py             # Dependency injection
│
├── application/            # Application Layer
│   ├── use_cases/          # Business operations
│   └── services/           # Application services
│
├── domain/                 # Domain Layer (PURE)
│   ├── entities/           # Business entities
│   ├── value_objects/      # Immutable values
│   ├── exceptions/         # Domain errors
│   └── ports/              # Repository interfaces
│
└── infrastructure/         # Infrastructure Layer
    ├── database/           # SQLAlchemy models, repos
    ├── auth/               # JWT, password hashing
    ├── cache/              # Redis implementation
    └── observability/      # Logging, tracing
```

## Example Flow: User Login

```text
1. POST /api/v1/auth/login
   └── api/v1/endpoints/auth.py
       ├── Validate request (Pydantic)
       └── Call LoginUseCase

2. LoginUseCase
   └── application/use_cases/auth/login.py
       ├── Get user from UserRepository (port)
       ├── Verify password
       ├── Generate tokens
       └── Return TokenResponse

3. Domain
   └── domain/entities/user.py
       └── User.verify_password()

4. Infrastructure
   └── infrastructure/database/repositories/user_repository.py
       └── UserRepository.get_by_email() (implements port)
```

## Benefits Achieved

| Benefit | How |
| ------- | --- |
| **Testable** | Domain logic tested without DB |
| **Swappable** | Change DB by implementing new adapter |
| **Readable** | Clear layer responsibilities |
| **Scalable** | Each layer can scale independently |
| **Maintainable** | Changes isolated to single layer |
