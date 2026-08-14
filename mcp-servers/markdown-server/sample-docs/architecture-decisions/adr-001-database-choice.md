# ADR-001: Database Choice for Auth Service

**Status:** Accepted  
**Date:** 2026-01-08  
**Deciders:** Alice Chen, Bob Martinez, Carol Wu

## Context

The new auth-service needs a datastore for users, sessions, refresh tokens, and OAuth client registrations.

## Decision

We will use **PostgreSQL 16** with the following rationale:

- Team expertise (existing Postgres ops runbooks)
- ACID compliance for token rotation
- JSONB for flexible OAuth client metadata
- Managed option: AWS RDS (staging/prod), Docker Postgres (local)

## Alternatives Considered

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| PostgreSQL | ACID, team knows it | Vertical scaling limits | **Selected** |
| MongoDB | Flexible schema | Weaker consistency for tokens | Rejected |
| DynamoDB | Serverless scaling | New ops burden | Rejected |

## Consequences

- Bob Martinez sets up RDS instance and migration tooling (Flyway)
- Refresh token table needs careful indexing (user_id, token_hash)
- Connection pooling via PgBouncer in production

## Related

- Auth refactor decision (2026-01-15)
- PR #42 — auth-service uses Postgres migrations
