# Building cimgui

`build_imgui.py` builds cimgui, Dear ImGui and the SDL2 and OpenGL3
backends, together with the C wrappers in `imgui_backends/`, into one
shared library, `cimgui_complete` (`.so`, `.dylib` or `.dll`).

```bash
git submodule update --init --recursive
python3 build_imgui.py <SDL2_PREFIX> <INSTALL_PREFIX>
```

CI and `build_local.sh` pass the platform prefix (for example
`prebuilt/linux/x86_64`) as both arguments, after SDL2 is installed
there. With no arguments the script uses its default paths and, outside
CI, runs a load test of the built library.

The script copies the wrapper files into the `cimgui/` submodule,
compiles everything as one unit and removes the copies afterwards, so
the submodule stays clean.

Prerequisites: a C++ compiler, SDL2 headers (from the prefix or the
system) and OpenGL headers. On Windows, CI uses MSVC.

To update Dear ImGui, move the `cimgui` submodule to a newer commit,
rebuild, then regenerate the Lua bindings with
`python3 build_imgui_bindings.py` (see `cimgui_love_generator/README.md`).
