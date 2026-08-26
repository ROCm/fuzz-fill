#!/usr/bin/env bash
# Reduction: scaffold and optionally run batch-from-coverage for the first N gap-fill hits.
#
# Thin wrapper around: python -m reduce batch-from-coverage

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# shellcheck source=scripts/lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

cd "$REPO_ROOT"
activate_venv_if_present "$REPO_ROOT"

exec python -m reduce batch-from-coverage "$@"
