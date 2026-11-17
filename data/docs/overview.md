# Nimbus Deploy — Platform Overview

Nimbus Deploy is an internal developer platform (IDP) that lets product teams ship
containerized services without managing Kubernetes directly. Teams describe a service
in a single `nimbus.yaml` file, and the platform handles building, scheduling,
networking, and observability.

## Key facts

- General availability: March 2024.
- Production uptime SLA: 99.95% measured monthly.
- Available regions: `ap-south-1` (Mumbai), `eu-west-2` (London), `us-east-1` (Virginia).
- The default region for new projects is `ap-south-1`.
- Every service gets a public HTTPS URL of the form `https://<service>.<project>.nimbus.app`.

## Core workflow

1. Developer runs `nimbus deploy` from a repository containing `nimbus.yaml`.
2. The Builder compiles the container image using BuildKit.
3. The Scheduler places the service on a compute node in the selected region.
4. The Gateway routes traffic and terminates TLS.
5. Metrics and logs stream to the built-in dashboard within 30 seconds of deployment.

## Environments

Each project has three environments: `dev`, `staging`, and `prod`. Promotions between
environments are manual by default; automatic promotion from staging to prod can be
enabled with `auto_promote: true` in `nimbus.yaml`. The `dev` environment is wiped and
rebuilt every Sunday at 02:00 UTC.