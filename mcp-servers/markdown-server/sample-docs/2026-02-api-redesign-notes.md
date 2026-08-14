# API Redesign Notes — February 2026

**Sprint:** Sprint 14  
**Author:** Alice Chen

## Summary

Following the auth refactor decision, we're redesigning the public API to be RESTful v2 with consistent error handling and OpenAPI 3.1 specs.

## Key Changes

1. **Version prefix**: All endpoints move from `/api/v1/` to `/api/v2/`.
2. **Unified error format**: RFC 7807 Problem Details for all 4xx/5xx responses.
3. **Pagination**: Cursor-based pagination replaces offset/limit.
4. **Auth headers**: Bearer token only; no API keys in query strings.

## Dependencies

- Blocked by auth refactor (OAuth 2.0 must ship first).
- PR #45 tracks the v2 route scaffolding.

## Timeline

- Design review: 2026-02-20
- Implementation start: 2026-03-01 (depends on auth-service merge)

## Stakeholders

- **Alice Chen** — API design lead
- **Eve Nakamura** — Documentation and developer experience
- **Bob Martinez** — Backend implementation
