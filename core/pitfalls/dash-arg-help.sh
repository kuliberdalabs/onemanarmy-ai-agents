#!/usr/bin/env bash
# Pitfall: a positional argument that starts with a dash is read as an option.
# Python's argparse takes "-hVtq..." (a real-looking video id, a base64 or
# hash fragment) as -h, prints the help text and exits 0. A loop that counts
# exit 0 as success counts an item that was never processed. Measured once:
# a batch reported 8 items added; the target held 7.
#
# Needs: bash and python3 3.11 or newer (stdlib argparse). Up to 3.10,
# argparse rejects "-hVtq..." with "ignored explicit argument" and exit 2, so
# the item fails loudly there and this pitfall does not show.
# Fix: put `--` before positional arguments, and after any API operation count
# the objects by reading them back instead of trusting exit codes.
# Prints REPRODUCED and exits 0 when the pitfall shows; exits 1 otherwise.

if ! command -v python3 >/dev/null 2>&1; then
  echo "NOT REPRODUCED: python3 not installed"; exit 1
fi
if ! python3 -I -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
  found=$(python3 -I -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null)
  echo "NOT REPRODUCED: needs python3 >= 3.11 (found ${found:-unknown})"; exit 1
fi

cli='
import argparse
p = argparse.ArgumentParser(prog="add-item")
p.add_argument("item_id")
print("ADDED", p.parse_args().item_id)
'
id="-hVtqK8Aq0E"

naive_out=$(python3 -I -c "$cli" "$id" 2>&1); naive_rc=$?
safe_out=$(python3 -I -c "$cli" -- "$id" 2>&1); safe_rc=$?

case "$naive_out" in *ADDED*) naive_added=yes ;; *) naive_added=no ;; esac

if [ "$naive_rc" -eq 0 ] && [ "$naive_added" = no ] && [ "$safe_rc" -eq 0 ] \
   && [ "$safe_out" = "ADDED $id" ]; then
  echo "REPRODUCED: '$id' printed help and exited 0 without adding anything; with '--' it printed '$safe_out'"
  exit 0
fi
echo "NOT REPRODUCED: naive_rc=$naive_rc naive_added=$naive_added safe_rc=$safe_rc safe_out=$safe_out"
exit 1
