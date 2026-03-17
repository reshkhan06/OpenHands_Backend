#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
ENDPOINT="${ENDPOINT:-/ngo/register}"

PY="${PYTHON:-python}"

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 2
  }
}

need_cmd curl
need_cmd "$PY"

ts="$(date +%s)"
email_ok="ngo_${ts}@example.com"

payload_ok="$(
  "$PY" - <<PY
import json
print(json.dumps({
  "ngo_name": "Helping Hands Foundation",
  "registration_number": "REG-12345/2026",
  "ngo_type": "trust",
  "email": "${email_ok}",
  "address": "12 MG Road, Near Park",
  "city": "Bengaluru",
  "state": "Karnataka",
  "pincode": "560001",
  "mission_statement": "We help communities with food and education.",
  "bank_name": "State Bank of India",
  "account_number": "12345678901",
  "ifsc_code": "SBIN0001234",
  "password": "StrongPass1",
}))
PY
)"

request() {
  local payload="$1"
  local out_file="$2"
  local code
  code="$(curl -sS -o "$out_file" -w "%{http_code}" \
    --connect-timeout 3 \
    --max-time 10 \
    -H "Content-Type: application/json" \
    -X POST "${BASE_URL}${ENDPOINT}" \
    --data "$payload")"
  echo "$code"
}

assert_status() {
  local got="$1"
  local want="$2"
  local label="$3"
  if [[ "$got" != "$want" ]]; then
    echo "FAIL: $label (status $got, expected $want)" >&2
    return 1
  fi
}

assert_field_error() {
  local body_file="$1"
  local field="$2"
  local contains_msg="$3"

  "$PY" - "$body_file" "$field" "$contains_msg" <<'PY'
import json, sys
body_path = sys.argv[1]
field = sys.argv[2]
needle = sys.argv[3] if len(sys.argv) > 3 else ""
with open(body_path, "r", encoding="utf-8") as f:
    data = json.load(f)
detail = data.get("detail")
if not isinstance(detail, list):
    print(f"Expected 'detail' list in error body, got: {type(detail).__name__}", file=sys.stderr)
    sys.exit(1)
msgs = []
for e in detail:
    loc = e.get("loc") if isinstance(e, dict) else None
    msg = e.get("msg") if isinstance(e, dict) else None
    if isinstance(loc, list) and len(loc) >= 2 and loc[0] == "body" and loc[1] == field:
        if isinstance(msg, str):
            msgs.append(msg)
if not msgs:
    print(f"Expected validation error for field '{field}', none found.", file=sys.stderr)
    sys.exit(1)
if needle and not any(needle.lower() in m.lower() for m in msgs):
    print(f"Expected field '{field}' message to include '{needle}'. Got: {msgs}", file=sys.stderr)
    sys.exit(1)
PY
}

echo "Testing NGO register validations against ${BASE_URL}${ENDPOINT}"

tmp_dir="$("$PY" - <<'PY'
import tempfile
print(tempfile.mkdtemp(prefix="ngo_reg_val_"))
PY
)"
trap 'rm -rf "$tmp_dir"' EXIT

pass_count=0
run_case() {
  local label="$1"
  local payload="$2"
  local want_status="$3"
  local body="$tmp_dir/${label// /_}.json"

  local got
  got="$(request "$payload" "$body")"
  assert_status "$got" "$want_status" "$label"
  pass_count=$((pass_count+1))
  echo "OK: $label"
  echo "$body"
}

# --- invalid cases (expect 422) ---

payload_bad_ngo_name="$("$PY" - <<PY
import json
d=json.loads('''$payload_ok''')
d["ngo_name"]="  "
print(json.dumps(d))
PY
)"
run_case "ngo_name_empty" "$payload_bad_ngo_name" "422"
assert_field_error "$tmp_dir/ngo_name_empty.json" "ngo_name" "cannot be empty"

payload_bad_regchars="$("$PY" - <<PY
import json
d=json.loads('''$payload_ok''')
d["registration_number"]="REG@@@"
print(json.dumps(d))
PY
)"
run_case "registration_number_invalid_chars" "$payload_bad_regchars" "422"
assert_field_error "$tmp_dir/registration_number_invalid_chars.json" "registration_number" "invalid"

payload_bad_email="$("$PY" - <<PY
import json
d=json.loads('''$payload_ok''')
d["email"]="not-an-email"
print(json.dumps(d))
PY
)"
run_case "email_invalid" "$payload_bad_email" "422"
assert_field_error "$tmp_dir/email_invalid.json" "email" "valid"

payload_bad_address="$("$PY" - <<PY
import json
d=json.loads('''$payload_ok''')
d["address"]="12345"
print(json.dumps(d))
PY
)"
run_case "address_no_letter" "$payload_bad_address" "422"
assert_field_error "$tmp_dir/address_no_letter.json" "address" "letter"

payload_bad_city="$("$PY" - <<PY
import json
d=json.loads('''$payload_ok''')
d["city"]="@@@"
print(json.dumps(d))
PY
)"
run_case "city_invalid" "$payload_bad_city" "422"
assert_field_error "$tmp_dir/city_invalid.json" "city" "invalid"

payload_bad_state="$("$PY" - <<PY
import json
d=json.loads('''$payload_ok''')
d["state"]=""
print(json.dumps(d))
PY
)"
run_case "state_empty" "$payload_bad_state" "422"
assert_field_error "$tmp_dir/state_empty.json" "state" "empty"

payload_bad_pincode="$("$PY" - <<PY
import json
d=json.loads('''$payload_ok''')
d["pincode"]="123"
print(json.dumps(d))
PY
)"
run_case "pincode_short" "$payload_bad_pincode" "422"
assert_field_error "$tmp_dir/pincode_short.json" "pincode" "6"

payload_bad_mission="$("$PY" - <<PY
import json
d=json.loads('''$payload_ok''')
d["mission_statement"]="short"
print(json.dumps(d))
PY
)"
run_case "mission_too_short" "$payload_bad_mission" "422"
assert_field_error "$tmp_dir/mission_too_short.json" "mission_statement" "least"

payload_bad_bank="$("$PY" - <<PY
import json
d=json.loads('''$payload_ok''')
d["bank_name"]="ab"
print(json.dumps(d))
PY
)"
run_case "bank_name_too_short" "$payload_bad_bank" "422"
assert_field_error "$tmp_dir/bank_name_too_short.json" "bank_name" "between"

payload_bad_acct="$("$PY" - <<PY
import json
d=json.loads('''$payload_ok''')
d["account_number"]="12AB"
print(json.dumps(d))
PY
)"
run_case "account_number_non_digits" "$payload_bad_acct" "422"
assert_field_error "$tmp_dir/account_number_non_digits.json" "account_number" "digits"

payload_bad_ifsc="$("$PY" - <<PY
import json
d=json.loads('''$payload_ok''')
d["ifsc_code"]="SBI00001234"
print(json.dumps(d))
PY
)"
run_case "ifsc_invalid" "$payload_bad_ifsc" "422"
assert_field_error "$tmp_dir/ifsc_invalid.json" "ifsc_code" "format"

payload_bad_password="$("$PY" - <<PY
import json
d=json.loads('''$payload_ok''')
d["password"]="password1"
print(json.dumps(d))
PY
)"
run_case "password_missing_upper" "$payload_bad_password" "422"
assert_field_error "$tmp_dir/password_missing_upper.json" "password" "uppercase"

# --- valid case (expect 200) ---
body_ok="$tmp_dir/ok.json"
code_ok="$(request "$payload_ok" "$body_ok")"
assert_status "$code_ok" "200" "valid_payload"
echo "OK: valid_payload"
pass_count=$((pass_count+1))

# --- duplicate email case (expect 400) ---
body_dup="$tmp_dir/duplicate_email.json"
code_dup="$(request "$payload_ok" "$body_dup")"
assert_status "$code_dup" "400" "duplicate_email"
"$PY" - "$body_dup" <<'PY'
import json, sys
path = sys.argv[1]
with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)
detail = data.get("detail")
if not (isinstance(detail, str) and "already" in detail.lower()):
    print(f"Expected duplicate-email message in detail, got: {detail!r}", file=sys.stderr)
    sys.exit(1)
PY
echo "OK: duplicate_email"
pass_count=$((pass_count+1))

echo "All checks passed ($pass_count)."
