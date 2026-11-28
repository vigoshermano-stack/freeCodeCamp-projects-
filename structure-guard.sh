#!/bin/sh
# src/ ships, tests/ proves it.
#
# Called by both CI providers (`sh scripts/structure-guard.sh`) so the rule lives
# in one place instead of drifting between two YAML files. Run it from anywhere;
# it walks up to the repo root itself.
#
# Under GitHub Flow this is the gate that keeps a branch cheap to review: the
# structural mistakes it catches (a test in src/, a committed token) would
# otherwise be found by a human an hour later.

set -u

root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root" || exit 1

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "structure-guard: not a git repository - run this from a clone" >&2
  exit 1
fi

fail=0

if [ ! -f requirements.txt ]; then
  echo "requirements.txt is missing - CI cannot reproduce a build" >&2
  fail=1
fi

if [ ! -d tests ] || [ -z "$(ls -A tests 2>/dev/null)" ]; then
  echo "tests/ is missing or empty" >&2
  fail=1
fi

tests_in_src=$(find src -type f \( -name 'test_*.py' -o -name '*_test.py' \) 2>/dev/null)
if [ -n "$tests_in_src" ]; then
  echo "Unit tests found under src/ - they belong in tests/:" >&2
  echo "$tests_in_src" >&2
  fail=1
fi

tracked_junk=$(git ls-files | grep -E '(^|/)\.env$|(^|/)__pycache__/|\.pyc$|(^|/)\.venv/|(^|/)reports/|(^|/)\.pytest_cache/')
if [ -n "$tracked_junk" ]; then
  echo "A secret or generated file is tracked in git:" >&2
  echo "$tracked_junk" >&2
  fail=1
fi

if [ ! -f .github/PULL_REQUEST_TEMPLATE.md ]; then
  echo ".github/PULL_REQUEST_TEMPLATE.md is missing - every PR needs the same questions" >&2
  fail=1
fi

if [ "$fail" -ne 0 ]; then
  echo "structure-guard: failed" >&2
  exit 1
fi

echo "structure-guard: passed"
