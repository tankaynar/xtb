#!/usr/bin/env bash
# Checks a bundled xtb on its own: its version, a water single point, and the two geometries on
# which xtb 6.7.1's `--esp` aborts at random (IF5, XeF6), each run ten times as a single point
# and as Molion's optimisation. Any crash fails the check.
#
#     molion/check.sh <path to xtb/bin/xtb or xtb.exe>
set -euo pipefail

xtb="$1"
export XTBPATH="$(cd "$(dirname "$xtb")/../share/xtb" && pwd)"
export OMP_NUM_THREADS=2 OMP_MAX_ACTIVE_LEVELS=1 OPENBLAS_NUM_THREADS=1 OMP_STACKSIZE=1024M
work="$(mktemp -d)"
cd "$work"

"$xtb" --version | grep -i 'version'

printf '3\nwater\nO 0 0 0.1173\nH 0 0.7572 -0.4692\nH 0 -0.7572 -0.4692\n' > water.xyz
mkdir water && (cd water && "$xtb" ../water.xyz --gfn 2 > output.log)
energy=$(grep 'TOTAL ENERGY' water/output.log | awk '{print $4}')
echo "water: $energy Eh"
# GFN2-xTB's water near its minimum, as Molion's own test expects
awk -v energy="$energy" 'BEGIN { exit !((energy + 5.0702) ^ 2 < 4e-6) }' || { echo 'water energy is off'; exit 1; }

cat > if5.xyz <<'EOF'
6

F -0.7808 -0.4508 1.4255
I 0.1562 0.0902 -0.2851
F -0.1758 -1.7541 -1.0501
F 0.4881 1.9344 0.4799
F 1.9193 -0.5445 0.4799
F -1.607 0.7248 -1.0501
EOF
cat > xef6.xyz <<'EOF'
7

F -1.27683319964409 -0.04650270176534 -1.43446012291264
Xe 0.00182657309906 -0.00054129339953 -0.00156691771910
F 1.27202814082175 0.04425029023864 1.43909488951244
F 1.03079295303362 -1.37109749144346 -0.86919778963613
F -1.02434790462834 1.36687294538017 0.86934139991828
F 1.00229708896330 1.35036149985029 -0.93281443592556
F -1.00586365164531 -1.34344324886077 0.92950297676271
EOF

failed=0
for molecule in if5 xef6; do
  for flags in "--esp" "--opt --json --esp --molden --parallel 2"; do
    codes=""
    for run in $(seq 10); do
      rm -rf run && mkdir run && cp "$molecule.xyz" run/input.xyz
      code=0; (cd run && "$xtb" input.xyz $flags > output.log 2>&1) || code=$?
      codes="$codes $code"
      [ "$code" = 0 ] || failed=1
    done
    echo "$molecule $flags:$codes"
  done
done
exit $failed
