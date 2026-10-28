#!/usr/bin/env bash
# Copies the licence files of xtb and of every subproject linked into it (meson's wraps, which
# the build fetched into subprojects/) to <dir>/<project>/.
#
#     molion/licences.sh <dir>
set -euo pipefail

out="$1"
mkdir -p "$out/xtb"
cp COPYING COPYING.LESSER "$out/xtb/"
for project in subprojects/*/; do
  name=$(basename "$project")
  files=$(find "$project" -maxdepth 1 -type f \( -iname 'COPYING*' -o -iname 'LICENSE*' -o -iname 'LICENCE*' \))
  if [ -z "$files" ]; then
    echo "warning: no licence files found for $name"
    continue
  fi
  mkdir -p "$out/$name"
  cp $files "$out/$name/"
done
ls "$out"
