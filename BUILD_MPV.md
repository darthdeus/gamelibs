# Vendoring libmpv + FFmpeg into gamelibs

> Living plan. Describes **current state + what's next**, not history.
> Cite commits for past decisions. Update checkboxes in place.

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

## Phases

### Phase 1 — macOS arm64 build + local fix — IN PROGRESS

The dev machine and the machine that hit the bug. Verifiable here;
structurally fixes the incident.

- [x] `build_mpv.py` written; FFmpeg + libmpv **both compile clean**
      (`[258/258] Linking libmpv.2.dylib`). Shared-FFmpeg override
      works: `--enable-libavdevice` was invalid (aborted configure) →
      corrected to `--enable-avdevice`.
- [x] **Version consistency proven**: `libmpv.2.dylib` links
      `libavcodec.62.dylib current 62.32.100`, identical to the staged
      `libavcodec.62.32.100.dylib`. The skew bug is structurally gone.
- [x] `stage()` corrected: meson emits `libmpv.2.dylib` + a
      `libmpv.2.dylib.p/` *build dir* (old rglob copied the dir →
      `IsADirectoryError`). Now explicit paths + symlink-chain
      preservation + `mpv.pc` from `mpv/build/meson-private/`.
- [x] **Pin-stick gap FIXED.** Root: `./rebuild` runs `./update` which
      resets refs to master, undoing a post-update `git checkout`.
      Correct mechanism = mpv-build's `config/branch-<project>` files
      (`@<ref>`), honored by `./update` every run. `build_mpv.py` now
      writes them; pins recorded in **Core decision**. Reproducible.
- [x] Resolved pins recorded in **Core decision**.
- [ ] **(Superseded by Phase 2 — CI is the staging path now.)** Local
      `prebuilt/gamelibs-macos-arm64/` staging was only for the
      pre-CI bringup; per the "build in CI for all platforms, then
      `make download`" decision, the durable path is gamelibs CI →
      release → consumer download. No local-artifact wiring of
      `stone-video/build.rs`.
- [ ] `stone-video/build.rs`: resolve vendored prefix like
      `stone-rs/build.rs` (`prebuilt/gamelibs-<plat>/`); set
      `PKG_CONFIG_LIBDIR`/`PKG_CONFIG_PATH` to the vendored
      `lib/pkgconfig`; link `mpv` + `libavdevice` from there; add
      rpath. Keep system `pkg-config` as a fallback **only** when the
      vendored prefix is absent (CI runners without a gamelibs
      checkout) — log which path was taken, never silently.
- [ ] Rebuild `libstone_video`, rerun the fm audio probe
      (`/tmp/cprobe.lua` pattern): handle non-null, open ok, position
      advances, **no crash**, audio audible.
- [ ] `otool -L libstone_video.dylib` + `otool -L libmpv.2.dylib`:
      every libav\* current_version identical between the two.

### Phase 2 — macOS + Linux via CI — DONE (run 25934244764, 943ac59)

- [x] mpv cache+build steps wired into the `ubuntu` and `macos` jobs
      (mirrors SDL2 cache pattern; key = hash of `build_mpv.py`, which
      embeds the pins).
- [x] CI dep gap fixed (the "works on my machine" trap a dev box
      hides): libass needs **fribidi** (+fontconfig+harfbuzz) and
      **autotools** — added `libfribidi-dev`/`libfontconfig1-dev`/
      `libharfbuzz-dev` (ubuntu apt) and `autoconf automake libtool
      fribidi fontconfig harfbuzz` (macos brew).
- [x] **Pins validated in CI**: built FFmpeg 7.x (libavformat
      61.7.100, libavutil 59.39.100) + libmpv 2.5.0 (mpv 0.40.0) —
      proves `config/branch-*` pinning is honored and reproducible
      (the earlier unpinned local build was FFmpeg 8.x).
- [x] Both artifacts contain libmpv + libav*/libsw* with intact
      symlink chains, `@rpath`(macOS)/`$ORIGIN`(linux) staged into the
      existing `gamelibs-{linux-x86_64,macos-arm64}.zip`.

### libass dropped (decided 2026-05-16, all platforms)

mpv now builds `-Dlibass=disabled` and mpv-build's unconditional
libass step is patched out of its `build` script (`build_mpv.py`
`clone_mpv_build()`). libass = SSA/ASS subtitle rendering, used by
**no** consumer (fm audio preview, anvil video preview, recorder/
export via ffmpeg-the-third). It was also the single most fragile
link: its autotools/gettext `autoreconf` hit an MSYS2<->MINGW
path-mangling bug that consumed six Windows CI rounds — `aclocal:
.../progtest.m4 does not exist` while `ls` proved the file present,
because a mingw tool handed aclocal a Windows-rooted path that is not
a valid MSYS mount. Uniform on every platform: smaller libmpv, one
fewer dep, no behaviour change for our use cases. If subtitles are
ever needed, revisit with a non-autotools libass path.

### Phase 3 — Windows x86_64 — self-built via MSYS2 — DONE (run 25960133197)

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

### macOS cache-key bug (latent, pre-existing, repo-wide)

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

### Packaging bugs found at consumer install (v0.6.0) — Linux fixed v0.6.1, macOS pending v0.6.2

1. **No `.pc` files shipped.** FFmpeg installs pkgconfig under
   `build_libs/lib/pkgconfig/*.pc`, but `build_mpv.py stage()` only
   scanned `build_libs/lib/` for `*.pc` (wrong dir) — so the zip has
   zero `libav*.pc` / `mpv.pc`. Consequence: consumers can't point
   `PKG_CONFIG_PATH` at the vendored prefix. Fix `stage()` to copy
   `build_libs/lib/pkgconfig/*` and the meson `mpv.pc`.
2. **Symlinks dereferenced in the zip.** CI staging preserves the
   `libfoo.dylib -> .N -> .N.M.P` chain, but the workflow's
   `zip -r` (macOS/linux) follows symlinks → 3× full copies (~42MB
   zip, 3×12MB libavcodec). Add `-y` (zip store-symlinks) to the
   `Create release archive` steps in the ubuntu + macos jobs.

Both are gamelibs-side; functional (linking still resolves) but must
be fixed for a clean prefix + sane artifact size, then `make
release-minor` again (→ v0.6.1).

### Phase 4 — Release + consumer cutover

> **Three consumer-found bugs fixed in code (`build_mpv.py` +
> workflow); release pending.** See `CONSUMER_CUTOVER_FIXES.md`.

- [x] **Bug 1 — relocatable `.pc`.** `make_pc_relocatable()` rewrites
      every staged `.pc`'s `prefix`/`exec_prefix`/`libdir`/`includedir`
      to `${pcfiledir}`-relative (prefix = `${pcfiledir}/../..`). Called
      from both `stage()` and `stage_windows()`; `Requires`/`Libs`/
      `Cflags` left intact. Verified locally against ffmpeg-style
      (absolute) and meson-style (`/opt/homebrew`) `.pc`.
- [x] **Bug 2 — self-contained libmpv. Chose option (a): bundle.**
      `fix_macos_install_names()` now recursively vendors every
      `/opt/homebrew` + `/usr/local` dep into `<prefix>/lib` with
      `-id @rpath/<name>` and re-points all referrers (worklist walk:
      harfbuzz→graphite2/glib, fontconfig→expat/png/freetype, …), then
      asserts no external dep remains. Linux: `fix_linux_rpath()`
      vendors the libass font/codec stack via an **allowlist** of
      sonames (`_LINUX_VENDOR_STEMS`) — GPU/display libs
      (GL/X11/wayland/vulkan/drm) are deliberately left system.
      Windows: `bundle_windows_deps()` recursively copies the mingw
      font DLLs (libass is static-in-libmpv; its harfbuzz/fribidi/
      fontconfig/freetype/lcms2 are dynamic) into `bin/`, skipping the
      Windows system dir. Each platform has a post-bundle leak assert.
- [x] **Bug 3 — cache-hit completeness.** mpv cache `path:` on all
      three jobs broadened to libpostproc + `pkgconfig/{mpv,libav*,
      libsw*,libpostproc*,libplacebo,libass}.pc` + matching headers
      (targeted globs, not whole `bin/`/`pkgconfig/` — those are shared
      with SDL2/etc. in the same job). The recursively-vendored
      font/codec libs have arbitrary sonames and can't be globbed, so
      the cache step is also **skipped on tag builds**
      (`if: !startsWith(github.ref,'refs/tags/')`) → every release
      full-rebuilds into a complete, self-contained bundle. Dev/branch
      cache hits stay fast (bundled-dep gap is irrelevant: not shipped).
- [ ] **Release** — version decision pending (`.version`=0.6.2;
      `CONSUMER_CUTOVER_FIXES.md` rock-sfx parked note expects v0.6.3
      patch, this section originally said minor bump). Confirm with
      human, then `make release[-minor]`, push tag, CI publishes
      per-platform zips.
- [ ] rock-sfx: `make download` refresh; delete the
      `pkg_config`-fallback branch in `stone-video/build.rs` once all
      three platforms ship vendored (fallback existed only to bridge
      Phase 1→4).
- [ ] Drop the `// TODO: vendor libmpv` comment in
      `stone-video/build.rs`; update `gamelibs/CLAUDE.md` (planned →
      shipped) and `gamelibs/README.md` library list.
- [ ] Update `gamelibs/build_local.sh` + `library_info.txt` generation
      to include mpv/ffmpeg versions.

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
- Windows is the schedule risk; Phases 1–2 deliver the actual bug fix
  for dev + Linux CI, so don't block them on Phase 3.

## Status

CI green on all three platforms with real artifacts (run 25960133197).
Phases 1–3 done. **Phase 4: the three consumer-cutover bugs are fixed
in code** (relocatable `.pc`; recursive external-dep bundling on
mac/linux/windows — option (a); cache skipped on tag builds) — see the
Phase 4 checklist above. Not yet released: awaiting the version
decision, then a tag build publishes per-platform zips, then the
rock-sfx consumer cutover (`stone-video/build.rs` → vendored prefix,
delete the pkg-config fallback). Until that lands, the rock-sfx
interim remains `brew reinstall --build-from-source mpv` to realign
Homebrew mpv with current ffmpeg and unblock fm audio.
