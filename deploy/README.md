# Production Deployment

This directory contains the production deployment artifacts for running `kiro-rs` on the VPS as an internal service for `CLIProxyAPI`.

## Topology

- `kiro-rs` does not publish any public internet host port.
- The service joins the external Docker network `cli-proxy-api-proxy`.
- `CLIProxyAPI` reaches it over container DNS as `http://kiro-rs:8990`.
- The admin UI/API can be reached privately over the Tailscale IP and a dedicated host port.

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
4. Set `TAILSCALE_BIND_IP` to the VPS Tailscale IPv4 and `TAILSCALE_ADMIN_PORT` to the management port you want to expose only on Tailscale.
5. Create `data/config.json`.
6. Create `data/credentials.json`.
7. Optionally mount AWS SSO cache data into `data/aws-sso-cache/` if your credential bootstrap depends on it.

## Production Config Expectations

Your production `config.json` should listen on all container interfaces so other containers on the shared Docker network can reach it:

```json
{
  "host": "0.0.0.0",
  "port": 8990,
  "apiKey": "set-a-strong-runtime-api-key",
  "adminApiKey": "set-a-strong-admin-api-key",
  "region": "us-east-1"
}
```

Setting `adminApiKey` enables the embedded admin UI/API. This deployment exposes it only on the Tailscale-bound host port, not on the public internet.

## CLIProxyAPI Integration

After deployment, configure the relevant upstream in CLIProxyAPI to use:

```text
http://kiro-rs:8990
```

This works because both stacks share the same external Docker network.

## Private Admin Access

After deployment, from a device already connected to the same tailnet:

- Admin UI: `http://100.67.99.9:18990/admin/`
- Admin API base: `http://100.67.99.9:18990/api/admin/`

You can also use the MagicDNS/Tailnet hostname form if enabled on your devices.

The admin UI/API requires the configured `adminApiKey`.

## GHCR Notes

- The image is intended to publish to `ghcr.io/dovelanlan/kiro-rs`.
- After the first image publish, confirm the package visibility is `public` if you want the VPS to pull it without registry credentials.

## GitHub Environment Secrets

Recommended production environment secrets in this repository:

- `PRODUCTION_SSH_PRIVATE_KEY`
- `PRODUCTION_SSH_KNOWN_HOSTS`

Use the same deployment key strategy you used for the CLIProxyAPI repository, but note that secrets are repo-scoped and must also be configured here.
