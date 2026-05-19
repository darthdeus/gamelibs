#!/usr/bin/env python3
"""
Build libmpv + FFmpeg as a version-consistent unit via mpv-build.

See BUILD_MPV.md for the why, the pinned-version contract, and the
critical "ONE FFmpeg in the process" constraint. The short version:
mpv-build clones pinned FFmpeg + mpv and compiles them against each
other, so libmpv and libav* can never ABI-skew. We build FFmpeg
*shared* (not mpv-build's default static-into-libmpv) because the
Anvil recorder's `ffmpeg-the-third` Rust crate must link the SAME
libav* that libmpv uses -- a static-in-libmpv FFmpeg would force a
second copy and recreate the skew bug at the Rust boundary.

Output: prebuilt/<platform>/<arch>/{lib,include} with libmpv +
libav*/libsw* shared libs + headers + pkgconfig, install names
rewritten to @rpath (macOS) / $ORIGIN (linux) so existing consumer
rpaths resolve them with no new wiring.

Status: Phase 1 (macOS arm64). Linux = Phase 2 (CI), Windows = Phase 3.
"""

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

# --- Pinned version contract (see BUILD_MPV.md "Core decision") -------
# mpv-build tracks ffmpeg/mpv as git submodules; we pin all three.
# Update deliberately, never float. Record the resolved tags back into
# BUILD_MPV.md once a build succeeds.
MPV_BUILD_REPO = "https://github.com/mpv-player/mpv-build.git"
# mpv-build itself, pinned to a SHA (its scripts/configure flags are
# part of the contract too).
MPV_BUILD_COMMIT = "9443097290e82008f26f1597590926c63e7ae053"
# The ABI-critical pair: FFmpeg release tag <-> mpv release tag. mpv
# 0.40.0 supports FFmpeg >= 6.1; n7.1.1 is well within range. This is
# the pair whose skew caused the original fm crash -- pin both hard.
FFMPEG_TAG = "n7.1.1"
MPV_TAG = "v0.40.0"
# libass / libplacebo are statically linked INTO libmpv (no ABI skew
# possible across the process boundary), so "release" (latest upstream
# release tag, not master) is reproducible enough and avoids pinning a
# libplacebo too old for mpv 0.40. Revisit only if a build breaks.
#
# libass is NOT optional: mpv 0.40's meson.build does an unconditional
# `dependency('libass')` (there is no -Dlibass meson option -- passing
# one yields "Unknown option"), and patching mpv-build to skip building
# libass just makes that dependency unresolvable. Shipping a *system*
# libass would re-introduce an un-vendored runtime dep, defeating the
# whole point. So mpv-build builds libass static and links it into
# libmpv -- self-contained, exactly as on the Phase-2 mac/linux build.
LIBASS_REF = "release"
LIBPLACEBO_REF = "release"

ROOT = Path(__file__).resolve().parent


def get_platform():
    s = platform.system().lower()
    if s == "darwin":
        return "macos"
    if s == "windows":
        return "windows"
    return "linux"


def get_arch():
    m = platform.machine().lower()
    if m in ("arm64", "aarch64"):
        return "arm64"
    return "x86_64"


def run(cmd, cwd=None, env=None):
    print(f"+ {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, cwd=cwd, env=env, check=True)


def write_lf(path: Path, text: str):
    """Write with hard LF endings. On Windows this script runs under
    mingw-python, where Path.write_text() (newline=None) translates \\n
    -> \\r\\n. mpv-build's *-config scripts split *_options with
    IFS=<newline> (LF only), so a CRLF file leaves a trailing \\r on
    every token: `-Dlibmpv=true\\r` -> meson "Option libmpv value
    true"; `--disable-static\\r` -> ffmpeg eval junk. config/branch-*
    and any patched POSIX script are equally CRLF-poisoned. Force LF
    for every generated file, every platform."""
    path.write_text(text, newline="\n")


def clone_mpv_build(work: Path) -> Path:
    mb = work / "mpv-build"
    if not mb.exists():
        run(["git", "clone", MPV_BUILD_REPO, str(mb)])
    run(["git", "fetch", "--all"], cwd=mb)
    run(["git", "checkout", MPV_BUILD_COMMIT], cwd=mb)
    # Pin via mpv-build's own mechanism: config/branch-<project> files,
    # honored by ./update on every run (incl. through ./rebuild). The
    # "@<ref>" form maps to `git checkout <ref>`; "release" = latest
    # upstream release tag. This is what makes the build reproducible --
    # a bare post-update `git checkout` got reset by the next ./update
    # (the gap recorded in BUILD_MPV.md).
    cfg = mb / "config"
    cfg.mkdir(exist_ok=True)
    write_lf(cfg / "branch-ffmpeg", f"@{FFMPEG_TAG}\n")
    write_lf(cfg / "branch-mpv", f"@{MPV_TAG}\n")
    write_lf(cfg / "branch-libass", f"{LIBASS_REF}\n")
    write_lf(cfg / "branch-libplacebo", f"{LIBPLACEBO_REF}\n")
    return mb


def patch_out_mpv_build_libass(mb: Path):
    """Windows only: comment out mpv-build's two libass invocation
    lines in its `build` script so it does NOT autotools-build libass.

    Why: libass's autogen.sh -> autoreconf -> aclocal hits an
    msys2/perl path-canonicalization bug -- aclocal naively strips the
    drive letter from its acdir, so /usr/share/aclocal is searched as a
    bogus drive-rooted path and progtest.m4 "does not exist" though it
    is present. Six CI rounds of shims (ACLOCAL_PATH, --system-acdir,
    automake 1.16, /etc/fstab, install relocation + symlink) each hit a
    different facet of the same msys path mangling. The durable fix is
    to take autotools out of the libass path entirely: build libass
    with Meson (build_libass_meson), exactly as upstream mpv CI does on
    Windows. meson never invokes aclocal, so the failure class is gone.

    Only the two simple invocation lines are commented (not any line
    containing 'libass' -- that earlier broke function bodies). They
    are plain `scripts/libass-config` / `scripts/libass-build "$@"`
    lines; commenting them is safe. mac/linux keep the autotools libass
    path (proven green) -- this is Windows-only."""
    build_script = mb / "build"
    out = []
    for ln in build_script.read_text().splitlines():
        s = ln.strip()
        if s in ("scripts/libass-config", 'scripts/libass-build "$@"'):
            out.append("# [build_mpv.py] libass via meson: " + ln)
        else:
            out.append(ln)
    write_lf(build_script, "\n".join(out) + "\n")


def build_libass_meson(mb: Path):
    """Windows only: build the libass mpv-build cloned (at the pinned
    release tag, via config/branch-libass) with Meson, static, into
    mpv-build's build_libs prefix. ffmpeg-config / mpv-config prepend
    build_libs/lib/pkgconfig to PKG_CONFIG_PATH, so mpv's mandatory
    `dependency('libass')` resolves to this static build and links it
    into libmpv -- same end state as the autotools path on mac/linux,
    just without aclocal."""
    src = mb / "libass"
    if not src.exists():
        raise SystemExit(
            f"libass source not at {src} -- mpv-build ./update did not "
            "clone it; cannot meson-build libass.")
    prefix = mb / "build_libs"
    bdir = src / "build"
    if bdir.exists():
        shutil.rmtree(bdir)
    # Minimal option set: static lib so it links INTO libmpv; let
    # font backend auto-detect (fontconfig is in the MSYS2 dep set).
    # Avoid passing libass-specific -D names that vary by version
    # ("Unknown option" aborts meson) -- builtins only.
    run(["meson", "setup", "build",
         f"--prefix={prefix.as_posix()}",
         "--libdir=lib",
         "--default-library=static",
         "--buildtype=release"], cwd=src)
    run(["meson", "compile", "-C", "build"], cwd=src)
    run(["meson", "install", "-C", "build"], cwd=src)
    pc = prefix / "lib" / "pkgconfig" / "libass.pc"
    if not pc.exists():
        raise SystemExit(
            f"libass.pc not installed at {pc} after meson install -- "
            "mpv's dependency('libass') would fail to resolve.")
    print(f"  libass (meson, static) -> {prefix}", flush=True)


def write_options(mb: Path):
    # mpv-build APPENDS this file to its own ffmpeg defaults
    # (--enable-static --disable-shared --enable-gpl --enable-gnutls ...);
    # FFmpeg configure takes the last value for a flag, so listing
    # --enable-shared/--disable-static here flips it to shared (the
    # whole point: one shared FFmpeg both libmpv and ffmpeg-the-third
    # link). avdevice is ON by default in FFmpeg -- the flag is
    # --enable-avdevice (NOT --enable-libavdevice, which aborts
    # configure); keep it explicit so a future default change can't
    # silently drop the Anvil recorder's screen-capture inputs.
    # ONE OPTION PER LINE -- newline-joined, NOT space-joined. mpv-build's
    # scripts/ffmpeg-config reads this file as `IFS=<newline>; set --
    # $(cat ffmpeg_options) "$@"` -- it word-splits on NEWLINE ONLY, not
    # spaces. A single space-joined line therefore arrives as ONE giant
    # argv string and ffmpeg's configure chokes (`eval: __disable_static:
    # not found`). Phase 2 (green on mac+linux) used newline-joined; the
    # later single-line "MSYS2 robustness" change was a misdiagnosis --
    # the real Windows breakage was CRLF (see write_lf), fixed there. LF
    # endings via write_lf make newline-joined correct on every platform.
    write_lf(mb / "ffmpeg_options", "\n".join([
        "--enable-shared",
        "--disable-static",
        "--enable-avdevice",
        "--disable-doc",
        "--disable-programs",
        "--disable-debug",
        "--enable-pic",
    ]) + "\n")
    # mpv: build libmpv as a shared library; no CLI player needed.
    # scripts/mpv-config splits this the same IFS=<newline> way.
    write_lf(mb / "mpv_options", "\n".join([
        "-Dlibmpv=true",
        "-Dcplayer=false",
        "-Ddefault_library=shared",
    ]) + "\n")
    # NB: do NOT add -Dlibass=disabled. mpv 0.40 has no `libass` meson
    # option (meson rejects it: "Unknown option"); libass is a hard
    # `dependency()` satisfied by mpv-build's own static libass build
    # (config/branch-libass). See clone_mpv_build() / LIBASS_REF.


def make_pc_relocatable(pcdir: Path):
    """Rewrite every staged `.pc` so it is self-locating from wherever
    the prefix is extracted, instead of baking the CI build host's
    absolute paths (Bug 1, CONSUMER_CUTOVER_FIXES.md).

    ffmpeg's `.pc` bake an absolute `prefix`/`libdir`/`includedir`
    pointing at the runner's `build_libs` (nonexistent on any consumer);
    meson's `mpv.pc` bakes the build host's brew `prefix=/opt/homebrew`
    with `libdir=${prefix}/lib` -- a consumer that points
    PKG_CONFIG_PATH at the vendored prefix would then link *Homebrew's*
    libmpv, recreating the exact ABI-skew crash this vendoring prevents.

    `${pcfiledir}` is a pkg-config/pkgconf builtin = the dir containing
    the `.pc` file (here `<prefix>/lib/pkgconfig`), so `../..` is the
    prefix root with zero consumer env. Only the three location
    variables are rewritten; `Requires`/`Libs`/`Cflags` already use
    `${libdir}`/`${includedir}` (ffmpeg's do) and are left intact."""
    repl = {
        "prefix": "${pcfiledir}/../..",
        "libdir": "${prefix}/lib",
        "includedir": "${prefix}/include",
        # exec_prefix is ${prefix}-relative in both ffmpeg & meson .pc;
        # normalize defensively in case a generator baked it absolute.
        "exec_prefix": "${prefix}",
    }
    for pc in sorted(pcdir.glob("*.pc")):
        out = []
        for ln in pc.read_text().splitlines():
            key = ln.split("=", 1)[0].strip() if "=" in ln else None
            # Only a leading `key=...` assignment (not `Cflags:` etc.,
            # not an indented continuation) is a location variable.
            if key in repl and ln.lstrip().startswith(key):
                out.append(f"{key}={repl[key]}")
            else:
                out.append(ln)
        write_lf(pc, "\n".join(out) + "\n")
        print(f"  relocatable: {pc.name}", flush=True)


def stage(mb: Path, prefix: Path):
    lib = prefix / "lib"
    inc = prefix / "include"
    for d in (lib, inc, lib / "pkgconfig"):
        d.mkdir(parents=True, exist_ok=True)

    plat = get_platform()
    if plat == "windows":
        return stage_windows(mb, prefix)

    ext = {"macos": ".dylib"}.get(plat, ".so")

    # FFmpeg shared libs + headers (mpv-build installs FFmpeg into
    # mpv-build/build_libs by default; fall back to the in-tree dirs).
    ff_prefix = mb / "build_libs"
    src_lib = ff_prefix / "lib"
    src_inc = ff_prefix / "include"
    if not src_lib.exists():
        raise SystemExit(
            f"FFmpeg install dir not found at {src_lib}. "
            "mpv-build layout changed -- inspect mpv-build/ and update stage()."
        )
    # Preserve the soname symlink chain (libfoo.dylib -> libfoo.62.dylib
    # -> libfoo.62.32.100.dylib): copy real files once, recreate
    # symlinks as symlinks. Dereferencing every link (the old bug) made
    # 3x copies and broke install_name identity.
    def put_lib(src: Path, dst: Path):
        if dst.exists() or dst.is_symlink():
            dst.unlink()
        if src.is_symlink():
            dst.symlink_to(os.readlink(src))
        else:
            shutil.copy2(src, dst)

    for f in src_lib.iterdir():
        if f.is_dir():
            continue
        if ext in f.name:
            put_lib(f, lib / f.name)
    # FFmpeg installs its .pc files under lib/pkgconfig/, NOT lib/ --
    # the original scan missed them entirely (v0.6.0 shipped zero
    # libav*.pc, so consumers couldn't PKG_CONFIG_PATH the prefix).
    src_pc = src_lib / "pkgconfig"
    if src_pc.is_dir():
        for pc in src_pc.glob("*.pc"):
            shutil.copy2(pc, lib / "pkgconfig" / pc.name)
    for sub in src_inc.iterdir():
        if sub.is_dir():
            shutil.copytree(sub, inc / sub.name, dirs_exist_ok=True)

    # libmpv: explicit paths (rglob caught meson's libmpv.2.dylib.p/
    # build dir). meson emits libmpv.<abi>.dylib + a libmpv.dylib
    # symlink directly in mpv/build/.
    mpv_build_dir = mb / "mpv" / "build"
    for f in mpv_build_dir.iterdir():
        if f.is_dir():
            continue
        if f.name.startswith("libmpv") and ext in f.name:
            put_lib(f, lib / f.name)
    mpv_hdr = mb / "mpv" / "include" / "mpv"
    if not mpv_hdr.exists():
        mpv_hdr = mb / "mpv" / "libmpv"
    shutil.copytree(mpv_hdr, inc / "mpv", dirs_exist_ok=True)
    mpv_pc = mpv_build_dir / "meson-private" / "mpv.pc"
    if mpv_pc.exists():
        shutil.copy2(mpv_pc, lib / "pkgconfig" / "mpv.pc")

    make_pc_relocatable(lib / "pkgconfig")

    if plat == "macos":
        fix_macos_install_names(lib)
    elif plat == "linux":
        fix_linux_rpath(lib)


def stage_windows(mb: Path, prefix: Path):
    """mingw mpv-build layout differs from unix: shared objects are
    `name-MAJOR.dll` in build_libs/bin (+ mpv/build), import libs are
    `*.dll.a` in build_libs/lib. gamelibs Windows convention (matches
    SDL2): DLLs -> prefix/bin, import libs + pkgconfig -> prefix/lib,
    headers -> prefix/include. No symlinks, no rpath -- co-located
    DLLs in bin/ resolve at load time."""
    binr = prefix / "bin"
    lib = prefix / "lib"
    inc = prefix / "include"
    for d in (binr, lib, inc, lib / "pkgconfig"):
        d.mkdir(parents=True, exist_ok=True)

    ff = mb / "build_libs"
    ff_bin = ff / "bin"
    ff_lib = ff / "lib"
    ff_inc = ff / "include"
    if not ff_lib.exists():
        raise SystemExit(
            f"FFmpeg install dir not found at {ff_lib}. "
            "mpv-build mingw layout changed -- inspect build_libs/ and "
            "update stage_windows()."
        )

    # FFmpeg + deps DLLs (avcodec-61.dll, swresample-5.dll, ...). mingw
    # may also drop runtime DLLs here (libwinpthread, zlib) -- ship them
    # too; a consumer DLL dir must be self-resolving.
    if ff_bin.is_dir():
        for f in ff_bin.glob("*.dll"):
            shutil.copy2(f, binr / f.name)
    # Import libs (.dll.a) + pkgconfig for the linker / build.rs.
    for f in ff_lib.iterdir():
        if f.is_file() and (f.name.endswith(".dll.a") or f.suffix == ".lib"):
            shutil.copy2(f, lib / f.name)
    src_pc = ff_lib / "pkgconfig"
    if src_pc.is_dir():
        for pc in src_pc.glob("*.pc"):
            shutil.copy2(pc, lib / "pkgconfig" / pc.name)
    for sub in ff_inc.iterdir():
        if sub.is_dir():
            shutil.copytree(sub, inc / sub.name, dirs_exist_ok=True)

    # libmpv: meson on mingw emits libmpv-2.dll + libmpv.dll.a in
    # mpv/build (DLL may also land via the meson install; scan both).
    mpv_build_dir = mb / "mpv" / "build"
    for f in mpv_build_dir.rglob("*mpv*"):
        if f.is_dir():
            continue
        if f.name.endswith(".dll"):
            shutil.copy2(f, binr / f.name)
        elif f.name.endswith(".dll.a") or f.name.endswith(".lib"):
            shutil.copy2(f, lib / f.name)
    mpv_hdr = mb / "mpv" / "include" / "mpv"
    if not mpv_hdr.exists():
        mpv_hdr = mb / "mpv" / "libmpv"
    shutil.copytree(mpv_hdr, inc / "mpv", dirs_exist_ok=True)
    mpv_pc = mpv_build_dir / "meson-private" / "mpv.pc"
    if mpv_pc.exists():
        shutil.copy2(mpv_pc, lib / "pkgconfig" / "mpv.pc")

    make_pc_relocatable(lib / "pkgconfig")
    bundle_windows_deps(binr)

    print("  windows: staged DLLs ->", binr, "import libs ->", lib)


def _otool_deps(dylib: Path) -> list[str]:
    out = subprocess.run(
        ["otool", "-L", str(dylib)], capture_output=True, text=True,
        check=True).stdout
    # otool's first line is the file itself; the rest are deps. Each
    # dep line is `\t<path> (compatibility ...)`.
    deps = []
    for line in out.splitlines()[1:]:
        dep = line.strip().split(" ", 1)[0]
        if dep:
            deps.append(dep)
    return deps


def fix_macos_install_names(lib: Path):
    """Make the staged set self-contained on macOS (Bug 2):

    1. Rewrite each staged dylib's id + inter-lib refs to `@rpath/<name>`
       so a consumer's `-rpath,@loader_path/...` resolves the whole set
       with no absolute build paths baked in.
    2. Recursively vendor every external (`/opt/homebrew`, `/usr/local`)
       dependency -- libmpv links the libass font stack
       (fontconfig/harfbuzz/fribidi) + lcms2/jpeg from Homebrew kegs;
       without this a machine with no Homebrew cannot load libmpv,
       defeating "vendored / hermetic". Each external dep is copied into
       `<prefix>/lib`, `-id @rpath/<name>`'d, every referrer `-change`'d
       to `@rpath/<name>`, then itself scanned (harfbuzz->graphite2/glib,
       fontconfig->expat/png/freetype, glib->pcre2/intl, ...).

    Mirrors how build_sdl_image stages its deps, extended with the
    transitive walk libmpv's richer dep graph needs."""
    def is_external(p: str) -> bool:
        return p.startswith("/opt/homebrew") or p.startswith("/usr/local")

    all_libs = [p for p in lib.iterdir() if ".dylib" in p.name]
    names = {p.name for p in all_libs}
    edited: set[Path] = set()
    # Worklist of real dylibs whose deps still need scanning. Symlinks
    # resolve through their target; editing a symlink's id rewrites the
    # target repeatedly, so only ever operate on real files.
    queue = [p for p in all_libs if not p.is_symlink()]

    while queue:
        d = queue.pop()
        if d in edited:
            continue
        edited.add(d)
        run(["install_name_tool", "-id", f"@rpath/{d.name}", str(d)])
        for dep in _otool_deps(d):
            base = os.path.basename(dep)
            if dep.startswith("@rpath/"):
                continue
            if base in names:
                # Already-staged sibling (libav*, libmpv, or a dep we
                # vendored on an earlier iteration): just re-point.
                run(["install_name_tool", "-change", dep,
                     f"@rpath/{base}", str(d)])
            elif is_external(dep):
                target = lib / base
                if base not in names:
                    # Resolve through any keg symlink to the real file.
                    real = Path(dep).resolve()
                    shutil.copy2(real, target)
                    target.chmod(0o644)
                    run(["install_name_tool", "-id",
                         f"@rpath/{base}", str(target)])
                    names.add(base)
                    queue.append(target)
                run(["install_name_tool", "-change", dep,
                     f"@rpath/{base}", str(d)])
            # else: /usr/lib, /System/... -- guaranteed present, leave.

    # Re-sign every edited file: macOS invalidates the signature on any
    # load-command edit.
    for d in edited:
        subprocess.run(["codesign", "--force", "--sign", "-", str(d)],
                        check=False)

    leaks = sorted(
        f"{d.name}: {dep}"
        for d in edited for dep in _otool_deps(d)
        if is_external(dep))
    if leaks:
        raise SystemExit(
            "fix_macos_install_names: external deps still present after "
            "bundling (Bug 2 acceptance failed):\n  " + "\n  ".join(leaks))
    print(f"  macos: {len(edited)} dylibs self-contained "
          f"(@rpath only, no /opt/homebrew or /usr/local)", flush=True)


# libmpv's libass font stack (+ image codecs) leaks the same way on
# Linux as the Homebrew kegs do on macOS -- the apt-installed
# libfontconfig/harfbuzz/fribidi/lcms2/jpeg are NOT guaranteed on a
# consumer machine. A macOS-style "anything outside /usr/lib" rule is
# WRONG here: libGL/libX11/libwayland/libvulkan/libdrm also live in
# /usr/lib and MUST stay system (they bind to the host's GPU driver).
# So Linux bundling is allowlist-driven: only these soname stems (and
# their transitive closure within the same allowlist) are vendored.
_LINUX_VENDOR_STEMS = {
    "fontconfig", "harfbuzz", "fribidi", "lcms2", "jpeg", "freetype",
    "png", "png16", "graphite2", "expat", "bz2", "uuid",
    "glib-2.0", "gobject-2.0", "gthread-2.0", "gmodule-2.0",
    "pcre2-8", "pcre", "ffi", "intl",
    "brotlidec", "brotlienc", "brotlicommon",
}


def _soname_stem(soname: str) -> str:
    # libfontconfig.so.1 -> fontconfig ; libpcre2-8.so.0 -> pcre2-8
    n = soname
    if n.startswith("lib"):
        n = n[3:]
    return n.split(".so", 1)[0]


def _ldd_resolved(so: Path) -> dict[str, str]:
    """soname -> absolute resolved path, for `=> /path` ldd lines."""
    out = subprocess.run(["ldd", str(so)], capture_output=True,
                          text=True).stdout
    resolved = {}
    for line in out.splitlines():
        line = line.strip()
        if "=>" not in line:
            continue
        soname, _, rhs = line.partition("=>")
        rhs = rhs.strip()
        if not rhs.startswith("/"):
            continue  # "not found" / vdso
        path = rhs.split(" (", 1)[0].strip()
        resolved[soname.strip()] = path
    return resolved


def fix_linux_rpath(lib: Path):
    """Set $ORIGIN rpath on the staged .so set AND recursively vendor
    the libass font / image-codec stack (Bug 2, Linux analogue of the
    macOS Homebrew bundling). GPU/display libs are deliberately NOT
    bundled -- see _LINUX_VENDOR_STEMS."""
    def staged_real():
        return [p for p in lib.iterdir()
                if ".so" in p.name and p.is_file() and not p.is_symlink()]

    edited: set[Path] = set()
    queue = staged_real()
    while queue:
        so = queue.pop()
        if so in edited:
            continue
        edited.add(so)
        subprocess.run(["patchelf", "--set-rpath", "$ORIGIN", str(so)],
                       check=False)
        for soname, src in _ldd_resolved(so).items():
            if _soname_stem(soname) not in _LINUX_VENDOR_STEMS:
                continue
            dst = lib / soname
            if not dst.exists():
                shutil.copy2(Path(src).resolve(), dst)
                dst.chmod(0o644)
                # Match the staged soname-link convention so a
                # DT_NEEDED `libfoo.so.1` finds it next to libmpv.
                subprocess.run(["patchelf", "--set-rpath", "$ORIGIN",
                                str(dst)], check=False)
                queue.append(dst)

    leaks = []
    for so in edited:
        for soname, src in _ldd_resolved(so).items():
            stem = _soname_stem(soname)
            if stem in _LINUX_VENDOR_STEMS and not (lib / soname).exists():
                leaks.append(f"{so.name}: {soname} -> {src}")
    if leaks:
        raise SystemExit(
            "fix_linux_rpath: vendorable deps still unbundled "
            "(Bug 2 acceptance failed):\n  " + "\n  ".join(leaks))
    print(f"  linux: {len(edited)} shared objects, $ORIGIN rpath, "
          f"font/codec stack vendored", flush=True)


def bundle_windows_deps(binr: Path):
    """Copy the mingw font/codec DLLs libmpv pulls in (libass is static
    into libmpv, but its harfbuzz/fribidi/fontconfig/freetype/lcms2 are
    dynamic MSYS2 DLLs) into prefix/bin so the dir is self-resolving on
    a machine without MSYS2 (Bug 2, Windows analogue). System DLLs
    (C:\\Windows\\System32: KERNEL32, msvcrt, ...) are left alone; only
    deps resolving under the MSYS2 tree are vendored, recursively."""
    def msys_ldd(dll: Path) -> dict[str, str]:
        out = subprocess.run(["sh", "-c", f"ldd '{dll.as_posix()}'"],
                              capture_output=True, text=True).stdout
        res = {}
        for line in out.splitlines():
            line = line.strip()
            if "=>" not in line:
                continue
            name, _, rhs = line.partition("=>")
            rhs = rhs.strip()
            if not rhs:
                continue
            path = rhs.split(" (", 1)[0].strip()
            low = path.lower()
            # Skip the Windows system dir; keep MSYS2/mingw paths
            # (/mingw64/bin, /usr/bin, C:\\msys64\\...).
            if "/windows/" in low or "\\windows\\" in low:
                continue
            if path.startswith("/") or ":" in path:
                res[name.strip()] = path
        return res

    edited: set[Path] = set()
    queue = [p for p in binr.glob("*.dll")]
    while queue:
        dll = queue.pop()
        if dll in edited or not dll.exists():
            continue
        edited.add(dll)
        for name, src in msys_ldd(dll).items():
            dst = binr / name
            if dst.exists():
                continue
            sp = subprocess.run(
                ["sh", "-c", f"cygpath -w '{src}'"],
                capture_output=True, text=True)
            real = sp.stdout.strip() or src
            try:
                shutil.copy2(real, dst)
            except OSError as e:
                print(f"  windows: WARN could not vendor {name} "
                      f"({src}): {e}", flush=True)
                continue
            queue.append(dst)
    print(f"  windows: bin/ self-resolving "
          f"({len(list(binr.glob('*.dll')))} DLLs)", flush=True)


def main():
    plat, arch = get_platform(), get_arch()
    print(f"=== build_mpv: {plat}/{arch} "
          f"(ffmpeg {FFMPEG_TAG}, mpv {MPV_TAG}) ===", flush=True)

    work = ROOT / "build" / "mpv"
    work.mkdir(parents=True, exist_ok=True)
    prefix = ROOT / "prebuilt" / plat / arch

    mb = clone_mpv_build(work)
    write_options(mb)
    jobs = str(os.cpu_count() or 4)
    # mpv-build's scripts are POSIX sh; on Windows we run under an MSYS2
    # MINGW64 shell, but Python's subprocess uses CreateProcess (no
    # shebang honoring) so scripts must be launched through `sh`. On
    # unix the shebang works directly.
    #
    # unix: ./rebuild = update -> build (ffmpeg + libass autotools +
    # libplacebo + mpv), proven green on mac/linux.
    #
    # windows: split the phases. ./update clones all sources at the
    # pinned refs; then build libass with Meson (autotools/aclocal is
    # broken under msys2 -- see patch_out_mpv_build_libass) and comment
    # mpv-build's own libass steps; then ./build compiles ffmpeg +
    # libplacebo + mpv, which find the meson libass via pkg-config.
    if plat == "windows":
        run(["sh", "./update"], cwd=mb)
        patch_out_mpv_build_libass(mb)
        build_libass_meson(mb)
        run(["sh", "./build", "-j" + jobs], cwd=mb)
    else:
        run(["./rebuild", "-j" + jobs], cwd=mb)
    stage(mb, prefix)

    print("\n=== staged ===", flush=True)
    for f in sorted((prefix / "lib").glob("*")):
        print(" ", f.name)
    print("\nNext: wire stone-video/build.rs to this prefix and rerun "
          "the fm audio probe (BUILD_MPV.md Phase 1).", flush=True)


if __name__ == "__main__":
    sys.exit(main())
