#!/bin/sh
# Gate: fail when any job in the batch manifest has status "failed".
# Fixed version. `read` splits the fields itself in every POSIX shell and
# in zsh, and a manifest with zero rows is reported as unknown, not clean.
# The field is named `state` because `status` is a read-only variable in
# zsh; the first draft of this fix died on it under zsh and passed under bash.
manifest=$1
failed=0
rows=0
# shellcheck disable=SC2034  # rest absorbs extra columns
while read -r job state rest; do
  [ -n "$job" ] || continue
  rows=$((rows + 1))
  if [ "$state" = "failed" ]; then
    echo "FAIL: job $job failed"
    failed=1
  fi
done < "$manifest"
if [ "$rows" -eq 0 ]; then
  echo "UNKNOWN: manifest has no rows"
  exit 2
fi
[ "$failed" -eq 0 ] && echo "OK: $rows jobs, none failed"
exit "$failed"
