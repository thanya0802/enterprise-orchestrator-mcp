# ADR-002: OAuth Provider Selection

**Status:** Proposed (pending final approval)  
**Date:** 2026-01-22  
**Deciders:** Alice Chen, Carol Wu, Bob Martinez

## Context

ADR-001 established Postgres for auth-service storage. We must choose an OAuth 2.0 identity provider for enterprise SSO.

## Decision (Proposed)

Use **Auth0** for MVP with a migration path to self-hosted Keycloak if costs exceed $2K/month.

## Implementation Plan

1. Auth0 tenant for staging (Sprint 15)
2. Custom claims for org_id and roles
3. Auth-service validates JWTs via Auth0 JWKS endpoint
4. Feature flag `auth.auth0_enabled` for gradual rollout

## Blockers

- Legal review of Auth0 DPA (in progress — Carol Wu)
- PR #42 blocked until this ADR is accepted
- Enterprise customer Acme Corp requires SAML — Auth0 supports this

## Owners

- **Alice Chen** — ADR author, architecture
- **Bob Martinez** — auth-service integration (PR #42, PR #51)
- **Carol Wu** — security and compliance sign-off
