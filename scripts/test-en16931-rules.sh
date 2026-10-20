#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
validator_jar=$("$repo_root/scripts/ensure-validator.sh")
exec python3 "$repo_root/tools/regression-tests/cen/run.py" "$repo_root" "$validator_jar"
