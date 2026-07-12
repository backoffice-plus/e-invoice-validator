#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
pom="$repo_root/tools/factur-x-xslt/pom.xml"
generated_root="$repo_root/tools/factur-x-xslt/target/generated-xslt"
schema_root="$repo_root/configuration/factur-x/1.09/Schema/factur-x-1.09"
maven_command="${MAVEN_COMMAND:-mvn}"
check_only=false

if [[ "${1:-}" == '--check' ]]; then
  check_only=true
elif [[ $# -gt 0 ]]; then
  echo "Usage: $0 [--check]" >&2
  exit 2
fi

python3 "$repo_root/tools/factur-x-xslt/restore-rule-ids.py"

"$maven_command" -q -f "$pom" clean generate-resources

profiles=(
  '0_Factur-X_1.09_MINIMUM|Factur-X_1.09_MINIMUM.xslt|_XSLT_MINIMUM/FACTUR-X_MINIMUM.xslt'
  '1_Factur-X_1.09_BASICWL|Factur-X_1.09_BASICWL.xslt|_XSLT_BASIC-WL/FACTUR-X_BASIC-WL.xslt'
  '2_Factur-X_1.09_BASIC|Factur-X_1.09_BASIC.xslt|_XSLT_BASIC/FACTUR-X_BASIC.xslt'
  '3_Factur-X_1.09_EN16931|Factur-X_1.09_EN16931.xslt|_XSLT_EN16931/FACTUR-X_EN16931.xslt'
  '4_Factur-X_1.09_EXTENDED|Factur-X_1.09_EXTENDED.xslt|_XSLT_EXTENDED/FACTUR-X_EXTENDED.xslt'
)

runtime_codelists=(
  '0_Factur-X_1.09_MINIMUM|Factur-X_1.09_MINIMUM_codedb.xml|_XSLT_MINIMUM/Factur-X_1.09_MINIMUM_codedb.xml'
  '1_Factur-X_1.09_BASICWL|Factur-X_1.09_BASICWL_codedb.xml|_XSLT_BASIC-WL/Factur-X_1.09_BASICWL_codedb.xml'
  '2_Factur-X_1.09_BASIC|Factur-X_1.09_BASIC_codedb.xml|_XSLT_BASIC/Factur-X_1.09_BASIC_codedb.xml'
  '3_Factur-X_1.09_EN16931|Factur-X_1.09_EN16931_codedb.xml|_XSLT_EN16931/Factur-X_1.09_EN16931_codedb.xml'
  '4_Factur-X_1.09_EXTENDED|Factur-X_1.09_EXTENDED_codedb.xml|_XSLT_EXTENDED/FACTUR-X_EXTENDED_codedb.xml'
)

for profile in "${profiles[@]}"; do
  IFS='|' read -r profile_dir generated_name target_path <<< "$profile"
  generated="$generated_root/$profile_dir/$generated_name"
  target="$schema_root/$profile_dir/$target_path"

  if [[ ! -f "$generated" || ! -f "$target" ]]; then
    echo "Missing generated or vendored XSLT for $profile_dir" >&2
    exit 1
  fi

  if $check_only; then
    if ! cmp -s "$generated" "$target"; then
      echo "Vendored XSLT is stale: ${target#"$repo_root/"}" >&2
      exit 1
    fi
  else
    cp "$generated" "$target"
    echo "Updated ${target#"$repo_root/"}"
  fi
done

for codelist in "${runtime_codelists[@]}"; do
  IFS='|' read -r profile_dir source_path target_path <<< "$codelist"
  source="$schema_root/$profile_dir/$source_path"
  target="$schema_root/$profile_dir/$target_path"

  if [[ ! -f "$source" ]]; then
    echo "Missing source codelist for $profile_dir" >&2
    exit 1
  fi

  if $check_only; then
    if [[ ! -f "$target" ]] || ! cmp -s "$source" "$target"; then
      echo "Missing or stale runtime codelist: ${target#"$repo_root/"}" >&2
      exit 1
    fi
  else
    cp "$source" "$target"
    echo "Updated ${target#"$repo_root/"}"
  fi
done

if $check_only; then
  echo 'All vendored Factur-X XSLT validators and runtime codelists are reproducible.'
fi
