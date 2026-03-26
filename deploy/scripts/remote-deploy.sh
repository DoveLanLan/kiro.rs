#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/compose.production.yml"

mkdir -p "$ROOT_DIR/data/aws-sso-cache"

if [[ ! -f "$ROOT_DIR/.env" && -f "$ROOT_DIR/.env.example" ]]; then
  cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
fi

if [[ ! -f "$ROOT_DIR/data/config.json" ]]; then
  echo "error: missing $ROOT_DIR/data/config.json" >&2
  exit 1
fi

if [[ ! -f "$ROOT_DIR/data/credentials.json" ]]; then
  echo "error: missing $ROOT_DIR/data/credentials.json" >&2
  exit 1
fi

if [[ -z "${SHARED_NETWORK_NAME:-}" ]]; then
  echo "error: SHARED_NETWORK_NAME must be set" >&2
  exit 1
fi

if ! docker network inspect "$SHARED_NETWORK_NAME" >/dev/null 2>&1; then
  echo "error: required docker network '$SHARED_NETWORK_NAME' not found" >&2
  echo "deploy CLIProxyAPI first or create the shared network before deploying kiro-rs" >&2
  exit 1
fi

: "${KIRO_RS_IMAGE:?KIRO_RS_IMAGE must be set}"

cd "$ROOT_DIR"
docker compose -f "$COMPOSE_FILE" pull
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans
docker compose -f "$COMPOSE_FILE" ps
