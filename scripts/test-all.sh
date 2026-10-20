#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

python3 "$repo_root/scripts/repair-en16931-ubl.py" --check
"$repo_root/scripts/regenerate-factur-x-xslt.sh" --check
python3 scripts/check-configuration.py
python3 tools/regression-tests/test_api_runner.py
"$repo_root/scripts/test-rule-corpora.sh"
"$repo_root/validation-api.spec.sh"
