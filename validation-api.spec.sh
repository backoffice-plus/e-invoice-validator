#!/bin/bash

API_URL="http://localhost:8080"  # Updated endpoint
VERBOSE=false

# Accepted file report needs to contain one of the following recommendation texts
ACCEPTED_RECOMMENDATIONS=(
  "Bewertung: Es wird empfohlen das Dokument anzunehmen und weiter zu verarbeiten."
  "Bewertung: Es wird empfohlen das Dokument anzunehmen und zu verarbeiten, da die vorhandenen Fehler derzeit toleriert werden."
)

REJECTED_RECOMMENDATIONS=(
  "Bewertung: Es wird empfohlen das Dokument nicht anzunehmen."
)

# Parse command line arguments
while getopts "v" opt; do
  case $opt in
    v)
      VERBOSE=true
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      exit 1
      ;;
  esac
done

# Function to get API response for a file
get_response() {
  local file=$1
  
  # Store both response body and status code
  response_body=$(curl -s \
    -X POST \
    -H "Content-Type: application/xml" \
    --data-binary @"$file" \
    -w "\n%{http_code}" \
    "$API_URL")
  
  # Extract status code from last line of response
  status_code=$(echo "$response_body" | tail -n1)
  # Get actual response body without the status code
  body=$(echo "$response_body" | sed '$d')
  
  # Return both status code and body
  echo -e "${status_code}\n${body}"
}

# Function to test if a file is valid
is_valid_file() {
  local file=$1
  
  # Get response (status code and body)
  response=$(get_response "$file")
  status_code=$(echo "$response" | head -n1)
  body=$(echo "$response" | tail -n +2)
  
  # Valid file criteria: status 200 and contains recommendation text
  valid=true
  error_messages=()
  
  # Check status code
  if [ "$status_code" -ne 200 ]; then
    valid=false
    error_messages+=("Status code: Expected 200, got $status_code")
  fi
  
  # Check recommendation text using the global array
  recommendation_found=false
  for recommendation in "${ACCEPTED_RECOMMENDATIONS[@]}"; do
    if echo "$body" | grep -q "$recommendation"; then
      recommendation_found=true
      break
    fi
  done
  
  if ! $recommendation_found; then
    valid=false
    error_messages+=("Expected recommendation text not found")
  fi
  
  # Result handling
  if $valid; then
    if $VERBOSE; then
      echo "✅ PASSED: $file"
    fi
    return 0
  else
    echo "❌ FAILED: $file"
    for message in "${error_messages[@]}"; do
      echo "   - $message"
    done
    return 1
  fi
}

# Function to test if a file is invalid
is_invalid_file() {
  local file=$1
  
  # Get response (status code and body)
  response=$(get_response "$file")
  status_code=$(echo "$response" | head -n1)
  body=$(echo "$response" | tail -n +2)
  
  # Invalid file criteria: status 406
  valid=true
  error_messages=()
  
  # Check status code
  if [ "$status_code" -ne 406 ]; then
    valid=false
    error_messages+=("Status code: Expected 406, got $status_code")
  fi
  
  # Result handling
  if $valid; then
    if $VERBOSE; then
      echo "✅ PASSED: $file"
    fi
    return 0
  else
    echo "❌ FAILED: $file"
    for message in "${error_messages[@]}"; do
      echo "   - $message"
    done
    return 1
  fi
}

# Process all files in a folder with the appropriate test function
process_folder() {
  local folder=$1
  local test_function=$2
  local success_count=0
  local fail_count=0
  
  while read -r file; do
    if $VERBOSE; then
      echo "Testing: $file"
    fi
    
    if $test_function "$file"; then
      ((success_count++))
    else
      ((fail_count++))
    fi
  done < <(find "$folder" -type f -name "*.xml")
  
  echo "✅ Passed: $success_count"
  echo "❌ Failed: $fail_count"
  echo ""
  
  return $fail_count
}

# Test valid files folder
test_valid_files() {
  local folder=${1:-"./test-data/valid-files"}
  
  echo "⏳ Testing files expected to be valid..."
  echo "   Checking for status code 200 and recommendation text"
  process_folder "$folder" is_valid_file
  return $?
}

# Test invalid files folder
test_invalid_files() {
  local folder=${1:-"./test-data/invalid-files"}
  
  echo "⏳ Testing files expected to be invalid..."
  echo "   Checking for status code 406"
  process_folder "$folder" is_invalid_file
  return $?
}

# Run tests
test_valid_files
valid_result=$?

test_invalid_files
invalid_result=$?

# Final summary and exit status
echo "🔍 Test Summary:"
echo "   Valid files test: $([ $valid_result -eq 0 ] && echo "✅ PASSED" || echo "❌ FAILED")"
echo "   Invalid files test: $([ $invalid_result -eq 0 ] && echo "✅ PASSED" || echo "❌ FAILED")"

# Exit with failure if any test failed
[ $valid_result -eq 0 ] && [ $invalid_result -eq 0 ] || exit 1
