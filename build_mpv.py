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
    (cfg / "branch-ffmpeg").write_text(f"@{FFMPEG_TAG}\n")
    (cfg / "branch-mpv").write_text(f"@{MPV_TAG}\n")
    (cfg / "branch-libass").write_text(f"{LIBASS_REF}\n")
    (cfg / "branch-libplacebo").write_text(f"{LIBPLACEBO_REF}\n")
    return mb


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
    (mb / "ffmpeg_options").write_text(
        "\n".join([
            "--enable-shared",
            "--disable-static",
            "--enable-avdevice",
            "--disable-doc",
            "--disable-programs",
            "--disable-debug",
            "--enable-pic",
        ]) + "\n"
    )
    # mpv: build libmpv as a shared library; no CLI player needed.
    (mb / "mpv_options").write_text(
        "\n".join([
            "-Dlibmpv=true",
            "-Dcplayer=false",
            "-Ddefault_library=shared",
        ]) + "\n"
    )


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

    print("  windows: staged DLLs ->", binr, "import libs ->", lib)


def fix_macos_install_names(lib: Path):
    """Rewrite each dylib's id + inter-lib refs to @rpath/<name> so a
    consumer's -rpath,@loader_path/... resolves the whole set with no
    absolute build paths baked in (mirrors how build_sdl_image stages
    its deps)."""
    all_libs = [p for p in lib.iterdir() if ".dylib" in p.name]
    names = {p.name for p in all_libs}
    # Only edit real files; symlinks resolve through them. Editing a
    # symlink's "id" would rewrite the target repeatedly.
    for d in [p for p in all_libs if not p.is_symlink()]:
        run(["install_name_tool", "-id", f"@rpath/{d.name}", str(d)])
        out = subprocess.run(
            ["otool", "-L", str(d)], capture_output=True, text=True, check=True
        ).stdout
        for line in out.splitlines()[1:]:
            dep = line.strip().split(" ")[0]
            base = os.path.basename(dep)
            if base in names and not dep.startswith("@rpath/"):
                run(["install_name_tool", "-change", dep,
                     f"@rpath/{base}", str(d)])
        # Re-sign: macOS invalidates the signature on any LC edit.
        subprocess.run(["codesign", "--force", "--sign", "-", str(d)],
                        check=False)


def fix_linux_rpath(lib: Path):
    for so in lib.iterdir():
        if ".so" in so.name and so.is_file() and not so.is_symlink():
            subprocess.run(["patchelf", "--set-rpath", "$ORIGIN", str(so)],
                           check=False)


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
    # ./rebuild does: update -> build ffmpeg -> build mpv, honoring the
    # *_options files written above. mpv-build's scripts are POSIX sh;
    # on Windows we run under an MSYS2 MINGW64 shell, but Python's
    # subprocess uses CreateProcess (no shebang honoring) so the script
    # must be launched through `sh` explicitly. On unix the shebang
    # works directly.
    rebuild = (["sh", "./rebuild", "-j" + jobs]
               if plat == "windows"
               else ["./rebuild", "-j" + jobs])
    run(rebuild, cwd=mb)
    stage(mb, prefix)

    print("\n=== staged ===", flush=True)
    for f in sorted((prefix / "lib").glob("*")):
        print(" ", f.name)
    print("\nNext: wire stone-video/build.rs to this prefix and rerun "
          "the fm audio probe (BUILD_MPV.md Phase 1).", flush=True)


if __name__ == "__main__":
    sys.exit(main())
