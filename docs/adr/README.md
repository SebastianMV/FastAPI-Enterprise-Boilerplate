# Architecture Decision Records (ADR)

This directory contains Architecture Decision Records for the FastAPI-Enterprise-Boilerplate project.

## What is an ADR?

An ADR documents a significant architectural decision along with its context and consequences.
The goal is to **prevent accidental reversion** of deliberate decisions by future contributors
(including AI agents) who may not know _why_ something was done a certain way.

## Format

Each ADR follows the template in [000-template.md](000-template.md):

| Section                     | Purpose                                           |
| --------------------------- | ------------------------------------------------- |
| **Status**                  | Accepted, Deprecated, or Superseded               |
| **Context**                 | The problem or situation that led to the decision |
| **Decision**                | What was decided                                  |
| **Consequences**            | Trade-offs, benefits, and things to watch         |
| **Alternatives Considered** | What was rejected and why                         |

## Index

| ADR                                           | Decision                                          | Status   |
| --------------------------------------------- | ------------------------------------------------- | -------- |
| [001](001-httponly-cookies-for-jwt.md)        | HttpOnly cookies for JWT storage                  | Accepted |
| [002](002-csrf-double-submit-pattern.md)      | CSRF double-submit with X-CSRF-Token              | Accepted |
| [003](003-centralized-structured-logging.md)  | Centralized `get_logger()` for structured logging | Accepted |
| [004](004-tenant-isolation-via-dependency.md) | `CurrentTenantId` dependency for tenant isolation | Accepted |
| [005](005-hexagonal-architecture.md)          | Hexagonal (Ports & Adapters) architecture         | Accepted |
| [006](006-semgrep-custom-rules.md)            | Custom Semgrep rules from 24 audits as pre-commit | Accepted |

## When to Write an ADR

Write a new ADR when:

- A decision affects 3+ files or modules
- The decision involves a security trade-off
- Someone might reasonably question "why not do it the other way?"
- An AI agent or new contributor could accidentally revert it

## Naming Convention

`NNN-short-description.md` where NNN is a zero-padded sequential number.
