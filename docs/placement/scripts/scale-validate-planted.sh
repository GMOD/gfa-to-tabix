#!/usr/bin/env bash
# scale-validate.py on planted faults: a clean GFA must pass and each fault
# (a link no L line gives, an end that disagrees with the steps' bp, a
# repeated path and start, a name starting #) must fail.
#   bash scale-validate-planted.sh PYTHON_WITH_NUMPY
set -u
PY=${1:-python3}
V=$(dirname "$0")/scale-validate.py
D=$(mktemp -d)
head='H\tVN:Z:1.1\nS\t1\tACGT\nS\t2\tAC\nS\t3\t*\tLN:i:5\nL\t1\t+\t2\t+\t0M\nL\t2\t+\t3\t-\t0M\nW\tGRCh38\t0\tchr1\t0\t11\t>1>2<3\n'
expect() {
  printf "$head$3" | gzip > $D/$1.gfa.gz
  $PY $V $D/$1.gfa.gz > /dev/null 2>&1
  local got=$?
  echo "$1: exit $got, expected $2 $([ $got -eq $2 ] && echo ok || echo FAILED)"
}
expect clean 0 'W\tA\t1\tc\t0\t7\t>3<2\n'
expect missing-link 1 'W\tA\t1\tc\t0\t9\t>1>3\n'
expect wrong-end 1 'W\tA\t1\tc\t0\t8\t>3<2\n'
expect repeated-start 1 'W\tA\t1\tc\t0\t7\t>3<2\nW\tA\t1\tc\t0\t7\t>3<2\n'
expect hash-name 1 'W\t#B\t1\tc\t0\t7\t>3<2\n'
rm -r $D
