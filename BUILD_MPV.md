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

### Phase 3 — Windows x86_64 — DEFERRED (decided 2026-05-15)

Decision: **macOS + Linux ship via CI first; Windows is a separate
follow-up.** mpv-build's native Windows path (MSYS2/mingw) is the
documented risk and slow to debug over the CI loop — it must not block
the two working platforms. The Windows gamelibs zip keeps its current
no-mpv state until this is picked up.

When resumed, the leading option is **repackage shinchiro/mpv-winbuild**
pinned libmpv+FFmpeg DLLs (battle-tested, low CI churn) rather than
running mpv-build under MSYS2. `stone-video` Windows link still needs
`libavdevice` → gdigrab. Not started.

### Phase 4 — Release + consumer cutover

- [ ] `make release-minor` (new lib = minor bump), push tag, CI
      publishes per-platform zips.
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

Phase 1 in progress. Nothing shipped yet. rock-sfx interim: until
Phase 1's build.rs lands, `brew reinstall --build-from-source mpv`
realigns Homebrew mpv with current ffmpeg and unblocks fm audio.
