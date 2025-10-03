#!/usr/bin/env sh
set -eu

# Fetch the about-corto-exchange.properties


TAG="${ABOUT_RELEASE_TAG:-}"
ASSET="about-corto-exchange.properties"
BASE_URL="https://github.com/agntcy/coffeeAgntcy/releases"

if [ -z "$TAG" ] || [ "$TAG" = "unknown" ] || [ "$TAG" = "latest" ]; then
  URL="${BASE_URL}/latest/download/${ASSET}"
  echo "[entrypoint] ABOUT_RELEASE_TAG is '${TAG:-unset}'. Fetching latest: ${URL}"
else
  URL="${BASE_URL}/download/${TAG}/${ASSET}"
  echo "[entrypoint] Fetching: ${URL}"
fi

if curl -fsSL "$URL" -o /app/about.properties.tmp; then
  mv /app/about.properties.tmp /app/about.properties
  echo "[entrypoint] Updated /app/about.properties"
else
  echo "[entrypoint] Warning: failed to fetch ${URL}; using baked metadata." >&2
fi

exec "$@"
