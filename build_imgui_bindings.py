#!/usr/bin/env python3
"""
Generate Lua FFI bindings for cimgui.

Pairs with build_imgui.py: that script builds libcimgui_complete.{so,dylib,dll}
from the cimgui submodule. This script generates the Lua FFI bindings (cdef.lua,
wrap.lua, enums.lua, plus the static master.lua/init.lua) that match the dylib's
ABI exactly because both are derived from the same cimgui submodule SHA.

Pipeline:
  1. Verify cimgui submodule is initialized and generator output is present.
     (cimgui's own generator.sh produces cimgui/generator/output/definitions.lua
     etc.; the submodule ships these committed, so we don't re-run it here
     unless --regen-cimgui is passed.)
  2. Run cimgui_love_generator/generator.lua under LuaJIT. It reads
     cimgui/cimgui.h via vendored cparser, plus the generator output, and emits
     cdef.lua / wrap.lua / enums.lua to cimgui_love_generator/out/.
  3. Copy generated + static files into prebuilt/lua/cimgui/.

The cimgui-love generator was vendored in cimgui_love_generator/ (cimgui-love
1.92.0-1, https://codeberg.org/apicici/cimgui-love) with LÖVE-specific bits
neutered (texture_ref coercion removed, love module require dropped from
init.lua, shortcuts.lua dropped). See cimgui_love_generator/README.md.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GEN_DIR = ROOT / "cimgui_love_generator"
OUT_DIR = GEN_DIR / "out"
DEST_DIR = ROOT / "prebuilt" / "lua" / "cimgui"
CIMGUI_DIR = ROOT / "cimgui"
CIMGUI_GEN_OUTPUT = CIMGUI_DIR / "generator" / "output" / "definitions.lua"


def fail(msg: str) -> "None":
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def find_luajit() -> str:
    candidates = [
        ROOT / "luajit" / "src" / "luajit",
        Path("/opt/homebrew/bin/luajit"),
        Path("/usr/local/bin/luajit"),
        Path("/usr/bin/luajit"),
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    found = shutil.which("luajit")
    if found:
        return found
    fail(
        "luajit not found. cimgui-love's generator uses setfenv (Lua 5.1 / "
        "LuaJIT only) — install LuaJIT or build the bundled luajit submodule."
    )


def main() -> None:
    if not CIMGUI_DIR.exists():
        fail(
            f"{CIMGUI_DIR} missing. Run "
            "`git submodule update --init --recursive` first."
        )
    if not CIMGUI_GEN_OUTPUT.exists():
        fail(
            f"{CIMGUI_GEN_OUTPUT} not found. cimgui's own generator output "
            "is missing — run cimgui/generator/generator.sh inside the "
            "submodule first (requires lua + dear_bindings)."
        )

    luajit = find_luajit()
    print(f"[bindings] using luajit: {luajit}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # cimgui-love's generator.lua does require("cimgui.generator.output.X")
    # and require("cparser.cparser"). It assumes cwd == repo root with cimgui/
    # alongside and cparser/ on package.path. We run it from gamelibs root and
    # extend LUA_PATH to find the vendored cparser.
    lua_path_extra = f"{GEN_DIR}/?.lua;{GEN_DIR}/?/init.lua"
    env = os.environ.copy()
    existing = env.get("LUA_PATH", ";;")
    env["LUA_PATH"] = f"{lua_path_extra};{existing}"

    print("[bindings] running cimgui-love generator")
    res = subprocess.run(
        [luajit, str(GEN_DIR / "generator.lua")],
        cwd=str(ROOT),
        env=env,
    )
    if res.returncode != 0:
        fail(f"generator.lua exited with status {res.returncode}")

    expected = ["cdef.lua", "wrap.lua", "enums.lua"]
    for name in expected:
        if not (OUT_DIR / name).exists():
            fail(f"generator did not produce {OUT_DIR / name}")

    DEST_DIR.mkdir(parents=True, exist_ok=True)

    # Generated files
    for name in expected:
        shutil.copy2(OUT_DIR / name, DEST_DIR / name)
        print(f"[bindings] generated -> prebuilt/lua/cimgui/{name}")

    # Static files (vendored, ship as-is)
    for name in ["master.lua", "init.lua"]:
        shutil.copy2(GEN_DIR / name, DEST_DIR / name)
        print(f"[bindings] static    -> prebuilt/lua/cimgui/{name}")

    # Informational dumps (not loaded at runtime, useful for diffs)
    for name in ["ignored_defaults.txt", "ignored_out_arg.txt", "overloads.txt"]:
        if (OUT_DIR / name).exists():
            shutil.copy2(OUT_DIR / name, DEST_DIR / name)

    print(f"[bindings] done -> {DEST_DIR}")


if __name__ == "__main__":
    main()
