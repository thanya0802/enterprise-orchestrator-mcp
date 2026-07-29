# Auth Refactor Decision — January 2026

**Date:** 2026-01-15  
**Attendees:** Alice Chen (Tech Lead), Bob Martinez (Backend), Carol Wu (Security), David Kim (Frontend)

## Context

Our current session-based auth is causing scaling issues and doesn't support SSO for enterprise customers. We need to migrate to OAuth 2.0 + JWT before Q2.

## Decisions Made

1. **Adopt OAuth 2.0 with PKCE** for all client applications (web, mobile, CLI).
2. **JWT access tokens** with 15-minute expiry; refresh tokens stored in HttpOnly cookies.
3. **Auth service extraction**: Move auth logic from monolith into dedicated `auth-service` microservice.
4. **Migration timeline**: 6-week phased rollout starting February 2026.
5. **Backward compatibility**: Legacy session cookies supported for 90 days post-migration.

## Action Items

| Owner | Task | Due |
|-------|------|-----|
| Alice Chen | Draft ADR-002 and architecture diagram | 2026-01-22 |
| Bob Martinez | Spike on auth-service extraction | 2026-01-29 |
| Carol Wu | Security review of JWT implementation | 2026-02-05 |
| David Kim | Update frontend auth flow (PKCE) | 2026-02-12 |

## Open Questions

- Should we use Auth0 or build in-house? **Leaning Auth0** for MVP, revisit at scale.
- How do we handle service-to-service auth? **Proposal: mTLS + client credentials grant.**

## Related PRs

- PR #42 — Auth service scaffold (Bob Martinez, **open**, blocked on ADR approval)
- PR #38 — JWT middleware prototype (Alice Chen, merged)

## Notes

Carol flagged that the current refresh token rotation isn't implemented — this is a **blocker** for production. Bob is working on PR #42 to address the auth-service boundary.
