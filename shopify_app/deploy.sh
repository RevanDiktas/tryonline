#!/usr/bin/env bash
# Deploy Tryon theme app extension to Shopify.
#
# Why copy to /tmp? The project may live on an external volume (/Volumes/Expansion).
# macOS creates AppleDouble (._*) files on such volumes; the Shopify CLI includes
# them in the bundle and validation fails. We copy to /tmp, strip all ._*, and
# do NOT copy the cached .shopify/deploy-bundle so the CLI builds a fresh bundle.
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY_DIR="/tmp/tryon-shopify-deploy"

echo "Preparing deploy from main disk (avoids macOS ._* on external volume)..."

# 1. Clean source of all AppleDouble files (they get recreated on external volumes)
find "$SCRIPT_DIR" -name '._*' -type f -delete 2>/dev/null || true
find "$SCRIPT_DIR" -name '._*' -type d -empty -delete 2>/dev/null || true

# 2. Fresh copy to /tmp; do NOT copy .shopify so the CLI builds the bundle in /tmp (main disk)
#    If we copy .shopify, the CLI may write the bundle to the original project path (external
#    volume), where macOS then creates ._* and validation fails.
rm -rf "$DEPLOY_DIR"
mkdir -p "$DEPLOY_DIR"
rsync -a \
  --exclude='._*' \
  --exclude='**/._*' \
  --exclude='.DS_Store' \
  --exclude='node_modules' \
  --exclude='.shopify' \
  "$SCRIPT_DIR/" "$DEPLOY_DIR/"

cd "$DEPLOY_DIR"

# 3. Strip any ._* that might have been created during copy
find . -name '._*' -type f -delete 2>/dev/null || true
find . -name '._*' -type d -delete 2>/dev/null || true
rm -f extensions/tryon-widget/._* \
      extensions/tryon-widget/blocks/._* \
      extensions/tryon-widget/locales/._* \
      extensions/tryon-widget/assets/._* \
      2>/dev/null || true

# 5. Prevent macOS from creating ._* when CLI builds the bundle
export COPYFILE_DISABLE=1

# 6. Force CLI to use this copy (not the original project path) so the bundle is built in /tmp
echo "Deploying from $DEPLOY_DIR ..."
shopify app deploy --path "$DEPLOY_DIR"

echo "Done. You can remove $DEPLOY_DIR later if you want (rm -rf $DEPLOY_DIR)."
