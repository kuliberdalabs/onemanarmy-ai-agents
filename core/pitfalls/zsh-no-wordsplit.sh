#!/usr/bin/env bash
# Pitfall: zsh does not word-split an unquoted parameter expansion.
# `row="id title status"; set -- $row` gives three arguments in bash and sh,
# and ONE argument in zsh. A loop `for v in $IDS` runs once over the whole
# string. Code that parses rows this way silently reads the wrong fields when
# the same snippet runs under zsh (the default login shell on macOS).
#
# Needs: zsh and bash.
# Fix: in zsh split explicitly (${=row} or an array); for portable snippets
# run them under bash with an array: arr=($row); set -- "${arr[@]}"
# Prints REPRODUCED and exits 0 when the pitfall shows; exits 1 otherwise.

if ! command -v zsh >/dev/null 2>&1; then
  echo "NOT REPRODUCED: zsh not installed"; exit 1
fi

snippet='row="42 invoice-reminder done"; set -- $row; echo "$#"'

in_bash=$(bash -c "$snippet")
in_zsh=$(zsh -f -c "$snippet")

if [ "$in_bash" = "3" ] && [ "$in_zsh" = "1" ]; then
  echo "REPRODUCED: 'set -- \$row' gave $in_bash args in bash and $in_zsh in zsh"
  exit 0
fi
echo "NOT REPRODUCED: bash=$in_bash zsh=$in_zsh"
exit 1
