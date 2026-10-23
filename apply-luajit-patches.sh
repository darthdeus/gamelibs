#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
LUAJIT_DIR="$ROOT_DIR/luajit"
PATCH_FILE="$ROOT_DIR/patches/luajit-health.patch"
HEADER_FILE="$ROOT_DIR/luajit-health.h"
HEADER_DEST="$LUAJIT_DIR/src/luajit-health.h"
EXPECTED_COMMIT=a4c064539ea931274d407e1249b4bb575424a0f4

die() {
  printf 'apply-luajit-patches: %s\n' "$1" >&2
  exit 1
}

[[ -d "$LUAJIT_DIR/.git" || -f "$LUAJIT_DIR/.git" ]] || die "LuaJIT submodule is missing; run git submodule update --init luajit"
[[ -f "$PATCH_FILE" ]] || die "required patch is missing: $PATCH_FILE"
[[ -f "$HEADER_FILE" ]] || die "required public header is missing: $HEADER_FILE"

actual_commit=$(git -C "$LUAJIT_DIR" rev-parse --verify HEAD 2>/dev/null) || die "cannot read LuaJIT submodule HEAD"
[[ "$actual_commit" == "$EXPECTED_COMMIT" ]] || die "expected LuaJIT $EXPECTED_COMMIT, found $actual_commit"

if git -C "$LUAJIT_DIR" apply --reverse --check "$PATCH_FILE" >/dev/null 2>&1; then
  printf 'LuaJIT health patch already applied.\n'
elif git -C "$LUAJIT_DIR" apply --check "$PATCH_FILE" >/dev/null 2>&1; then
  git -C "$LUAJIT_DIR" apply "$PATCH_FILE"
  printf 'Applied LuaJIT health patch.\n'
else
  die "patch is neither cleanly applicable nor already applied; inspect the LuaJIT worktree"
fi

if [[ -e "$HEADER_DEST" ]]; then
  cmp -s "$HEADER_FILE" "$HEADER_DEST" || die "existing LuaJIT header differs from $HEADER_FILE: $HEADER_DEST"
else
  cp "$HEADER_FILE" "$HEADER_DEST"
  printf 'Installed LuaJIT health header.\n'
fi
