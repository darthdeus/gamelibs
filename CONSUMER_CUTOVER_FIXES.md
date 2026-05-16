# gamelibs consumer-cutover fixes (libmpv/FFmpeg vendoring)

> Handoff for a parallel session. Context: BUILD_MPV.md (Phases 1-3
> done, CI green all platforms run 25960133197). These three bugs were
> found while wiring the **rock-sfx** consumer against the macOS
> bundle. Each breaks `make download` for *every* consumer, not just
> rock-sfx. Fix all three, then a clean release unblocks the consumer
> cutover (rock-sfx side is being done in parallel and currently works
> only via local workarounds for #1).

All three are in `build_mpv.py` `stage()` / `stage_windows()` /
`fix_macos_install_names()` and/or the cache step in
`.github/workflows/build-libraries.yml`. mac/linux/windows unix vs
meson-libass split is already in place; do not regress it.

---

## Bug 1 — shipped `.pc` files are not relocatable (ALL platforms)

**Symptom / evidence (macOS bundle from run 25959761350):**

- `lib/pkgconfig/mpv.pc` ships `prefix=/opt/homebrew` with
  `libdir=${prefix}/lib` -> a consumer pointing `PKG_CONFIG_PATH` at
  the vendored prefix links **Homebrew's** libmpv, recreating the
  exact ABI-skew crash this vendoring exists to prevent.
- `lib/pkgconfig/libav*.pc` / `libplacebo.pc` / `libass.pc` ship
  `prefix=/Users/runner/work/gamelibs/gamelibs/build/mpv/mpv-build/build_libs`
  and **absolute** `libdir=/Users/runner/.../lib` (NOT
  `${prefix}`-relative), so they resolve to nonexistent CI paths on
  any consumer machine.

**Root cause:** `stage()` copies `.pc` verbatim. ffmpeg's `.pc` bake
absolute `prefix`/`libdir`/`includedir`; meson's `mpv.pc` bakes the
build-host brew prefix.

**Fix (in `build_mpv.py` `stage()` / `stage_windows()`):** after
copying each `.pc` into `<prefix>/lib/pkgconfig`, rewrite it to be
relocatable:

- `prefix=${pcfiledir}/../..`   (pcfiledir = `<prefix>/lib/pkgconfig`)
- `libdir=${prefix}/lib`
- `includedir=${prefix}/include`
- leave `Requires`/`Libs`/`Cflags` intact.

`${pcfiledir}` is pkg-config/pkgconf builtin and makes the prefix
self-locating with zero consumer env. Apply to **every** staged `.pc`
(mpv, libav*, libsw*, libpostproc, libplacebo, libass). Verify the
`Libs:`/`Cflags:` still use `${libdir}`/`${includedir}` (ffmpeg's do).

**Acceptance:** in a clean dir,
`PKG_CONFIG_PATH=<extracted>/lib/pkgconfig pkg-config --libs --cflags mpv libavdevice libavcodec`
prints paths under `<extracted>`, never `/opt/homebrew` or
`/Users/runner`. (On a non-mac host the system-dep `-I` for
fontconfig/etc. may be absent; that's fine — only the mpv/libav*
prefix must be local.)

---

## Bug 2 — macOS libmpv hard-links Homebrew dylibs (not self-contained)

**Symptom / evidence:** `otool -L lib/libmpv.2.dylib` on the macOS
bundle lists, by absolute install name:

```
/opt/homebrew/opt/fontconfig/lib/libfontconfig.1.dylib
/opt/homebrew/opt/harfbuzz/lib/libharfbuzz.0.dylib
/opt/homebrew/opt/fribidi/lib/libfribidi.0.dylib
/opt/homebrew/opt/little-cms2/lib/liblcms2.2.dylib
/opt/homebrew/opt/jpeg-turbo/lib/libjpeg.8.dylib
```

The libav*/libmpv inter-refs are correctly `@rpath` (the ABI-skew fix
holds), but a machine without these Homebrew kegs cannot load libmpv.
Defeats "vendored / hermetic."

**Root cause:** `fix_macos_install_names()` only rewrites refs whose
basename is in the staged set; it does not vendor libmpv's external
brew deps. The build links them because the macOS job `brew install`s
fontconfig/harfbuzz/fribidi (libass deps) and mpv-build links them
dynamically.

**Fix options (pick one, document choice in BUILD_MPV.md):**

- **(a) Bundle them.** In `fix_macos_install_names()`: for each
  `/opt/homebrew/...` (or `/usr/local/...`) dep of every staged dylib,
  `cp` the real dylib into `<prefix>/lib`, `install_name_tool -id
  @rpath/<name>` it, and `-change` the ref in the dependents. Recurse
  one level (those deps have their own deps: glib, pcre2, graphite2,
  png, freetype...). Mirror whatever `build_sdl_image.py` /
  `build_soloud.py` already do for their deps — reuse that helper if
  present. Watch the transitive set (harfbuzz->graphite2/glib;
  fontconfig->expat/png/freetype).
- **(b) Static-link the font stack into libmpv** by building
  fribidi/harfbuzz/fontconfig static in the mpv-build step (heavier;
  (a) is closer to how the other gamelibs deps are handled).

Linux: check `ldd lib/libmpv.so` for the analogous apt absolute deps;
`fix_linux_rpath` only sets `$ORIGIN`. Apply the same bundling if
non-system (libfontconfig/harfbuzz/fribidi/lcms2/jpeg) deps leak.
Windows: `stage_windows()` already copies `ff_bin/*.dll`; verify the
libass/font DLLs (libass, fribidi-0, harfbuzz, fontconfig, freetype,
lcms2, jpeg) land in `bin/` too — meson libass + mingw deps.

**Acceptance:** `otool -L lib/libmpv.2.dylib` (and every staged dylib)
shows only `@rpath/...`, `/usr/lib/...`, `/System/...` — no
`/opt/homebrew` or `/usr/local`. Same idea via `ldd`/Dependencies for
linux/windows. A from-scratch container/VM without Homebrew loads
libmpv.

---

## Bug 3 — cache-hit runs ship an incomplete macOS bundle

**Symptom / evidence:** run 25960133197 (build_mpv.py unchanged ->
macOS mpv cache HIT) produced `gamelibs-macos-arm64.zip` with **zero
`.pc` files** and only partial libav*. Run 25959761350 (full rebuild,
same code) produced the complete bundle (11 `.pc`). The consumer had
to use the full-build run's artifact.

**Root cause:** the `Cache libmpv+FFmpeg` step's `path:` only covers
`prebuilt/macos/arm64/lib/libmpv*` + `include/mpv` (grep the workflow:
~line 1135 macOS, 350 ubuntu, 743 windows). On a cache hit only those
are restored; the staged libav*/`.pc`/headers are absent, and the
release-archive step then zips an incomplete prefix.

**Fix:** make the mpv cache `path:` cover the **whole** staged mpv/av
contribution on all three jobs — `prebuilt/<plat>/<arch>/lib/libmpv*`,
`lib/libav*`, `lib/libsw*`, `lib/libpostproc*`, `lib/pkgconfig/*`,
`include/mpv`, `include/libav*`, `include/libsw*` (windows: `bin/*mpv*`,
`bin/av*`, `bin/sw*`, `lib/*.dll.a`, `lib/pkgconfig/*`, includes). OR
gate the release archive so a tag build always does a full rebuild
(skip the mpv cache when `startsWith(github.ref,'refs/tags/')`).
Prefer fixing the cache `path:` — keeps tag builds fast and correct.

**Acceptance:** trigger a cache-hit run (push a no-op/comment change so
build_mpv.py hash is unchanged) and confirm all three artifacts still
contain libmpv + every libav*/libsw* + all `.pc` + headers. Then a tag
build (`make release` -> push tag) publishes complete zips.

---

## After 1-3: release + verify

1. `make release` (patch -> v0.6.3; `.version` currently 0.6.2; the
   rock-sfx parked note expects v0.6.3, not the minor bump BUILD_MPV.md
   mentions — confirm with the human if unsure). Push tag; the
   `create-release` job (gated on `refs/tags/`) publishes per-platform
   zips.
2. Update BUILD_MPV.md: Phase 4 status, record the Bug-2 choice (a/b),
   tick the cache-bug note in the "macOS cache-key bug" section.
3. Ping the rock-sfx side: once v0.6.3 is up with relocatable `.pc` +
   self-contained libmpv, the rock-sfx consumer drops its local `.pc`
   prefix-rewrite workaround and just `gh release download`s.

Run-ID evidence trail: green CI = 25960133197; complete macOS bundle
= 25959761350; incomplete (cache-hit) = 25960133197.
