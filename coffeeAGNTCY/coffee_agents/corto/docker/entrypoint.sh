#!/usr/bin/env sh
set -eu

# Minimal entrypoint: always attempt to fetch the about-corto-exchange.properties


TAG="${ABOUT_RELEASE_TAG:-}"
ASSET="about-corto-exchange.properties"
BASE_URL="https://github.com/agntcy/coffeeAgntcy/releases/download"

if [ -z "$TAG" ] || [ "$TAG" = "unknown" ]; then
  echo "[entrypoint] ABOUT_RELEASE_TAG not set or unknown; using baked /app/about.properties."
else
  URL="${BASE_URL}/${TAG}/${ASSET}"
  echo "[entrypoint] Fetching: ${URL}"
  if curl -fsSL "$URL" -o /app/about.properties.tmp; then
    mv /app/about.properties.tmp /app/about.properties
    echo "[entrypoint] Updated /app/about.properties with tag $TAG"
  else
    echo "[entrypoint] Warning: failed to fetch ${URL}; using baked metadata." >&2
  fi
fi

exec "$@"
