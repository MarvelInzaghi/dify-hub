#!/usr/bin/env bash
# Start the dify-hub backend on the host (anaconda Python 3.12, conda env "difyhub").
set -euo pipefail

CONDA_BASE=/home/a360/anaconda3
APP_DIR=/home/a360/dify-hub/server
PORT=8101

source "$CONDA_BASE/etc/profile.d/conda.sh"
conda activate difyhub
cd "$APP_DIR"

echo "Starting dify-hub backend on 0.0.0.0:${PORT} (conda env: difyhub)..."
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
