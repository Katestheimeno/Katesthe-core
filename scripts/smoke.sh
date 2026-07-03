#!/usr/bin/env bash
set -euo pipefail
BASE_URL="${BASE_URL:-http://localhost:8000}"

fail=0
probe() {
  local name="$1" url="$2" expect="$3" ; shift 3
  local code
  code="$(curl -sS -m 10 -o /dev/null -w "%{http_code}" "$@" "$url" || echo "000")"
  if [ "$code" = "$expect" ]; then
    printf "PASS  %-24s %s (%s)\n" "$name" "$url" "$code"
  else
    printf "FAIL  %-24s %s (got %s, want %s)\n" "$name" "$url" "$code" "$expect"
    fail=1
  fi
}

probe "health"  "$BASE_URL/health/" 200
probe "ready"   "$BASE_URL/ready/"  200
if [ -n "${SMOKE_JWT:-}" ]; then
  probe "auth-me" "$BASE_URL/api/v1/auth/users/me/" 200 -H "Authorization: Bearer ${SMOKE_JWT}"
fi

if [ "$fail" -eq 0 ]; then echo "SMOKE OK"; exit 0; else echo "SMOKE FAILED"; exit 1; fi
