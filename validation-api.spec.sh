#!/usr/bin/env bash

set -uo pipefail

API_URL="${API_URL:-http://localhost:8888}"
API_URL="${API_URL%/}"
CONNECT_TIMEOUT_SECONDS="${CONNECT_TIMEOUT_SECONDS:-5}"
REQUEST_TIMEOUT_SECONDS="${REQUEST_TIMEOUT_SECONDS:-60}"
READINESS_TIMEOUT_SECONDS="${READINESS_TIMEOUT_SECONDS:-120}"
FACTUR_X_X20_CANARY="${FACTUR_X_X20_CANARY:-}"
VERBOSE=false

ACCEPTED_RECOMMENDATIONS=(
  'Bewertung: Es wird empfohlen das Dokument anzunehmen und weiter zu verarbeiten.'
  'Bewertung: Es wird empfohlen das Dokument anzunehmen und zu verarbeiten, da die vorhandenen Fehler derzeit toleriert werden.'
)

REJECTED_RECOMMENDATIONS=(
  'Bewertung: Es wird empfohlen das Dokument nicht anzunehmen.'
  'Bewertung: Es wird empfohlen das Dokument zurückzuweisen.'
)

while getopts 'v' opt; do
  case "$opt" in
    v)
      VERBOSE=true
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      exit 2
      ;;
  esac
done

wait_for_api() {
  local deadline=$((SECONDS + READINESS_TIMEOUT_SECONDS))
  local health=''

  echo "Waiting for validator API at $API_URL ..."
  while ((SECONDS < deadline)); do
    if health=$(curl --silent --show-error --fail \
      --connect-timeout "$CONNECT_TIMEOUT_SECONDS" \
      --max-time "$CONNECT_TIMEOUT_SECONDS" \
      "$API_URL/server/health" 2>/dev/null) && \
      grep -Fq '<ns2:status>UP</ns2:status>' <<< "$health"; then
      echo 'Validator API is ready.'
      return 0
    fi
    sleep 1
  done

  echo "Validator API did not become ready within ${READINESS_TIMEOUT_SECONDS}s." >&2
  return 1
}

get_response() {
  local file=$1
  local response_file
  local error_file
  local curl_exit=0

  response_file=$(mktemp)
  error_file=$(mktemp)

  RESPONSE_STATUS=$(curl --silent --show-error \
    --connect-timeout "$CONNECT_TIMEOUT_SECONDS" \
    --max-time "$REQUEST_TIMEOUT_SECONDS" \
    --request POST \
    --header 'Content-Type: application/xml' \
    --data-binary "@$file" \
    --output "$response_file" \
    --write-out '%{http_code}' \
    "$API_URL" 2>"$error_file") || curl_exit=$?

  RESPONSE_BODY=$(<"$response_file")
  RESPONSE_ERROR=$(<"$error_file")
  rm -f "$response_file" "$error_file"

  if ((curl_exit != 0)); then
    RESPONSE_STATUS=${RESPONSE_STATUS:-000}
    return 1
  fi

  return 0
}

contains_recommendation() {
  local body=$1
  shift
  local recommendation

  for recommendation in "$@"; do
    if grep -Fq "$recommendation" <<< "$body"; then
      return 0
    fi
  done

  return 1
}

is_valid_file() {
  local file=$1
  local valid=true
  local error_messages=()

  if ! get_response "$file"; then
    valid=false
    error_messages+=("Request failed: ${RESPONSE_ERROR:-unknown curl error}")
  fi

  if [[ "$RESPONSE_STATUS" != '200' ]]; then
    valid=false
    error_messages+=("Status code: expected 200, got $RESPONSE_STATUS")
  fi

  if ! contains_recommendation "$RESPONSE_BODY" "${ACCEPTED_RECOMMENDATIONS[@]}"; then
    valid=false
    error_messages+=('Expected acceptance recommendation was not found')
  fi

  if $valid; then
    if $VERBOSE; then
      echo "✅ PASSED: $file"
    fi
    return 0
  fi

  echo "❌ FAILED: $file"
  local message
  for message in "${error_messages[@]}"; do
    echo "   - $message"
  done
  return 1
}

is_invalid_file() {
  local file=$1
  local valid=true
  local error_messages=()

  if ! get_response "$file"; then
    valid=false
    error_messages+=("Request failed: ${RESPONSE_ERROR:-unknown curl error}")
  fi

  if [[ "$RESPONSE_STATUS" != '406' ]]; then
    valid=false
    error_messages+=("Status code: expected 406, got $RESPONSE_STATUS")
  fi

  if ! contains_recommendation "$RESPONSE_BODY" "${REJECTED_RECOMMENDATIONS[@]}"; then
    valid=false
    error_messages+=('Expected rejection recommendation was not found')
  fi

  if $valid; then
    if $VERBOSE; then
      echo "✅ PASSED: $file"
    fi
    return 0
  fi

  echo "❌ FAILED: $file"
  local message
  for message in "${error_messages[@]}"; do
    echo "   - $message"
  done
  return 1
}

process_folder() {
  local folder=$1
  local test_function=$2
  local success_count=0
  local fail_count=0
  local tested_count=0
  local file

  while IFS= read -r -d '' file; do
    tested_count=$((tested_count + 1))
    if $VERBOSE; then
      echo "Testing: $file"
    fi

    if "$test_function" "$file"; then
      success_count=$((success_count + 1))
    else
      fail_count=$((fail_count + 1))
    fi
  done < <(find "$folder" -type f -iname '*.xml' -print0)

  echo "✅ Passed: $success_count"
  echo "❌ Failed: $fail_count"
  echo ''

  if ((tested_count == 0)); then
    echo "No XML test files found in $folder" >&2
    return 1
  fi

  ((fail_count == 0))
}

test_valid_files() {
  local folder=${1:-'./test-data/valid-files'}

  echo '⏳ Testing files expected to be valid...'
  echo '   Checking for status code 200 and an acceptance recommendation'
  process_folder "$folder" is_valid_file
}

test_invalid_files() {
  local folder=${1:-'./test-data/invalid-files'}

  echo '⏳ Testing files expected to be invalid...'
  echo '   Checking for status code 406 and a rejection recommendation'
  process_folder "$folder" is_invalid_file
}

test_factur_x_canaries() {
  local warning_fixture='./test-data/valid-files/factur-x-1.07.2/3. EN16931/EN16931_Physiotherapeut/factur-x.xml'
  local basic_fixture='./test-data/valid-files/factur-x-1.07.2/2. BASIC/BASIC_Einfach/factur-x.xml'
  local invalid_fixture
  local original='<ram:DuePayableAmount>235.62</ram:DuePayableAmount>'
  local replacement='<ram:DuePayableAmount>235.63</ram:DuePayableAmount>'
  local failed=false

  echo '⏳ Testing Factur-X API and report-code canaries...'

  if ! is_valid_file "$warning_fixture"; then
    failed=true
  elif ! grep -Fq 'code="FX-SCH-A-000372"' <<< "$RESPONSE_BODY"; then
    echo '❌ FAILED: Factur-X warning did not retain code FX-SCH-A-000372' >&2
    failed=true
  else
    echo '✅ Warning-only EN16931 invoice returns HTTP 200 with FX-SCH-A-000372'
  fi

  if [[ $(grep -Foc "$original" "$basic_fixture") -ne 1 ]]; then
    echo '❌ FAILED: Factur-X BASIC mutation anchor changed' >&2
    failed=true
  else
    invalid_fixture=$(mktemp)
    sed "s#$original#$replacement#" "$basic_fixture" > "$invalid_fixture"
    if ! is_invalid_file "$invalid_fixture"; then
      failed=true
    elif ! grep -Fq 'code="FX-SCH-A-000122"' <<< "$RESPONSE_BODY"; then
      echo '❌ FAILED: Factur-X error did not retain code FX-SCH-A-000122' >&2
      failed=true
    else
      echo '✅ Invalid BASIC amount returns HTTP 406 with FX-SCH-A-000122'
    fi
    rm -f "$invalid_fixture"
  fi

  if [[ -n "$FACTUR_X_X20_CANARY" ]]; then
    if [[ ! -f "$FACTUR_X_X20_CANARY" ]]; then
      echo "❌ FAILED: FACTUR_X_X20_CANARY does not exist: $FACTUR_X_X20_CANARY" >&2
      failed=true
    elif ! is_valid_file "$FACTUR_X_X20_CANARY"; then
      failed=true
    elif grep -Eq 'code="FX-SCH-A-000(379|380|412)"' <<< "$RESPONSE_BODY"; then
      echo '❌ FAILED: X20 regression rule was reported' >&2
      failed=true
    else
      echo '✅ Optional X20 sub-invoice-line canary passed'
    fi
  else
    echo 'ℹ️  Optional X20 runtime canary skipped; set FACTUR_X_X20_CANARY to its local XML path.'
  fi

  echo ''
  ! $failed
}

wait_for_api || exit 1

if test_valid_files; then
  valid_result=0
else
  valid_result=1
fi

if test_invalid_files; then
  invalid_result=0
else
  invalid_result=1
fi

if test_factur_x_canaries; then
  canary_result=0
else
  canary_result=1
fi

echo '🔍 Test Summary:'
echo "   Valid files test: $([[ $valid_result -eq 0 ]] && echo '✅ PASSED' || echo '❌ FAILED')"
echo "   Invalid files test: $([[ $invalid_result -eq 0 ]] && echo '✅ PASSED' || echo '❌ FAILED')"
echo "   Factur-X canaries: $([[ $canary_result -eq 0 ]] && echo '✅ PASSED' || echo '❌ FAILED')"

if ((valid_result != 0 || invalid_result != 0 || canary_result != 0)); then
  exit 1
fi
