# Troubleshooting Guide

## Build fails with "timeout exceeded"

The default build timeout is 15 minutes. Raise it with `build.timeout` in
`nimbus.yaml` (maximum 60 minutes). Large monorepos should enable the shared layer
cache by setting `build.cache: true`.

## Service returns 502 after deploy

The Gateway could not reach a healthy instance. Check:
1. The service listens on the port declared in `nimbus.yaml` (`port`, default 8080).
2. Health checks pass: the Scheduler probes `/healthz` every 10 seconds and restarts
   after 3 consecutive failures.
3. The instance is not out of memory — free tier instances only have 512 MB RAM.

## Deploy is stuck in "pending"

The Scheduler could not find a node with enough memory. Reduce the requested
resources or upgrade the tier. Run `nimbus status` to see per-environment health.

## Cold starts are slow

Free tier services sleep after 15 minutes of inactivity. The first request after
sleep takes about 3 seconds. Upgrade to Pro to keep instances warm.

## Rollback did not change behavior

Rollbacks restore the container image and configuration of a revision, but secrets
are not versioned. If a secret changed after the target revision, redeploy with the
correct secret value.

## Getting help

- Pro tier: email support, 24-hour response SLA.
- Enterprise: 1-hour response SLA with a named technical account manager.
- Free tier: community forum only.