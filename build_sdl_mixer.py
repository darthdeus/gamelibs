#!/usr/bin/env python3
"""
Build script for SDL_mixer
Builds SDL_mixer with OGG, Vorbis, FLAC, and MP3 support
"""

import os
import sys
import shutil
import subprocess
import platform
import urllib.request
import tarfile
import zipfile
from pathlib import Path

# Version configuration
SDL_MIXER_VERSION = "2.8.0"
# SDL_mixer is now vendored in the repository

LIBOGG_VERSION = "1.3.5"
LIBOGG_URL = f"https://downloads.xiph.org/releases/ogg/libogg-{LIBOGG_VERSION}.tar.gz"

LIBVORBIS_VERSION = "1.3.7"
LIBVORBIS_URL = f"https://downloads.xiph.org/releases/vorbis/libvorbis-{LIBVORBIS_VERSION}.tar.gz"

FLAC_VERSION = "1.4.3"
FLAC_URL = f"https://downloads.xiph.org/releases/flac/flac-{FLAC_VERSION}.tar.xz"

MPG123_VERSION = "1.32.10"
MPG123_URL = f"https://sourceforge.net/projects/mpg123/files/mpg123/{MPG123_VERSION}/mpg123-{MPG123_VERSION}.tar.bz2"

def get_platform():
    """Detect the current platform"""
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    elif system == "windows":
        return "windows"
    return "linux"

def download_file(url, dest):
    """Download a file from URL to destination"""
    print(f"Downloading {url}...")
    urllib.request.urlretrieve(url, dest)
    print(f"Downloaded to {dest}")

def extract_archive(archive_path, dest_dir):
    """Extract various archive formats"""
    print(f"Extracting {archive_path}...")
    archive_str = str(archive_path)
    if archive_str.endswith('.tar.gz'):
        with tarfile.open(archive_path, 'r:gz') as tar:
            tar.extractall(dest_dir)
    elif archive_str.endswith('.tar.xz'):
        with tarfile.open(archive_path, 'r:xz') as tar:
            tar.extractall(dest_dir)
    elif archive_str.endswith('.tar.bz2'):
        with tarfile.open(archive_path, 'r:bz2') as tar:
            tar.extractall(dest_dir)
    elif archive_str.endswith('.zip'):
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(dest_dir)

def run_command(cmd, cwd=None, env=None):
    """Run a shell command and check for errors"""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}")
        if result.stdout:
            print(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"STDERR:\n{result.stderr}")
        sys.exit(1)
    return result

def build_libogg(build_dir, install_dir, platform_name):
    """Build libogg"""
    print("\n=== Building libogg ===")
    ogg_archive = build_dir / f"libogg-{LIBOGG_VERSION}.tar.gz"
    ogg_src = build_dir / f"libogg-{LIBOGG_VERSION}"
    
    if not ogg_archive.exists():
        download_file(LIBOGG_URL, ogg_archive)
    
    if ogg_src.exists():
        shutil.rmtree(ogg_src)
    extract_archive(ogg_archive, build_dir)
    
    # Build with CMake
    build_path = ogg_src / "build"
    build_path.mkdir(exist_ok=True)
    
    cmake_args = [
        "cmake", "..",
        f"-DCMAKE_INSTALL_PREFIX={install_dir}",
        "-DBUILD_SHARED_LIBS=OFF",
        "-DCMAKE_BUILD_TYPE=Release",
        "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",  # Allow older CMakeLists.txt
        "-DCMAKE_POSITION_INDEPENDENT_CODE=ON"  # Build with -fPIC for shared lib linking
    ]
    
    if platform_name == "windows":
        cmake_args.extend(["-G", "Visual Studio 17 2022", "-A", "x64"])
    elif platform_name == "macos":
        cmake_args.append("-DCMAKE_OSX_ARCHITECTURES=arm64")
    
    run_command(cmake_args, cwd=build_path)
    run_command(["cmake", "--build", ".", "--config", "Release"], cwd=build_path)
    run_command(["cmake", "--install", "."], cwd=build_path)

def build_libvorbis(build_dir, install_dir, platform_name):
    """Build libvorbis (requires libogg)"""
    print("\n=== Building libvorbis ===")
    vorbis_archive = build_dir / f"libvorbis-{LIBVORBIS_VERSION}.tar.gz"
    vorbis_src = build_dir / f"libvorbis-{LIBVORBIS_VERSION}"
    
    if not vorbis_archive.exists():
        download_file(LIBVORBIS_URL, vorbis_archive)
    
    if vorbis_src.exists():
        shutil.rmtree(vorbis_src)
    extract_archive(vorbis_archive, build_dir)
    
    # Build with CMake
    build_path = vorbis_src / "build"
    build_path.mkdir(exist_ok=True)
    
    cmake_args = [
        "cmake", "..",
        f"-DCMAKE_INSTALL_PREFIX={install_dir}",
        f"-DOGG_ROOT={install_dir}",
        "-DBUILD_SHARED_LIBS=OFF",
        "-DCMAKE_BUILD_TYPE=Release",
        "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",  # Allow older CMakeLists.txt
        "-DCMAKE_POSITION_INDEPENDENT_CODE=ON"  # Build with -fPIC for shared lib linking
    ]
    
    if platform_name == "windows":
        cmake_args.extend(["-G", "Visual Studio 17 2022", "-A", "x64"])
    elif platform_name == "macos":
        cmake_args.append("-DCMAKE_OSX_ARCHITECTURES=arm64")
    
    run_command(cmake_args, cwd=build_path)
    run_command(["cmake", "--build", ".", "--config", "Release"], cwd=build_path)
    run_command(["cmake", "--install", "."], cwd=build_path)

def build_flac(build_dir, install_dir, platform_name):
    """Build FLAC"""
    print("\n=== Building FLAC ===")
    flac_archive = build_dir / f"flac-{FLAC_VERSION}.tar.xz"
    flac_src = build_dir / f"flac-{FLAC_VERSION}"
    
    if not flac_archive.exists():
        download_file(FLAC_URL, flac_archive)
    
    if flac_src.exists():
        shutil.rmtree(flac_src)
    extract_archive(flac_archive, build_dir)
    
    # Build with CMake
    build_path = flac_src / "build"
    build_path.mkdir(exist_ok=True)
    
    cmake_args = [
        "cmake", "..",
        f"-DCMAKE_INSTALL_PREFIX={install_dir}",
        f"-DOGG_ROOT={install_dir}",
        "-DBUILD_SHARED_LIBS=OFF",
        "-DBUILD_PROGRAMS=OFF",
        "-DBUILD_EXAMPLES=OFF",
        "-DBUILD_TESTING=OFF",
        "-DBUILD_DOCS=OFF",
        "-DINSTALL_MANPAGES=OFF",
        "-DWITH_OGG=ON",
        "-DCMAKE_BUILD_TYPE=Release",
        "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",  # Allow older CMakeLists.txt
        "-DCMAKE_POSITION_INDEPENDENT_CODE=ON"  # Build with -fPIC for shared lib linking
    ]
    
    if platform_name == "windows":
        cmake_args.extend(["-G", "Visual Studio 17 2022", "-A", "x64"])
    elif platform_name == "macos":
        cmake_args.append("-DCMAKE_OSX_ARCHITECTURES=arm64")
    
    env = os.environ.copy()
    env["PKG_CONFIG_PATH"] = f"{install_dir.resolve()}/lib/pkgconfig"
    
    run_command(cmake_args, cwd=build_path, env=env)
    run_command(["cmake", "--build", ".", "--config", "Release"], cwd=build_path)
    run_command(["cmake", "--install", "."], cwd=build_path)

def build_mpg123(build_dir, install_dir, platform_name):
    """Build mpg123 for MP3 support"""
    print("\n=== Building mpg123 ===")
    mpg123_archive = build_dir / f"mpg123-{MPG123_VERSION}.tar.bz2"
    mpg123_src = build_dir / f"mpg123-{MPG123_VERSION}"
    
    if not mpg123_archive.exists():
        download_file(MPG123_URL, mpg123_archive)
    
    if mpg123_src.exists():
        shutil.rmtree(mpg123_src)
    extract_archive(mpg123_archive, build_dir)
    
    if platform_name == "windows":
        # Windows: Use CMake build if available, otherwise skip
        cmake_lists = mpg123_src / "CMakeLists.txt"
        if cmake_lists.exists():
            build_path = mpg123_src / "build"
            build_path.mkdir(exist_ok=True)
            
            cmake_args = [
                "cmake", "..",
                f"-DCMAKE_INSTALL_PREFIX={install_dir}",
                "-DBUILD_SHARED_LIBS=OFF",
                "-DCMAKE_BUILD_TYPE=Release",
                "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",  # Allow older CMakeLists.txt
                "-G", "Visual Studio 17 2022", "-A", "x64"
            ]
            
            run_command(cmake_args, cwd=build_path)
            run_command(["cmake", "--build", ".", "--config", "Release"], cwd=build_path)
            run_command(["cmake", "--install", "."], cwd=build_path)
        else:
            print("Warning: mpg123 CMake build not available for Windows, skipping MP3 support")
            return
    else:
        # Unix-like build
        configure_args = [
            "./configure",
            f"--prefix={install_dir.resolve()}",
            "--enable-static",
            "--disable-shared",
            "--with-audio=dummy",  # We only need decoding, not audio output
            "--enable-int-quality=yes",
            "--with-pic"  # Build with -fPIC for shared lib linking
        ]
        
        if platform_name == "macos":
            configure_args.append("--host=aarch64-apple-darwin")
        
        run_command(configure_args, cwd=mpg123_src)
        run_command(["make", f"-j{os.cpu_count()}"], cwd=mpg123_src)
        run_command(["make", "install"], cwd=mpg123_src)

def build_sdl_mixer(build_dir, install_dir, platform_name):
    """Build SDL_mixer with all dependencies"""
    print("\n=== Building SDL_mixer ===")
    # Use vendored source instead of downloading
    vendored_src = Path(f"SDL2_mixer-{SDL_MIXER_VERSION}")
    sdl_mixer_src = build_dir / f"SDL2_mixer-{SDL_MIXER_VERSION}"
    
    if not vendored_src.exists():
        print(f"Error: Vendored SDL_mixer source not found at {vendored_src}")
        print("Please ensure SDL2_mixer-2.8.0 directory exists in the project root")
        sys.exit(1)
    
    if sdl_mixer_src.exists():
        shutil.rmtree(sdl_mixer_src)
    
    # Copy vendored source to build directory
    print(f"Copying vendored source from {vendored_src} to {sdl_mixer_src}")
    shutil.copytree(vendored_src, sdl_mixer_src)
    
    # Find SDL2 - use the same architecture directory
    sdl2_dir = install_dir
    if not sdl2_dir.exists():
        print(f"Error: SDL2 not found at {sdl2_dir}")
        print("Please build SDL2 first using build_sdl2.py")
        sys.exit(1)
    
    # Check if mpg123 was built (won't be on Windows)
    has_mpg123 = (install_dir / "lib" / "libmpg123.a").exists() or \
                 (install_dir / "lib" / "mpg123.lib").exists()
    
    # Build with CMake
    build_path = sdl_mixer_src / "build"
    build_path.mkdir(exist_ok=True)
    
    cmake_args = [
        "cmake", "..",
        f"-DCMAKE_INSTALL_PREFIX={install_dir}",
        f"-DCMAKE_PREFIX_PATH={install_dir};{sdl2_dir.resolve()}",
        f"-DSDL2_DIR={sdl2_dir.resolve()}/lib/cmake/SDL2",
        "-DSDL2MIXER_SAMPLES=OFF",
        "-DSDL2MIXER_INSTALL_TEST=OFF",
        "-DBUILD_SHARED_LIBS=ON",
        "-DSDL2MIXER_DEPS_SHARED=OFF",
        "-DSDL2MIXER_VENDORED=OFF",
        # Audio format support
        "-DSDL2MIXER_WAV=ON",
        "-DSDL2MIXER_OGG=ON",
        "-DSDL2MIXER_OGG_SHARED=OFF",
        "-DSDL2MIXER_FLAC=ON",
        "-DSDL2MIXER_FLAC_LIBFLAC=ON",
        "-DSDL2MIXER_FLAC_LIBFLAC_SHARED=OFF",
        "-DSDL2MIXER_MOD=OFF",  # Disable MOD support (no modplug/xmp)
        "-DSDL2MIXER_MIDI=OFF",  # Disable MIDI for now
        "-DSDL2MIXER_OPUS=OFF",  # Disable Opus for now
        "-DSDL2MIXER_WAVPACK=OFF",  # Disable WavPack support
        f"-DOGG_LIBRARY={install_dir}/lib/libogg.a",
        f"-DOGG_INCLUDE_DIR={install_dir}/include",
        f"-DVORBIS_LIBRARY={install_dir}/lib/libvorbis.a",
        f"-DVORBISFILE_LIBRARY={install_dir}/lib/libvorbisfile.a",
        f"-DVORBIS_INCLUDE_DIR={install_dir}/include",
        f"-DFLAC_LIBRARY={install_dir}/lib/libFLAC.a",
        f"-DFLAC_INCLUDE_DIR={install_dir}/include",
        "-DCMAKE_BUILD_TYPE=Release"
    ]
    
    # Only enable MP3 support if mpg123 was successfully built
    if has_mpg123:
        cmake_args.extend([
            "-DSDL2MIXER_MP3=ON",
            "-DSDL2MIXER_MP3_MPG123=ON",
            "-DSDL2MIXER_MP3_MPG123_SHARED=OFF",
            f"-DMPG123_LIBRARY={install_dir}/lib/libmpg123.a",
            f"-DMPG123_INCLUDE_DIR={install_dir}/include",
        ])
    else:
        cmake_args.append("-DSDL2MIXER_MP3=OFF")
        print("Note: MP3 support disabled (mpg123 not available)")
    
    if platform_name == "windows":
        cmake_args.extend([
            "-G", "Visual Studio 17 2022",
            "-A", "x64",
            # Define FLAC__NO_DLL to use static linking
            "-DCMAKE_C_FLAGS=/DFLAC__NO_DLL",
            "-DCMAKE_CXX_FLAGS=/DFLAC__NO_DLL"
        ])
        # Windows static lib names are different - update library paths
        for i, arg in enumerate(cmake_args):
            if arg.startswith("-DOGG_LIBRARY="):
                cmake_args[i] = f"-DOGG_LIBRARY={install_dir.resolve()}/lib/ogg.lib"
            elif arg.startswith("-DVORBIS_LIBRARY="):
                cmake_args[i] = f"-DVORBIS_LIBRARY={install_dir.resolve()}/lib/vorbis.lib"
            elif arg.startswith("-DVORBISFILE_LIBRARY="):
                cmake_args[i] = f"-DVORBISFILE_LIBRARY={install_dir.resolve()}/lib/vorbisfile.lib"
            elif arg.startswith("-DFLAC_LIBRARY="):
                # FLAC needs ogg library as well on Windows
                cmake_args[i] = f"-DFLAC_LIBRARY={install_dir.resolve()}/lib/FLAC.lib;{install_dir.resolve()}/lib/ogg.lib"
            elif arg.startswith("-DMPG123_LIBRARY=") and has_mpg123:
                cmake_args[i] = f"-DMPG123_LIBRARY={install_dir.resolve()}/lib/mpg123.lib"
    elif platform_name == "macos":
        cmake_args.extend([
            "-DCMAKE_OSX_ARCHITECTURES=arm64",
            "-DCMAKE_OSX_DEPLOYMENT_TARGET=11.0"
        ])
    
    env = os.environ.copy()
    env["PKG_CONFIG_PATH"] = f"{install_dir.resolve()}/lib/pkgconfig:{sdl2_dir.resolve()}/lib/pkgconfig"

    # Platform-specific environment variables
    if platform_name == "windows":
        # Define FLAC__NO_DLL to use static linking on Windows
        env["CFLAGS"] = "/DFLAC__NO_DLL"
        env["CXXFLAGS"] = "/DFLAC__NO_DLL"
    else:
        env["CFLAGS"] = f"-I{install_dir.resolve()}/include -I{sdl2_dir.resolve()}/include"
        env["LDFLAGS"] = f"-L{install_dir.resolve()}/lib -L{sdl2_dir.resolve()}/lib"
    
    run_command(cmake_args, cwd=build_path, env=env)
    run_command(["cmake", "--build", ".", "--config", "Release"], cwd=build_path)
    run_command(["cmake", "--install", "."], cwd=build_path)

def main():
    platform_name = get_platform()
    print(f"Building SDL_mixer for {platform_name}")

    # All platforms use arm64 directory structure in this project
    # (even though Ubuntu and Windows build x86_64 binaries)
    arch = "arm64"

    # Setup directories with absolute paths
    build_dir = Path.cwd() / "build" / "sdl_mixer"
    install_dir = Path.cwd() / "prebuilt" / platform_name / arch
    
    build_dir.mkdir(parents=True, exist_ok=True)
    install_dir.mkdir(parents=True, exist_ok=True)
    
    # Ensure lib and include dirs exist before building dependencies
    (install_dir / "lib").mkdir(parents=True, exist_ok=True)
    (install_dir / "include").mkdir(parents=True, exist_ok=True)
    
    # Build dependencies directly into main install dir so SDL_mixer can find them
    build_libogg(build_dir, install_dir, platform_name)
    build_libvorbis(build_dir, install_dir, platform_name)
    build_flac(build_dir, install_dir, platform_name)
    build_mpg123(build_dir, install_dir, platform_name)
    
    # Build SDL_mixer
    build_sdl_mixer(build_dir, install_dir, platform_name)
    
    print(f"\nSDL_mixer built successfully!")
    print(f"Libraries installed to: {install_dir}")
    
    # List what was built
    lib_dir = install_dir / "lib"
    if lib_dir.exists():
        print("\nInstalled libraries:")
        for lib in lib_dir.glob("*SDL*mixer*"):
            print(f"  - {lib.name}")
        print("\nSupported formats:")
        print("  - WAV (built-in)")
        print("  - OGG/Vorbis")
        print("  - FLAC")
        if (install_dir / "lib" / "libmpg123.a").exists() or \
           (install_dir / "lib" / "mpg123.lib").exists():
            print("  - MP3 (via mpg123)")
        else:
            print("  - MP3 (not available on this platform)")

if __name__ == "__main__":
    main()