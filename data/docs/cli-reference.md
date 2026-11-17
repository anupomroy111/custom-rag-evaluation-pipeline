# Nimbus CLI Reference

The CLI binary is `nimbus`. Install it with `curl -fsSL https://get.nimbus.app | sh`.
Authentication uses `nimbus login`, which opens a browser-based device flow.

## nimbus deploy

Deploys the service described by `nimbus.yaml` in the current directory.

Flags:
- `--env <dev|staging|prod>` — target environment (default: `dev`).
- `--region <region>` — override the project default region.
- `--timeout <duration>` — client-side wait for rollout (default: `10m`).
- `--dry-run` — validate configuration and print the execution plan without deploying.

## nimbus rollback

Rolls a service back to a previous revision.

- `nimbus rollback --env prod --to <revision>` rolls back to a specific revision.
- Without `--to`, the immediately previous revision is used.
- Rollbacks keep the last 10 revisions; older revisions are garbage-collected.

## nimbus logs

Streams logs: `nimbus logs --env prod --follow`. Without `--follow` it prints the
last 200 lines. Add `--since 1h` to limit the time window.

## nimbus secrets

- `nimbus secrets set KEY=value --env prod` stores an encrypted secret.
- `nimbus secrets list` shows names only, never values.
- Secrets are injected into containers as environment variables at startup.

## nimbus status

Prints the current revision, health, and URL of every environment in the project.
Exit code 0 means all environments are healthy; exit code 2 means at least one
environment is degraded.