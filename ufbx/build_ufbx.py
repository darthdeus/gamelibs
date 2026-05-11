#!/usr/bin/env python3
"""Build ufbx as a shared library for the current platform.

ufbx is a single-file C library. Compile the .c, drop the .dylib/.so/.dll
into prebuilt/<os>/<arch>/lib/ and copy the header to prebuilt/.../include/.

Usage:
    ./build_ufbx.py                              # default ../prebuilt
    ./build_ufbx.py <INSTALL_PREFIX>             # explicit prefix
"""

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Default install layout follows the rest of gamelibs/.
if len(sys.argv) == 2:
    INSTALL_PREFIX = Path(sys.argv[1]).resolve()
else:
    repo_root = HERE.parent
    sysname = platform.system().lower()
    if sysname == "darwin":
        sysname = "macos"
    arch = platform.machine().lower()
    if arch == "x86_64":
        arch = "x64"
    INSTALL_PREFIX = repo_root / "prebuilt" / sysname / arch

print(f"[ufbx] building -> {INSTALL_PREFIX}")

LIB_DIR = INSTALL_PREFIX / "lib"
INC_DIR = INSTALL_PREFIX / "include"
LIB_DIR.mkdir(parents=True, exist_ok=True)
INC_DIR.mkdir(parents=True, exist_ok=True)

src = HERE / "ufbx.c"
hdr = HERE / "ufbx.h"
if not src.exists() or not hdr.exists():
    sys.exit("ufbx.c / ufbx.h missing in this directory — fetch them from https://github.com/ufbx/ufbx")

obj = HERE / "build" / "ufbx.o"
obj.parent.mkdir(exist_ok=True)

cc = os.environ.get("CC", "cc")
cflags = ["-O2", "-fPIC", "-Wall", "-std=c11"]
# ufbx prefers either single- or double-precision; default builds fine.

# Platform-specific output filename + link flags
sysname = platform.system()
if sysname == "Darwin":
    out = LIB_DIR / "libufbx.dylib"
    link_extra = ["-dynamiclib", f"-install_name", f"@rpath/{out.name}"]
elif sysname == "Linux":
    out = LIB_DIR / "libufbx.so"
    link_extra = ["-shared", f"-Wl,-soname,{out.name}"]
elif sysname == "Windows":
    out = LIB_DIR / "ufbx.dll"
    link_extra = ["-shared"]
else:
    sys.exit(f"unsupported platform: {sysname}")

# Single-step compile + link
cmd = [cc, *cflags, *link_extra, "-o", str(out), str(src), "-lm"]
print("[ufbx]", " ".join(cmd))
subprocess.run(cmd, check=True)

shutil.copy2(hdr, INC_DIR / "ufbx.h")
print(f"[ufbx] {out}  ({out.stat().st_size // 1024} KiB)")
print(f"[ufbx] {INC_DIR / 'ufbx.h'}")
