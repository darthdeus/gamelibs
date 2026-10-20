# gamelibs

Prebuilt native game libraries (SDL2, FreeType, LuaJIT, cimgui, libmpv +
FFmpeg) for Linux x86_64, macOS arm64 and Windows x86_64, built by
`.github/workflows/build-libraries.yml` and published as release zips.
Rock's engine (`stone-rs`, `stone-video`) consumes them from
`prebuilt/<platform>/<arch>/`. See README.md.

- `build_local.sh`: local Linux build of the core libraries.
- `build_imgui.py`: cimgui plus backends; `docs/build-imgui.md`.
- `build_mpv.py`: libmpv + FFmpeg; `docs/build-mpv.md`.
- `build_imgui_bindings.py` + `cimgui_love_generator/`: Lua bindings.
- `build_ios.sh`: LuaJIT for iOS.

This repository is public. Run `git config core.hooksPath .githooks`
once per clone: the hooks refuse developer paths, private keys and the
names in `~/.config/rock-lang/denylist`. Keep docs current-state; do not
add handoff or investigation notes to the tree.
