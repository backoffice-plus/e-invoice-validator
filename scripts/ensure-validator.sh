#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
validator_jar="${VALIDATOR_JAR:-$repo_root/tools/regression-tests/target/validator-standalone.jar}"
expected_sha256='799e64befca97d4080e03608c80b85dd5a5ecc5f4ae4f35d1116ec2855b9a7c9'

verify() {
  python3 - "$1" "$expected_sha256" <<'PY'
import hashlib
import sys
from pathlib import Path

path = Path(sys.argv[1])
actual = hashlib.sha256(path.read_bytes()).hexdigest()
if actual != sys.argv[2]:
    raise SystemExit(f'Unexpected KoSIT Validator SHA-256 for {path}: {actual}')
PY
}

if [[ ! -f "$validator_jar" ]]; then
  if [[ -n "${VALIDATOR_JAR:-}" ]]; then
    echo "VALIDATOR_JAR does not exist: $validator_jar" >&2
    exit 1
  fi
  mkdir -p "$(dirname "$validator_jar")"
  temporary_jar=$(mktemp "${validator_jar}.XXXXXX")
  trap 'rm -f "$temporary_jar"' EXIT
  curl --fail --silent --show-error --location --retry 3 \
    --connect-timeout 10 --max-time 180 \
    --output "$temporary_jar" \
    'https://github.com/itplr-kosit/validator/releases/download/v1.6.3/validator-1.6.3-standalone.jar'
  verify "$temporary_jar"
  mv "$temporary_jar" "$validator_jar"
  trap - EXIT
else
  verify "$validator_jar"
fi

python3 - "$validator_jar" <<'PY'
import sys
from pathlib import Path
print(Path(sys.argv[1]).resolve())
PY
