# Sprint Retrospective — March 2026

**Sprint:** Sprint 16 (March 3–14, 2026)  
**Facilitator:** David Kim

## What Went Well

- Auth service scaffold merged (PR #42) after ADR-002 approval
- JWT middleware passing security review
- Frontend PKCE flow demo'd successfully in staging

## What Didn't Go Well

- API v2 work delayed — still waiting on auth-service production deploy
- Integration tests flaky around token refresh
- Confluence docs out of date (nobody owns doc updates)

## Decisions from Retro

1. **Assign doc ownership**: Eve Nakamura owns API docs; Alice owns architecture ADRs.
2. **Freeze API v2** until auth-service is in production (target: March 28).
3. **Add refresh token rotation** as P0 for Sprint 17 — Carol Wu to review PR #51.

## Action Items

- Bob: Fix flaky refresh token tests by March 18
- Alice: Update ADR-002 with Auth0 decision (final)
- David: Ship PKCE to production behind feature flag

## Metrics

- Velocity: 34 points (target: 38)
- PR cycle time: 2.3 days avg (improved from 3.1)
- Open blockers: 2 (refresh token rotation, API v2 dependency)
