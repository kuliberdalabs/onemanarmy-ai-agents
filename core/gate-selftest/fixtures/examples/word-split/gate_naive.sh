#!/bin/sh
# Gate: fail when any job in the batch manifest has status "failed".
# Naive version. `set -- $row` relies on word splitting, which bash and dash
# do and zsh does not. Under zsh $1 holds the whole row, $2 is empty, and
# no job ever counts as failed.
manifest=$1
failed=0
while IFS= read -r row; do
  # shellcheck disable=SC2086  # the unquoted split is the incident under test
  set -- $row
  if [ "$2" = "failed" ]; then
    echo "FAIL: job $1 failed"
    failed=1
  fi
done < "$manifest"
[ "$failed" -eq 0 ] && echo "OK: no failed jobs"
exit "$failed"
