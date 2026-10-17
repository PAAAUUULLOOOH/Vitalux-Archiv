#!/usr/bin/env bash
# Launch ONLY the native Qt Quick prototype. Stable Vitalux remains unchanged.
set -euo pipefail
cd -- "$(dirname -- "$0")"
exec bash ./run.sh --gpu-preview "$@"
