#!/bin/bash
# iOS gamelibs: LuaJIT only.
#
# SDL2 is NOT built here. rock's stone-rs builds it from source for iOS via
# the sdl2-sys `bundled` feature (cmake handles the iOS cross fine), so the
# only thing iOS needs from gamelibs is a LuaJIT that mlua can link against
# -- luajit-src cannot cross-compile to iOS (it builds the host-side minilua
# and buildvm with the target flags, and macOS then kills the iOS binary).
#
# Builds both the device and simulator slices; both go through the same
# LuaJIT cross recipe, differing only in SDK and -target triple.
#
# JIT is compiled OUT on both slices. iOS forbids the W^X mapping the JIT
# needs, so a device build could never use it; the simulator *could*, but a
# simulator that JITs while the device interprets makes the simulator
# useless for judging performance.
set -euo pipefail

cd "$(dirname "$0")"
ROOT="$PWD"

if [ "$(uname -s)" != "Darwin" ]; then
  echo "build_ios.sh: iOS builds require macOS + Xcode" >&2
  exit 1
fi

git submodule update --init luajit

MIN_VERSION=14.0

build_slice() {
  local name="$1" sdk="$2" triple="$3"
  local sdk_path toolchain_bin prefix
  sdk_path="$(xcrun --sdk "$sdk" --show-sdk-path)"
  toolchain_bin="$(dirname "$(xcrun --sdk "$sdk" --find clang)")"
  prefix="$ROOT/prebuilt/ios/$name"

  echo "==> LuaJIT for $name ($sdk, $triple)"
  rm -rf "$prefix"
  mkdir -p "$prefix/lib" "$prefix/include/luajit-2.1"

  # amalg: single-TU build, noticeably smaller than the default.
  # HOST_CC stays bare `clang` -- minilua and buildvm run on the *build*
  # machine. CROSS is what redirects the target compiler at the iOS
  # toolchain; CC=clang because LuaJIT's Makefile defaults it to gcc.
  # `make clean` leaves enough behind that a second slice reuses the first
  # slice's objects and silently produces a duplicate of it. Nuke everything
  # untracked instead -- luajit is a pinned submodule, so this is safe.
  git -C luajit clean -xfdq
  make -C luajit -j"$(sysctl -n hw.ncpu)" amalg \
    CC=clang \
    HOST_CC=clang \
    CROSS="$toolchain_bin/" \
    TARGET_SYS=iOS \
    TARGET_FLAGS="-isysroot $sdk_path -target $triple" \
    XCFLAGS="-DLUAJIT_DISABLE_JIT"

  cp luajit/src/libluajit.a "$prefix/lib/"
  cp luajit/src/lua.h luajit/src/lauxlib.h luajit/src/lualib.h \
     luajit/src/luaconf.h luajit/src/luajit.h luajit/src/lua.hpp \
     "$prefix/include/luajit-2.1/"

  # A slice must be the platform it claims: a stale-object reuse silently
  # ships the previous slice's binary under the new name.
  local got
  got=$(otool -l "$prefix/lib/libluajit.a" | awk '/LC_BUILD_VERSION/{f=1} f&&/platform/{print $2; exit}')
  if [ "$got" != "$4" ]; then
    echo "build_ios.sh: $name built for platform $got, expected $4" >&2
    exit 1
  fi
  echo "    -> $prefix/lib/libluajit.a (platform $got)"
}

# Trailing arg is the Mach-O platform each slice must report: 2 = iOS,
# 7 = iOS Simulator.
build_slice arm64     iphoneos        "arm64-apple-ios${MIN_VERSION}"           2
build_slice arm64-sim iphonesimulator "arm64-apple-ios${MIN_VERSION}-simulator" 7

echo
echo "iOS gamelibs built:"
find prebuilt/ios -name 'libluajit.a' -exec ls -la {} \;
