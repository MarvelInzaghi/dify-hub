#!/usr/bin/env bash
# Build the two dify-hub images and export them as tarballs for offline distribution.
# Run on a machine with Docker + internet access.
set -euo pipefail

cd "$(dirname "$0")/.."

TAG=0.1.0

echo "==> Building dify-hub-api:${TAG} ..."
docker build -t "dify-hub-api:${TAG}" server/

echo "==> Building dify-hub-web:${TAG} ..."
docker build -t "dify-hub-web:${TAG}" web/

echo "==> Saving images to deploy/ ..."
docker save "dify-hub-api:${TAG}" -o "deploy/dify-hub-api.tar"
docker save "dify-hub-web:${TAG}" -o "deploy/dify-hub-web.tar"

echo "==> Done. On the offline host:"
echo "      docker load -i deploy/dify-hub-api.tar"
echo "      docker load -i deploy/dify-hub-web.tar"
echo "      cd deploy && docker compose up -d"
