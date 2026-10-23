#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
prefix=${1:?usage: test-luajit-health.sh INSTALLED_LUAJIT_PREFIX}
prefix=$(cd -- "$prefix" && pwd)
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
for test in luajit-health luajit-coalescing; do
  cc -Wall -Wextra -I "$prefix/include/luajit-2.1" -I "$root" "$root/tests/$test.c" \
    -L "$prefix/lib" -Wl,-rpath,"$prefix/lib" -lluajit-5.1 -ldl -o "$work/$test"
  "$work/$test" "$root/tests/luajit-coalescing.lua"
done
