#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
validator_jar="$("$project_dir/scripts/ensure-validator.sh")"
exec python3 "$project_dir/tools/regression-tests/kosit/run.py" --validator-jar "$validator_jar" "$@"
