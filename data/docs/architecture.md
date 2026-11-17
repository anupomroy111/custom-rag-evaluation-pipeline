# Nimbus Deploy — Architecture

The platform is composed of five core services, all running in a management cluster
separate from customer workloads.

## Gateway

Built on Envoy 1.29. Terminates TLS 1.3, enforces rate limits, and routes requests to
service instances. The Gateway performs automatic retries: up to 2 retries on 5xx
responses with a 250 ms backoff, but never retries non-idempotent methods (POST, PATCH).

## Scheduler

Written in Go 1.22. Uses a bin-packing strategy to place services on compute nodes,
preferring nodes with the most available memory. Health checks run every 10 seconds;
a service failing 3 consecutive checks is restarted automatically. The Scheduler
supports canary deployments: 10% of traffic is shifted to the new version for
5 minutes before full rollout.

## Builder

Uses BuildKit with a shared layer cache stored in S3-compatible object storage.
Builds run on ephemeral ARM64 or AMD64 nodes. The default build timeout is 15 minutes
and can be raised to a maximum of 60 minutes via `build.timeout` in `nimbus.yaml`.

## Store

Metadata lives in PostgreSQL 16 with streaming replication to a standby. Container
images and build caches live in object storage with lifecycle rules that delete
untagged images after 30 days.

## Event Bus

NATS JetStream connects the services. Every deployment emits events on the
`nimbus.deploy.*` subject; audit consumers retain events for 90 days.