# gamelibs

Prebuilt native libraries for games, built from pinned sources by GitHub
Actions and published as release zips. Rock's
engine links them, but nothing here is Rock-specific: each zip is an
ordinary install prefix with `include/`, `lib/` (`bin/` on Windows),
`pkg-config` files and upstream notices under `licenses/`.

## Libraries

| Library | Version | Licence | Notes |
|---|---|---|---|
| SDL2 | 2.32.4 (in tree) | Zlib | |
| FreeType | 2.14.1 (in tree) | FTL (or GPL-2.0-or-later) | |
| LuaJIT | submodule `luajit` | MIT | |
| cimgui + Dear ImGui | submodule `cimgui` | MIT | one `cimgui_complete` library with the SDL2 and OpenGL3 backends |
| Lua bindings for cimgui | generated (`cimgui_love_generator`) | MIT | `gamelibs-lua-bindings.zip` |

## Platforms

| Zip | Target |
|---|---|
| `gamelibs-linux-x86_64.zip` | Linux x86_64 (glibc) |
| `gamelibs-macos-arm64.zip` | macOS arm64 (deployment target 15.0) |
| `gamelibs-windows-x86_64.zip` | Windows x86_64 |
| `gamelibs-ios-arm64.zip`, `gamelibs-ios-arm64-sim.zip` | iOS: LuaJIT only |

## Using a release

Download the zip for your platform from the
[releases page](https://github.com/darthdeus/gamelibs/releases) and
extract it into a prefix, or run `make download`, which extracts the
latest release into `prebuilt/<platform>/<arch>/`. Shared libraries use
relative install names (`@rpath` on macOS, `$ORIGIN` on Linux) and the
`.pc` files are relocatable, so the prefix can live anywhere.

## Building

`make build` builds SDL2, FreeType, cimgui and LuaJIT locally on Linux
(`build_local.sh`). The workflow builds desktop and iOS libraries and Lua
bindings on every push and pull request.
Pushing a `v*` tag builds and publishes a release; `make release` bumps the
version and tags it.

Clone with submodules: `git clone --recursive`.

## Licence

The build scripts, CI configuration, wrappers and documentation in this
repository are licensed under either of [MIT](LICENSE-MIT) or
[Apache-2.0](LICENSE-APACHE), at your option. Vendored and built
third-party libraries keep their own licences, listed above; each
in-tree copy carries its upstream licence files.
