#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export VALIDATOR_JAR
VALIDATOR_JAR=$("$repo_root/scripts/ensure-validator.sh")

python3 "$repo_root/scripts/check-upstream-corpus.py"
"$repo_root/scripts/test-en16931-rules.sh"
"$repo_root/scripts/test-kosit-rules.sh"
