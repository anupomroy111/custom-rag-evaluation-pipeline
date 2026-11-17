# Quotas and Pricing

## Free tier

- Up to 3 projects per account.
- 512 MB RAM and 0.5 vCPU per service instance.
- 100 builds per month; extra builds are rejected until the next billing cycle.
- Services on the free tier sleep after 15 minutes without traffic and cold-start
  in roughly 3 seconds.
- Community support only.

## Pro tier — $29 per user per month

- Unlimited projects.
- Up to 8 GB RAM and 4 vCPU per instance.
- 2,000 builds per month, then $0.01 per additional build.
- No sleep behavior; instances stay warm.
- Email support with a 24-hour response SLA.
- Custom domains with automatic certificate management.

## Enterprise tier — custom pricing

- Dedicated compute nodes and VPC peering.
- 99.99% uptime SLA (the standard platform SLA is 99.95%).
- SAML SSO and SCIM provisioning.
- 1-hour response SLA with a named technical account manager.

## Hard limits (all tiers)

- Maximum container image size: 2 GB compressed.
- Maximum request body size at the Gateway: 10 MB.
- Maximum environment variables per service: 100.
- Build concurrency: 2 simultaneous builds per project (Enterprise: 10).