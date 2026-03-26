# Production Deployment

This directory contains the production deployment artifacts for running `kiro-rs` on the VPS as an internal service for `CLIProxyAPI`.

## Topology

- `kiro-rs` does not publish any public host port.
- The service joins the external Docker network `cli-proxy-api-proxy`.
- `CLIProxyAPI` reaches it over container DNS as `http://kiro-rs:8990`.

## Server Layout

Recommended root on the VPS:

```text
/opt/kiro-rs/
  .env
  compose.production.yml
  data/config.json
  data/credentials.json
  data/aws-sso-cache/
  scripts/remote-deploy.sh
```

## One-Time Server Bootstrap

1. Copy this `deploy/` directory to `/opt/kiro-rs/`.
2. Copy `.env.example` to `.env`.
3. Ensure `SHARED_NETWORK_NAME=cli-proxy-api-proxy` unless you deliberately changed the CLIProxyAPI network name.
4. Create `data/config.json`.
5. Create `data/credentials.json`.
6. Optionally mount AWS SSO cache data into `data/aws-sso-cache/` if your credential bootstrap depends on it.

## Production Config Expectations

Your production `config.json` should listen on all container interfaces so other containers on the shared Docker network can reach it:

```json
{
  "host": "0.0.0.0",
  "port": 8990,
  "apiKey": "set-a-strong-runtime-api-key",
  "region": "us-east-1"
}
```

If you need the embedded admin UI/API for private operator use, set `adminApiKey` as well. This deployment does not expose it publicly.

## CLIProxyAPI Integration

After deployment, configure the relevant upstream in CLIProxyAPI to use:

```text
http://kiro-rs:8990
```

This works because both stacks share the same external Docker network.

## GHCR Notes

- The image is intended to publish to `ghcr.io/dovelanlan/kiro-rs`.
- After the first image publish, confirm the package visibility is `public` if you want the VPS to pull it without registry credentials.

## GitHub Environment Secrets

Recommended production environment secrets in this repository:

- `PRODUCTION_SSH_PRIVATE_KEY`
- `PRODUCTION_SSH_KNOWN_HOSTS`

Use the same deployment key strategy you used for the CLIProxyAPI repository, but note that secrets are repo-scoped and must also be configured here.
