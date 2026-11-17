# Security Policy

## Encryption

- Data in transit: TLS 1.3 everywhere; TLS 1.2 is disabled at the Gateway.
- Data at rest: AES-256. PostgreSQL volumes and object storage buckets are encrypted
  with platform-managed keys; Enterprise customers may bring their own keys (BYOK).

## Secrets management

Application secrets are stored in HashiCorp Vault and injected as environment
variables at container startup. Secret values are never written to logs or returned
by the API. Rotating a secret requires a redeploy to take effect.

## Access control

- Role-based access control with three roles: `viewer`, `developer`, `admin`.
- Only `admin` can deploy to `prod` or manage secrets.
- SAML SSO is available on the Enterprise tier; all tiers support TOTP two-factor
  authentication.

## Audit and compliance

- Audit logs are retained for 90 days and exportable to S3.
- The platform is SOC 2 Type II certified (report available under NDA).
- Vulnerability scans run on every base image weekly; critical CVEs must be patched
  within 72 hours.

## Incident response

Severity 1 incidents page the on-call engineer immediately and require a status
update every 30 minutes. Postmortems are published internally within 5 business days.