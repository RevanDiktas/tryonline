#!/usr/bin/env bash
# Deploy Tryon app config + extensions to Shopify (Partners).
# Requires: Node >= 20.10, Shopify CLI (npm install -g @shopify/cli)
set -e
cd "$(dirname "$0")"
# Remove macOS resource-fork files so theme-check doesn't fail on ._* in bundle
find extensions -name '._*' -type f -delete 2>/dev/null || true
find extensions -name '._*' -type d -empty -delete 2>/dev/null || true
shopify app deploy
