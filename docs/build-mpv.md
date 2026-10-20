# Vendoring libmpv + FFmpeg into gamelibs


## Why

`stone-video` (playback) and the Anvil recorder (screen capture via
libavdevice) were the last consumers still binding FFmpeg/libmpv via
system `pkg-config`. Every other game lib (SDL2, LuaJIT, freetype,
cimgui, soloud) is pinned in `prebuilt/<platform>/<arch>/`. libmpv was
the hold-out — and it broke exactly the way pinning prevents:

**Root incident (rock-sfx `sfx` branch, 2026-05-15):** fm audio preview
crashed `EXC_BAD_ACCESS` PC=0 in libmpv's decoder thread. Cause: Homebrew
`mpv 0.40.0_4` was built against `ffmpeg 8.0` (libavcodec **62.11.100**)
but the `opt/ffmpeg` symlink had moved to `ffmpeg 8.1.1` (libavcodec
**62.28.101**). Same install-name path → dyld loaded the newer libav\*
into a libmpv built for the older ABI → indirect call through a moved
function table → null jump on any audio decode.

Vendoring libmpv **and** its FFmpeg together, built as one unit, makes
this class of skew structurally impossible: the ABI both sides see is
the one we shipped.

## Core decision

Use **`mpv-build`** (upstream meta-build:
`https://github.com/mpv-player/mpv-build`). It clones pinned FFmpeg +
mpv (+ libass, libplacebo) and builds them against each other in one
pass — so libmpv and libav\* are version-consistent **by construction**.
That is the entire point; do not build mpv against a system/Homebrew
FFmpeg.

**Pinned versions** (the contract — bump deliberately, never float).
Pinned via mpv-build's own `config/branch-<project>` mechanism (the
`@<ref>` form = `git checkout <ref>`, honored by `./update` every run
incl. through `./rebuild`). Set in `build_mpv.py`:

- FFmpeg: `@n7.1.1` — the ABI-critical pin (this pair's skew caused the
  fm crash).
- mpv: `@v0.40.0` — supports FFmpeg >= 6.1, so n7.1.1 is in range.
- mpv-build: `9443097290e82008f26f1597590926c63e7ae053`.
- libass / libplacebo: `release` (latest upstream release tag). They
  static-link INTO libmpv so no cross-process ABI skew is possible;
  `release` is reproducible enough and dodges pinning a libplacebo too
  old for mpv 0.40.

> CI is the validator for this combo (the "diagnose in CI" step). If
> n7.1.1 ↔ v0.40.0 fails to build, adjust here and re-push.

## Critical constraint: ONE FFmpeg in the process

`stone-video` also links the Rust crate `ffmpeg-the-third` (async export
+ recorder). It resolves FFmpeg via `pkg-config` too. If it binds a
*different* FFmpeg than libmpv, we recreate the exact skew bug at the
Rust boundary instead of the Homebrew one.

**Requirement:** `ffmpeg-the-third` must build against the **vendored**
FFmpeg. Mechanism: `stone-video/build.rs` prepends the gamelibs
prebuilt `lib/pkgconfig` to `PKG_CONFIG_PATH` (and sets
`PKG_CONFIG_LIBDIR` to fully isolate from Homebrew) before
`ffmpeg-the-third`'s build script runs, and links libmpv from the same
prefix. libmpv + libav\* + ffmpeg-the-third then all reference one set
of dylibs with one install_name root.

## Output layout (matches existing libs)

```
prebuilt/<platform>/<arch>/
  lib/   libmpv.2.dylib            (+ .so.2 / mpv-2.dll)
         libavcodec.<v>.dylib  libavformat  libavutil
         libavdevice  libavfilter  libswscale  libswresample
         pkgconfig/{mpv,libav*,libsw*}.pc
  include/ mpv/  libavcodec/ ... (FFmpeg dev headers)
```

macOS: rewrite install names to `@rpath/<name>` and inter-lib refs via
`install_name_tool`, so consumers' existing
`-rpath,@loader_path/../prebuilt/gamelibs-macos-arm64/lib` (see
`stone-rs/build.rs:39`) resolves them with zero new wiring. Linux:
`-Wl,-rpath,$ORIGIN`. Windows: DLLs are co-located, no rpath concept.

## Platform notes

### libass is static inside libmpv

mpv 0.40 has a hard `dependency('libass')` and no meson option to drop
it, so libass is built static and linked into libmpv, like libplacebo.
macOS and Linux use mpv-build's autotools step; Windows builds it with
Meson (`build_libass_meson`) because autoreconf breaks under MSYS2.

### Windows x86_64: self-built via MSYS2

All three platforms green with real artifacts (Windows: `libmpv-2.dll`
+ `av*/sw*/postproc` DLLs, FFmpeg n7.1.1 ABI — `avcodec-61` etc. —
consistent with mac/linux). `build_mpv.py` `stage_windows()` (DLLs→bin,
import libs+pkgconfig→lib) + `build-windows` job (`msys2/setup-msys2`
MINGW64, `shell: msys2 {0}`, `git hash-object` cache key).

Windows-specific divergence from the unix `./rebuild` path (all in
`build_mpv.py` `main()`, gated `if plat == "windows"`):

- **libass via Meson, not autotools.** mpv-build's autotools libass
  (`autogen.sh`→`autoreconf`→`aclocal`) is unfixable under MSYS2: the
  runtime drive-strips aclocal's canonicalized acdir so
  `/usr/share/aclocal` is searched at a bogus drive-rooted path and
  `progtest.m4` "does not exist" though present. Six shim rounds
  (`ACLOCAL_PATH`, `--system-acdir`, automake 1.16, `/etc/fstab`,
  install relocation + symlink) each hit a different facet — abandoned.
  `main()` splits `./rebuild` into `./update` →
  `patch_out_mpv_build_libass` (comment mpv-build's two libass
  invocation lines) → `build_libass_meson` (static, into `build_libs`)
  → `./build`. Meson never invokes aclocal. mac/linux keep autotools
  libass (proven green) — unchanged.
- **`unset PKG_CONFIG_PATH`** in the build step. `actions/setup-python`
  exports a `C:\…\lib/pkgconfig` Windows path; mpv-build's `*-config`
  scripts append `build_libs/lib/pkgconfig` with a POSIX `:` sep, and
  the inherited `C:` drive-colon makes the list unparseable to pkgconf
  → mpv couldn't see ffmpeg's `libav*.pc`. Empty → clean msys path;
  mingw deps resolve via pkgconf's built-in `/mingw64` dir.

Also fixed this round (were breaking *all* platforms / masking macOS):
newline-joined `ffmpeg_options` (mpv-build splits `IFS=<newline>`;
single-line collapsed to one argv → `eval: __disable_static`);
`write_lf()` for all generated files (mingw-python CRLF left `\r` on
every option → meson "Option libmpv value true"); libass kept (mpv
0.40 hard-requires it, no `-Dlibass` option); macOS `mpv-hash` added
to its cache-keys step (was empty → constant key → macOS shipped a
stale pre-regression libmpv and reported false green).

Original design notes (still the rationale):

Still deferred in *sequence* (mac+linux cut over first) but **not
architecturally special**. Earlier notes proposed repackaging
shinchiro/BtbN prebuilts; that is rejected. It contradicts the entire
point of gamelibs — own the build, no reliance on third parties to
manage versioning. (The "vanilla mpv-build has no mingw path"
conclusion was a shallow grep, not real investigation: mpv-build
builds shared libmpv+FFmpeg under MSYS2 mingw; that is how upstream
mpv itself produces Windows libmpv.)

**Windows is the same shape as mac/linux:** we build FFmpeg *shared* +
libmpv against it, dynamically linked, from our pinned sources. The
skew bug cannot recur on any platform for one uniform reason — *we*
build libmpv against the FFmpeg *we* ship. No static-isolation
cleverness needed; that was only attractive while reaching for a
third-party prebuilt.

`ffmpeg-the-third = "5.0"` is unconditional and `record.rs` has a
`#[cfg(target_os="windows")]` gdigrab path, so Windows needs the same
shared FFmpeg for the recorder too — which the self-built shared
FFmpeg provides, exactly as on mac/linux.

Plan when resumed:

- [ ] `build_mpv.py` Windows branch: run mpv-build under an MSYS2
      `MINGW64` shell on the existing `build-windows` runner. Deps via
      `pacman`: `mingw-w64-x86_64-{gcc,meson,ninja,nasm,pkgconf,
      libass,fribidi,...}`. Same `ffmpeg_options`
      (`--enable-shared --disable-static --enable-avdevice`) + mpv
      `default_library=shared`.
- [ ] Stage `mpv-2.dll` + `av*.dll`/`sw*.dll` + import libs
      (`.dll.a` / `.lib`) + headers + `.pc` into
      `prebuilt/windows/x86_64/{bin,lib,include}` (Windows DLLs go in
      `bin/`, import libs in `lib/` — match the other gamelibs win
      layout). No rpath on Windows; co-located DLLs resolve.
- [ ] `build-windows` job: add `msys2/setup-msys2` action, the
      `pacman` deps, cached mpv build step (same `git hash-object`
      key). The other libs on this runner stay CMake/MSVC as-is — only
      the mpv step uses the MSYS2 shell.
- [ ] `stone-video/build.rs` Windows arm: link `mpv`/`avdevice` from
      the vendored prefix; `FFMPEG_DIR` → vendored prefix for
      ffmpeg-the-third (same mechanism as mac/linux).

Risk is real (MSYS2 toolchain wiring in CI is fiddlier than apt/brew)
but it is the *correct* risk — owned, reproducible, uniform. Not
blocking the mac/linux cutover.

### macOS cache key

The `Generate cache keys` step uses `sha256sum`, which **does not exist
on macOS runners** — every `*-macos-*` cache key degrades to the
constant `<lib>-macos-v1-` (empty hash). Effect: macOS lib caches never
invalidate on source change; v0.6.1's `.pc`/symlink fixes built on
Linux but macOS `Build libmpv+FFmpeg` was `skipped` (stale v0.6.0
restored). Fixed for the mpv key only by switching to `git hash-object`
(portable, deterministic). Additionally, the mpv cache step is now
skipped entirely on tag builds (Bug 3 fix) so a release can never ship
a partial cache-restored bundle. The other libs (SDL2/freetype/…) still
have the constant-key bug — out of scope here, but they silently never
rebuild on macOS until someone bumps `CACHE_VERSION`. Worth a separate
gamelibs cleanup.

### Windows vcruntime140

Found while verifying the v0.6.3 Windows bundle. The 6 **MSVC**-built
DLLs (`SDL2_image`, `SDL2_mixer`, `cimgui_complete`, `freetype`,
`lua51`, `soloud`) were `/MD` (dynamic CRT) and imported
`vcruntime140.dll` (+ `vcruntime140_1.dll` for cimgui) — the VC++
2015–2022 redistributable runtime, **not guaranteed on a clean Windows
10/11 box** (UCRT *is* an OS component; `vcruntime140` is not;
`msvcp140` was not imported — C++ stdlib was already static). Not
introduced by the mpv work and **not in the libmpv/FFmpeg chain**
(that stack is MinGW → `msvcrt.dll`, an OS component — fully
self-contained).

Resolved by **static-linking the VC++ CRT (`/MT`)** rather than
shipping the redist DLLs — zero MS-runtime redistribution surface (no
VS license clause, nothing for the consumer or Steam Common
Redistributables to install). CMake libs:
`-DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreaded` +
`-DCMAKE_POLICY_DEFAULT_CMP0091=NEW` at **every** cmake site (incl.
statically-linked zlib/libpng/ogg/vorbis/… — else CRT mixing within a
DLL); cimgui `cl /MD→/MT`; LuaJIT submodule `msvcbuild.bat` patched at
build time. `CACHE_VERSION` v1→v2 (all jobs) forces the clean rebuild.
Assumes Windows 10+ (UCRT as OS component); pre-Win10 consumers would
also need the UCRT redist — acceptable floor for a modern game-lib repo.

## Gotchas / risks

- **avdevice must be enabled** in the FFmpeg configure or the Anvil
  recorder loses screen capture (avfoundation/x11grab/gdigrab). It is
  not on by default in minimal FFmpeg configs.
- **macOS SDL2 dedup note** (`stone-video/build.rs:19-27`): do NOT link
  SDL2 here; mpv's GL path resolves `SDL_GL_GetProcAddress` via dlsym
  at runtime. Vendoring mpv doesn't change this — keep the no-SDL2 rule.
- **install_name rewriting** is the fiddly macOS step: libmpv references
  libav\* by absolute build path by default; must `install_name_tool
  -change` each to `@rpath/...` and set libmpv's own id. Mirror whatever
  `build_sdl_image.py`/`build_soloud.py` already do for their deps.
- **Binary size**: full FFmpeg is large. Acceptable (matches the
  "precompiled, vendored" repo purpose) but consider
  `--disable-doc --disable-programs --disable-debug` and dropping
  encoders we never use *only if* size is a problem — keep decoders +
  avdevice broad; correctness over bytes.
- **ffmpeg-the-third version match**: the crate must support the pinned
  FFmpeg major. Check the crate's supported range when picking the
  FFmpeg tag; if `ffmpeg-the-third = "5.0"` caps below the chosen
  FFmpeg, bump the crate in the same change.

## Status

Shipped since v0.6.3 on Linux x86_64, macOS arm64 and Windows x86_64.
Staged `.pc` files are rewritten to be relocatable, external runtime
dependencies are bundled per platform, and tag builds skip the cache.
`stone-video` links the vendored prefix only.

Next: publish the media stack as a separate download from the core
libraries, since this FFmpeg build is GPL (`--enable-gpl`, libx264), and
ship licence notices for every bundled library.
