# cimgui_love_generator

Vendored generator for cimgui Lua FFI bindings. Produces `cdef.lua`,
`wrap.lua`, `enums.lua` matching the dylib that `build_imgui.py` builds
from the `cimgui/` submodule.

## Why this exists

Without lockstep generation, the Lua FFI bindings drift from the dylib's
ABI as cimgui evolves: overloaded ImGui functions get type-suffixed names
(`igIsMouseDown_Nil`/`_ID`, `ImVec2_Float`, etc.) introduced in the
underlying dear_bindings tooling, and bindings produced against an older
cimgui rev silently fail to call newer overloads. By regenerating the
bindings from the same cimgui submodule SHA the dylib is built from, drift
is impossible.

## Source

Vendored from [cimgui-love](https://codeberg.org/apicici/cimgui-love)
1.92.0-1 (commit `3b8a61d9b5`, 2025-07-12). LÖVE-specific bits removed:

- `templates.texture_ref` neutered in `generator.lua` — non-LÖVE callers
  pass real `ImTextureRef` values (e.g. via `ImTextureRef_TextureID`).
- `love` env entry removed from `base.lua`.
- `love.lua` not vendored. `shortcuts.lua` not vendored (LÖVE-only,
  deprecated upstream since ImGui 1.90.7).
- `init.lua` rewritten to load the dylib by platform-specific filename
  (no LÖVE `package.cpath` magic).

## How to regenerate

```bash
git submodule update --init --recursive   # ensure cimgui/ is present
python3 build_imgui_bindings.py           # writes prebuilt/lua/cimgui/
```

The script:
1. Verifies `cimgui/generator/output/definitions.lua` exists (committed
   in the cimgui submodule itself; rerun `cimgui/generator/generator.sh`
   only if bumping cimgui to a rev that hasn't pre-generated it).
2. Runs `generator.lua` under LuaJIT, reading `cimgui/cimgui.h` via the
   vendored `cparser/` and the cimgui generator's Lua output.
3. Copies generated + static files to `prebuilt/lua/cimgui/`.

LuaJIT is required (the generator uses `setfenv`, Lua 5.1 / LuaJIT only).

## When bumping cimgui

The generator output is robust: cdef + wrap + enums regenerate cleanly
against whatever cimgui rev is checked out. After bumping:

1. Rebuild the dylib (`build_imgui.py`).
2. Regenerate bindings (`build_imgui_bindings.py`).
3. Commit both in the same change so consumers get them paired.

## Files

- `generator.lua`, `base.lua` — modified copies of cimgui-love sources.
- `cparser/` — verbatim copy of cimgui-love's vendored cparser.
- `master.lua` — verbatim copy (no changes needed).
- `init.lua` — rewritten for non-LÖVE dylib loading.
- `out/` — scratch directory for generator output (gitignored).
- `LICENSE.cimgui-love` — upstream MIT license.
