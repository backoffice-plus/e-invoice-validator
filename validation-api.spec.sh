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
  elif ! grep -Fq 'code="PEPPOL-EN16931-R008"' <<< "$RESPONSE_BODY"; then
    echo '❌ FAILED: Factur-X warning did not retain code PEPPOL-EN16931-R008' >&2
    failed=true
  else
    echo '✅ Warning-only EN16931 invoice returns HTTP 200 with PEPPOL-EN16931-R008'
  fi

  if [[ $(grep -Foc "$original" "$basic_fixture") -ne 1 ]]; then
    echo '❌ FAILED: Factur-X BASIC mutation anchor changed' >&2
    failed=true
  else
    invalid_fixture=$(mktemp)
    sed "s#$original#$replacement#" "$basic_fixture" > "$invalid_fixture"
    if ! is_invalid_file "$invalid_fixture"; then
      failed=true
    elif ! grep -Fq 'code="BR-CO-16"' <<< "$RESPONSE_BODY"; then
      echo '❌ FAILED: Factur-X error did not retain code BR-CO-16' >&2
      failed=true
    else
      echo '✅ Invalid BASIC amount returns HTTP 406 with BR-CO-16'
    fi
    rm -f "$invalid_fixture"
  fi

  if [[ -n "$FACTUR_X_X20_CANARY" ]]; then
    if [[ ! -f "$FACTUR_X_X20_CANARY" ]]; then
      echo "❌ FAILED: FACTUR_X_X20_CANARY does not exist: $FACTUR_X_X20_CANARY" >&2
      failed=true
    elif ! is_valid_file "$FACTUR_X_X20_CANARY"; then
      failed=true
    elif grep -Eq 'code="BR-FXEXT-S-08(ini|rev|b)"' <<< "$RESPONSE_BODY"; then
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

test_en16931_canaries() {
  local fixture_dir
  local cii_fixture='./test-data/invalid-files/factur-x-1.07.2/5. XRECHNUNG/XRECHNUNG_Einfach/xrechnung.xml'
  local failed=false
  local check
  local fixture
  local rule
  fixture_dir=$(mktemp -d) || return 1

  echo '⏳ Testing updated EN16931 rules for generic UBL and XRechnung CII...'
  if ! python3 - "$fixture_dir" <<'PY'
import copy
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ns = {
    'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
    'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
    'ram': 'urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100',
}
source = Path('test-data/valid-files/xrechnung-3.0.2/standard/01.01a-INVOICE_ubl.xml')
target = Path(sys.argv[1])
root = ET.parse(source).getroot()
root.find('cbc:CustomizationID', ns).text = 'urn:cen.eu:en16931:2017'
ET.ElementTree(root).write(target / 'generic.xml', encoding='utf-8', xml_declaration=True)

invalid_vat = copy.deepcopy(root)
vat = invalid_vat.find('cac:AccountingSupplierParty/cac:Party/cac:PartyTaxScheme/cbc:CompanyID', ns)
vat.text = 'A'
ET.ElementTree(invalid_vat).write(target / 'vat-prefix.xml', encoding='utf-8', xml_declaration=True)

duplicate_legal_entity = copy.deepcopy(root)
supplier = duplicate_legal_entity.find('cac:AccountingSupplierParty/cac:Party', ns)
legal_entity = supplier.find('cac:PartyLegalEntity', ns)
supplier.insert(list(supplier).index(legal_entity) + 1, ET.Element(legal_entity.tag))
ET.ElementTree(duplicate_legal_entity).write(target / 'legal-entity.xml', encoding='utf-8', xml_declaration=True)

credit_note = copy.deepcopy(root)
credit_note.tag = '{urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2}CreditNote'
renamed_tags = {
    f'{{{ns["cac"]}}}InvoiceLine': f'{{{ns["cac"]}}}CreditNoteLine',
    f'{{{ns["cbc"]}}}InvoicedQuantity': f'{{{ns["cbc"]}}}CreditedQuantity',
    f'{{{ns["cbc"]}}}InvoiceTypeCode': f'{{{ns["cbc"]}}}CreditNoteTypeCode',
}
for element in credit_note.iter():
    element.tag = renamed_tags.get(element.tag, element.tag)
credit_note.find('cbc:CreditNoteTypeCode', ns).text = '381'
ET.ElementTree(credit_note).write(target / 'credit-note.xml', encoding='utf-8', xml_declaration=True)

for base, name, prefix in ((root, 'greek-el-invoice', 'EL'),
                           (credit_note, 'greek-el-credit-note', 'EL'),
                           (root, 'greek-gr-invoice', 'GR')):
    greek = copy.deepcopy(base)
    seller = greek.find('cac:AccountingSupplierParty/cac:Party', ns)
    seller.find('cac:PartyTaxScheme/cbc:CompanyID', ns).text = prefix + '123456789'
    seller.find('cac:PostalAddress/cac:Country/cbc:IdentificationCode', ns).text = 'GR'
    ET.ElementTree(greek).write(target / (name + '.xml'), encoding='utf-8', xml_declaration=True)

cii_source = Path('test-data/invalid-files/factur-x-1.07.2/5. XRECHNUNG/XRECHNUNG_Einfach/xrechnung.xml')
cii_root = ET.parse(cii_source).getroot()
contact = cii_root.find('.//ram:SellerTradeParty/ram:DefinedTradeContact', ns)
contact.remove(contact.find('ram:DepartmentName', ns))
ET.ElementTree(cii_root).write(target / 'cii-contact.xml', encoding='utf-8', xml_declaration=True)
PY
  then
    rm -f "$fixture_dir/"*.xml
    rmdir "$fixture_dir"
    return 1
  fi

  if ! is_valid_file "$fixture_dir/generic.xml"; then
    failed=true
  else
    echo '✅ Generic UBL invoice is accepted'
  fi

  if ! is_valid_file "$fixture_dir/credit-note.xml"; then
    failed=true
  else
    echo '✅ Generic UBL credit note is accepted'
  fi

  for fixture in greek-el-invoice greek-el-credit-note greek-gr-invoice; do
    if ! is_valid_file "$fixture_dir/$fixture.xml"; then
      failed=true
    elif grep -Fq 'code="BR-CO-09"' <<< "$RESPONSE_BODY"; then
      echo "❌ FAILED: Allowed Greek VAT prefix reported BR-CO-09 in $fixture" >&2
      failed=true
    else
      echo "✅ Allowed Greek VAT prefix is accepted in $fixture"
    fi
  done

  for check in 'vat-prefix.xml|BR-CO-09' 'legal-entity.xml|UBL-SR-57'; do
    IFS='|' read -r fixture rule <<< "$check"
    if ! is_invalid_file "$fixture_dir/$fixture"; then
      failed=true
    elif ! grep -Fq "code=\"$rule\"" <<< "$RESPONSE_BODY"; then
      echo "❌ FAILED: Expected EN16931 rule $rule was not reported" >&2
      failed=true
    else
      echo "✅ Generic UBL regression is rejected with $rule"
    fi
  done

  if ! is_invalid_file "$cii_fixture"; then
    failed=true
  elif ! grep -Fq 'code="CII-SR-465"' <<< "$RESPONSE_BODY"; then
    echo '❌ FAILED: Duplicate XRechnung seller contact did not report CII-SR-465' >&2
    failed=true
  else
    echo '✅ Duplicate XRechnung seller contact is rejected with CII-SR-465'
  fi

  if ! is_valid_file "$fixture_dir/cii-contact.xml"; then
    failed=true
  else
    echo '✅ XRechnung seller contact is accepted after removing the duplicate field'
  fi

  rm -f "$fixture_dir/"*.xml
  rmdir "$fixture_dir"
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

if test_en16931_canaries; then
  en16931_result=0
else
  en16931_result=1
fi

if python3 ./scripts/test-upstream-api.py --api-url "$API_URL"; then
  upstream_result=0
else
  upstream_result=1
fi

echo '🔍 Test Summary:'
echo "   Valid files test: $([[ $valid_result -eq 0 ]] && echo '✅ PASSED' || echo '❌ FAILED')"
echo "   Invalid files test: $([[ $invalid_result -eq 0 ]] && echo '✅ PASSED' || echo '❌ FAILED')"
echo "   Factur-X canaries: $([[ $canary_result -eq 0 ]] && echo '✅ PASSED' || echo '❌ FAILED')"
echo "   EN16931 canaries: $([[ $en16931_result -eq 0 ]] && echo '✅ PASSED' || echo '❌ FAILED')"
echo "   Upstream API corpus: $([[ $upstream_result -eq 0 ]] && echo '✅ PASSED' || echo '❌ FAILED')"

if ((valid_result != 0 || invalid_result != 0 || canary_result != 0 || en16931_result != 0 || upstream_result != 0)); then
  exit 1
fi
