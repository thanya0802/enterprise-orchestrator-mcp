# Onboarding: Auth Service Development

**Last updated:** 2026-02-01  
**Maintainer:** Bob Martinez

## Quick Start

```bash
git clone https://github.com/example/auth-service
cd auth-service
docker compose up -d postgres
uv sync
uv run pytest
```

## Architecture Overview

The auth-service handles:
- OAuth 2.0 authorization code + PKCE flows
- JWT issuance and validation
- Refresh token rotation (see PR #51)
- User session management

## Key Contacts

- **Alice Chen** — architecture questions, ADRs
- **Bob Martinez** — auth-service implementation
- **Carol Wu** — security reviews
- **David Kim** — frontend integration

## Current Open Work

- PR #51: Refresh token rotation (Bob, blocked on security review)
- PR #48: Frontend PKCE feature flag (David)
- PR #45: API v2 scaffolding (blocked on auth production deploy)

## Related Docs

- [Auth Refactor Decision](../2026-01-auth-refactor-decision.md)
- [ADR-001 Database Choice](../architecture-decisions/adr-001-database-choice.md)
- [ADR-002 OAuth Provider](../architecture-decisions/adr-002-oauth-provider.md)
