# Security Review — JWT & Refresh Token Implementation

**Reviewer:** Carol Wu  
**Date:** 2026-02-10  
**Scope:** PR #38 (merged), PR #51 (in review)

## Findings

### PR #38 (JWT Middleware) — APPROVED

- Token validation uses RS256 with key rotation support
- Clock skew tolerance set to 30 seconds (acceptable)
- No sensitive data in JWT claims

### PR #51 (Refresh Token Rotation) — CHANGES REQUESTED

1. **Must implement reuse detection** — if a refresh token is used twice, revoke all sessions for that user
2. **Store token hashes only** — never persist raw refresh tokens
3. **Add rate limiting** on `/oauth/token` endpoint

## Blockers for Production

- PR #51 must address items 1–3 before merge
- Auth0 DPA must be signed (legal, ETA March 5)
- Pen test scheduled March 15

## Assigned To

Bob Martinez owns PR #51 fixes. Carol Wu will re-review by March 12.

## Related Decisions

- Auth refactor (Jan 2026) — refresh token rotation was flagged as blocker
- ADR-002 — Auth0 integration depends on this review passing
