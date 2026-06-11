#!/bin/bash
# Cloudflare Development Mode + Cache Purge
# Usage: ./scripts/cloudflare-dev-mode.sh

CLOUDFLARE_ZONE_ID="${CLOUDFLARE_ZONE_ID:?CLOUDFLARE_ZONE_ID env var is required}"
CLOUDFLARE_API_TOKEN="${CLOUDFLARE_API_TOKEN:?CLOUDFLARE_API_TOKEN env var is required}"

echo "Enabling Cloudflare Development Mode..."
curl -X PATCH "https://api.cloudflare.com/client/v4/zones/$CLOUDFLARE_ZONE_ID/settings/development_mode" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{"value":"on"}'

echo ""
echo "Purging Cloudflare cache..."
curl -X POST "https://api.cloudflare.com/client/v4/zones/$CLOUDFLARE_ZONE_ID/purge_cache" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{"purge_everything":true}'

echo ""
echo "Done! Development Mode enabled for 3 hours and cache purged."
