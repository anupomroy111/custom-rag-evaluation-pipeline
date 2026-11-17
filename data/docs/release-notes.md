# Release Notes

## v2.4.0 — 2026-09-10

- ARM64 build nodes are now available in all regions; select with `build.arch: arm64`.
- Canary deployments are generally available (10% traffic for 5 minutes).
- `nimbus logs --since` flag added.
- Gateway upgraded to Envoy 1.29.

## v2.3.1 — 2026-07-22

- Fixed a bug where rollbacks restored stale environment variables.
- Build cache hit rate improved by 18% after switching to zstd compression.

## v2.3.0 — 2026-06-05

- Custom domains with automatic certificates for Pro and Enterprise.
- SCIM provisioning for Enterprise.
- PostgreSQL upgraded from 15 to 16.

## v2.2.0 — 2026-04-18

- `nimbus deploy --dry-run` added.
- Audit log export to S3.
- Maximum request body size raised from 5 MB to 10 MB.

## v2.1.0 — 2026-02-27

- Two-factor authentication (TOTP) for all tiers.
- Dev environment weekly rebuild introduced (Sundays 02:00 UTC).