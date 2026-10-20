# gamelibs

Prebuilt native libraries for games, built from pinned sources by GitHub
Actions and published as release zips. Rock's
engine links them, but nothing here is Rock-specific: each zip is an
ordinary install prefix with `include/`, `lib/` (`bin/` on Windows) and
`pkg-config` files.

## Libraries

| Library | Version | Licence | Notes |
|---|---|---|---|
| SDL2 | 2.32.4 (in tree) | Zlib | |
| FreeType | 2.14.1 (in tree) | FTL (or GPL-2.0-or-later) | |
| LuaJIT | submodule `luajit` | MIT | |
| cimgui + Dear ImGui | submodule `cimgui` | MIT | one `cimgui_complete` library with the SDL2 and OpenGL3 backends |
| Lua bindings for cimgui | generated (`cimgui_love_generator`) | MIT | `gamelibs-lua-bindings.zip` |
| libmpv + FFmpeg | mpv v0.40.0, FFmpeg n7.1.1 | **GPL-2.0-or-later** as built | FFmpeg is configured with `--enable-gpl` and libx264; see [docs/build-mpv.md](docs/build-mpv.md) |

The libmpv and FFmpeg build also bundles its runtime dependencies (for
example fontconfig, HarfBuzz, FriBidi, GnuTLS, GMP and Nettle on some
platforms), each under its own licence. Today the media stack ships in
the same zip as the core libraries; it is being moved to a separate
download so the core zip contains only permissively licensed code.

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
(`build_local.sh`). The full matrix, including libmpv and FFmpeg
(`build_mpv.py`), runs in `.github/workflows/build-libraries.yml` on
every push and pull request. Pushing a `v*` tag builds and publishes a
release; `make release` bumps the version and tags it.

Clone with submodules: `git clone --recursive`.

## Licence

The build scripts, CI configuration, wrappers and documentation in this
repository are licensed under either of [MIT](LICENSE-MIT) or
[Apache-2.0](LICENSE-APACHE), at your option. Vendored and built
third-party libraries keep their own licences, listed above; each
in-tree copy carries its upstream licence files.
