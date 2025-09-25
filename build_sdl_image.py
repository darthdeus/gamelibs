#!/usr/bin/env python3
"""
Build script for SDL_image
Builds SDL_image with PNG, JPG, and WebP support
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
SDL_IMAGE_VERSION = "2.8.2"
# SDL_image is now vendored in the repository

LIBPNG_VERSION = "1.6.44"
LIBPNG_URL = f"https://download.sourceforge.net/libpng/libpng-{LIBPNG_VERSION}.tar.gz"

LIBJPEG_VERSION = "3.0.4"
LIBJPEG_URL = f"https://github.com/libjpeg-turbo/libjpeg-turbo/releases/download/{LIBJPEG_VERSION}/libjpeg-turbo-{LIBJPEG_VERSION}.tar.gz"

LIBWEBP_VERSION = "1.3.2"
LIBWEBP_URL = f"https://github.com/webmproject/libwebp/archive/v{LIBWEBP_VERSION}.tar.gz"

ZLIB_VERSION = "1.3.1"
ZLIB_URL = f"https://github.com/madler/zlib/releases/download/v{ZLIB_VERSION}/zlib-{ZLIB_VERSION}.tar.gz"

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
    """Extract tar.gz or zip archive"""
    print(f"Extracting {archive_path}...")
    archive_str = str(archive_path)
    if archive_str.endswith('.tar.gz'):
        with tarfile.open(archive_path, 'r:gz') as tar:
            tar.extractall(dest_dir)
    elif archive_str.endswith('.zip'):
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(dest_dir)

def run_command(cmd, cwd=None, env=None):
    """Run a shell command and check for errors"""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(1)
    return result

def build_zlib(build_dir, install_dir, platform_name):
    """Build zlib (required for libpng)"""
    print("\n=== Building zlib ===")
    zlib_archive = build_dir / f"zlib-{ZLIB_VERSION}.tar.gz"
    zlib_src = build_dir / f"zlib-{ZLIB_VERSION}"
    
    if not zlib_archive.exists():
        download_file(ZLIB_URL, zlib_archive)
    
    if zlib_src.exists():
        shutil.rmtree(zlib_src)
    extract_archive(zlib_archive, build_dir)
    
    # Configure and build
    env = os.environ.copy()
    
    # Force arm64 architecture on macOS for Apple Silicon
    if platform_name == "macos":
        env["CFLAGS"] = "-arch arm64"
        env["LDFLAGS"] = "-arch arm64"
    
    if platform_name == "windows":
        # Windows build using CMake
        build_path = zlib_src / "build"
        build_path.mkdir(exist_ok=True)
        run_command([
            "cmake", "..",
            f"-DCMAKE_INSTALL_PREFIX={install_dir}",
            "-DCMAKE_BUILD_TYPE=Release"
        ], cwd=build_path)
        run_command(["cmake", "--build", ".", "--config", "Release"], cwd=build_path)
        run_command(["cmake", "--install", "."], cwd=build_path)
    else:
        # Unix-like build
        run_command([
            "./configure",
            f"--prefix={install_dir.resolve()}",
            "--static"
        ], cwd=zlib_src, env=env)
        run_command(["make", f"-j{os.cpu_count()}"], cwd=zlib_src)
        run_command(["make", "install"], cwd=zlib_src)

def build_libpng(build_dir, install_dir, platform_name):
    """Build libpng"""
    print("\n=== Building libpng ===")
    png_archive = build_dir / f"libpng-{LIBPNG_VERSION}.tar.gz"
    png_src = build_dir / f"libpng-{LIBPNG_VERSION}"
    
    if not png_archive.exists():
        download_file(LIBPNG_URL, png_archive)
    
    if png_src.exists():
        shutil.rmtree(png_src)
    extract_archive(png_archive, build_dir)
    
    # Patch pngpriv.h on macOS to remove fp.h dependency
    if platform_name == "macos":
        pngpriv_h = png_src / "pngpriv.h"
        if pngpriv_h.exists():
            content = pngpriv_h.read_text()
            # Comment out the fp.h include
            content = content.replace('#      include <fp.h>', '/* #      include <fp.h> */')
            pngpriv_h.write_text(content)
            print("Patched pngpriv.h to remove fp.h dependency")
    
    # Configure and build
    env = os.environ.copy()
    
    # CRITICAL: Put our include path FIRST to override system headers
    cflags = f"-I{install_dir.resolve()}/include"
    cppflags = f"-I{install_dir.resolve()}/include"
    ldflags = f"-L{install_dir.resolve()}/lib"
    
    # Fix macOS fp.h header issue and force arm64 architecture for Apple Silicon
    if platform_name == "macos":
        cflags += " -DPNG_ARM_NEON_OPT=0 -arch arm64"
        cppflags += " -DPNG_ARM_NEON_OPT=0 -arch arm64"
        ldflags += " -arch arm64"
    
    # Override any existing flags to ensure our paths come first
    env["CFLAGS"] = cflags
    env["CPPFLAGS"] = cppflags  
    env["LDFLAGS"] = ldflags
    env["PKG_CONFIG_PATH"] = f"{install_dir.resolve()}/lib/pkgconfig"
    
    # Force libpng to use our zlib
    env["ZLIB_CFLAGS"] = cppflags
    env["ZLIB_LIBS"] = f"{ldflags} -lz"
    
    # Clear any system paths that might interfere
    if "C_INCLUDE_PATH" in env:
        del env["C_INCLUDE_PATH"]
    if "CPLUS_INCLUDE_PATH" in env:
        del env["CPLUS_INCLUDE_PATH"]
    
    if platform_name == "windows":
        # Windows build using CMake
        build_path = png_src / "build"
        build_path.mkdir(exist_ok=True)
        run_command([
            "cmake", "..",
            f"-DCMAKE_INSTALL_PREFIX={install_dir}",
            f"-DZLIB_ROOT={install_dir}",
            "-DPNG_SHARED=OFF",
            "-DPNG_STATIC=ON",
            "-DCMAKE_BUILD_TYPE=Release"
        ], cwd=build_path)
        run_command(["cmake", "--build", ".", "--config", "Release"], cwd=build_path)
        run_command(["cmake", "--install", "."], cwd=build_path)
    else:
        # Unix-like build - force our zlib
        configure_args = [
            "./configure",
            f"--prefix={install_dir.resolve()}",
            "--enable-static",
            "--disable-shared",
            f"--with-zlib-prefix={install_dir.resolve()}",
            f"CPPFLAGS=-I{install_dir.resolve()}/include",
            f"LDFLAGS=-L{install_dir.resolve()}/lib"
        ]
        
        # Additional macOS-specific configure options to fix fp.h
        if platform_name == "macos":
            # Remove the generic CPPFLAGS first
            configure_args = [arg for arg in configure_args if not arg.startswith("CPPFLAGS=")]
            # Add macOS-specific flags with ARM NEON disabled
            configure_args.extend([
                "--disable-arm-neon",
                f"CPPFLAGS=-I{install_dir.resolve()}/include -DPNG_ARM_NEON_OPT=0 -DPNG_ARM_NEON_IMPLEMENTATION=0"
            ])
        
        run_command(configure_args, cwd=png_src, env=env)
        run_command(["make", f"-j{os.cpu_count()}"], cwd=png_src)
        run_command(["make", "install"], cwd=png_src)

def build_libjpeg(build_dir, install_dir, platform_name):
    """Build libjpeg-turbo"""
    print("\n=== Building libjpeg-turbo ===")
    jpeg_archive = build_dir / f"libjpeg-turbo-{LIBJPEG_VERSION}.tar.gz"
    jpeg_src = build_dir / f"libjpeg-turbo-{LIBJPEG_VERSION}"
    
    if not jpeg_archive.exists():
        download_file(LIBJPEG_URL, jpeg_archive)
    
    if jpeg_src.exists():
        shutil.rmtree(jpeg_src)
    extract_archive(jpeg_archive, build_dir)
    
    # Build with CMake
    build_path = jpeg_src / "build"
    build_path.mkdir(exist_ok=True)
    
    cmake_args = [
        "cmake", "..",
        f"-DCMAKE_INSTALL_PREFIX={install_dir.resolve()}",
        "-DENABLE_SHARED=OFF",
        "-DENABLE_STATIC=ON",
        "-DCMAKE_BUILD_TYPE=Release",
        "-DCMAKE_POLICY_VERSION_MINIMUM=3.5"  # Allow older CMakeLists.txt
    ]
    
    if platform_name == "windows":
        cmake_args.extend(["-G", "Visual Studio 17 2022", "-A", "x64"])
    elif platform_name == "macos":
        cmake_args.append("-DCMAKE_OSX_ARCHITECTURES=arm64")
    
    run_command(cmake_args, cwd=build_path)
    run_command(["cmake", "--build", ".", "--config", "Release"], cwd=build_path)
    run_command(["cmake", "--install", "."], cwd=build_path)

def build_libwebp(build_dir, install_dir, platform_name):
    """Build libwebp"""
    print("\n=== Building libwebp ===")
    webp_archive = build_dir / f"libwebp-{LIBWEBP_VERSION}.tar.gz"
    webp_src = build_dir / f"libwebp-{LIBWEBP_VERSION}"
    
    if not webp_archive.exists():
        download_file(LIBWEBP_URL, webp_archive)
    
    if webp_src.exists():
        shutil.rmtree(webp_src)
    extract_archive(webp_archive, build_dir)
    
    # Build with CMake
    build_path = webp_src / "build"
    build_path.mkdir(exist_ok=True)
    
    cmake_args = [
        "cmake", "..",
        f"-DCMAKE_INSTALL_PREFIX={install_dir.resolve()}",
        "-DBUILD_SHARED_LIBS=OFF",
        "-DWEBP_BUILD_ANIM_UTILS=OFF",
        "-DWEBP_BUILD_CWEBP=OFF",
        "-DWEBP_BUILD_DWEBP=OFF",
        "-DWEBP_BUILD_GIF2WEBP=OFF",
        "-DWEBP_BUILD_IMG2WEBP=OFF",
        "-DWEBP_BUILD_VWEBP=OFF",
        "-DWEBP_BUILD_WEBPINFO=OFF",
        "-DWEBP_BUILD_WEBPMUX=OFF",
        "-DWEBP_BUILD_EXTRAS=OFF",
        "-DCMAKE_BUILD_TYPE=Release",
        "-DCMAKE_POLICY_VERSION_MINIMUM=3.5"  # Allow older CMakeLists.txt
    ]
    
    if platform_name == "windows":
        cmake_args.extend(["-G", "Visual Studio 17 2022", "-A", "x64"])
    elif platform_name == "macos":
        cmake_args.append("-DCMAKE_OSX_ARCHITECTURES=arm64")
    
    run_command(cmake_args, cwd=build_path)
    run_command(["cmake", "--build", ".", "--config", "Release"], cwd=build_path)
    run_command(["cmake", "--install", "."], cwd=build_path)

def build_sdl_image(build_dir, install_dir, platform_name):
    """Build SDL_image with all dependencies"""
    print("\n=== Building SDL_image ===")
    # Use vendored source instead of downloading
    vendored_src = Path(f"SDL2_image-{SDL_IMAGE_VERSION}")
    sdl_image_src = build_dir / f"SDL2_image-{SDL_IMAGE_VERSION}"
    
    if not vendored_src.exists():
        print(f"Error: Vendored SDL_image source not found at {vendored_src}")
        print("Please ensure SDL2_image-2.8.2 directory exists in the project root")
        sys.exit(1)
    
    if sdl_image_src.exists():
        shutil.rmtree(sdl_image_src)
    
    # Copy vendored source to build directory
    print(f"Copying vendored source from {vendored_src} to {sdl_image_src}")
    shutil.copytree(vendored_src, sdl_image_src)
    
    # Find SDL2 - use the same architecture directory
    sdl2_dir = install_dir
    if not sdl2_dir.exists():
        print(f"Error: SDL2 not found at {sdl2_dir}")
        print("Please build SDL2 first using build_sdl2.py")
        sys.exit(1)
    
    # Build with CMake
    build_path = sdl_image_src / "build"
    build_path.mkdir(exist_ok=True)
    
    cmake_args = [
        "cmake", "..",
        f"-DCMAKE_INSTALL_PREFIX={install_dir.resolve()}",
        f"-DCMAKE_PREFIX_PATH={install_dir.resolve()};{sdl2_dir.resolve()}",
        f"-DSDL2_DIR={sdl2_dir.resolve()}/lib/cmake/SDL2",
        "-DSDL2IMAGE_SAMPLES=OFF",
        "-DBUILD_SHARED_LIBS=ON",
        "-DSDL2IMAGE_DEPS_SHARED=OFF",
        "-DSDL2IMAGE_VENDORED=OFF",
        "-DSDL2IMAGE_PNG=ON",
        "-DSDL2IMAGE_PNG_SHARED=OFF",
        "-DSDL2IMAGE_JPG=ON",
        "-DSDL2IMAGE_JPG_SHARED=OFF",
        "-DSDL2IMAGE_WEBP=ON",
        "-DSDL2IMAGE_WEBP_SHARED=OFF",
        "-DSDL2IMAGE_TIF=OFF",
        "-DSDL2IMAGE_AVIF=OFF",
        "-DSDL2IMAGE_JXL=OFF",
        f"-DZLIB_LIBRARY={install_dir.resolve()}/lib/libz.a",
        f"-DZLIB_INCLUDE_DIR={install_dir.resolve()}/include",
        f"-DPNG_LIBRARY={install_dir.resolve()}/lib/libpng.a",
        f"-DPNG_PNG_INCLUDE_DIR={install_dir.resolve()}/include",
        f"-DJPEG_LIBRARY={install_dir.resolve()}/lib/libjpeg.a",
        f"-DJPEG_INCLUDE_DIR={install_dir.resolve()}/include",
        f"-DWEBP_LIBRARY={install_dir.resolve()}/lib/libwebp.a",
        f"-DWEBP_INCLUDE_DIR={install_dir.resolve()}/include",
        "-DCMAKE_BUILD_TYPE=Release"
    ]
    
    if platform_name == "windows":
        cmake_args.extend(["-G", "Visual Studio 17 2022", "-A", "x64"])
        # Windows static lib names are different
        # Update the library paths for Windows
        for i, arg in enumerate(cmake_args):
            if arg.startswith("-DZLIB_LIBRARY="):
                cmake_args[i] = f"-DZLIB_LIBRARY={install_dir.resolve()}/lib/zlibstatic.lib"
            elif arg.startswith("-DPNG_LIBRARY="):
                cmake_args[i] = f"-DPNG_LIBRARY={install_dir.resolve()}/lib/libpng16_static.lib"
            elif arg.startswith("-DJPEG_LIBRARY="):
                cmake_args[i] = f"-DJPEG_LIBRARY={install_dir.resolve()}/lib/jpeg-static.lib"
            elif arg.startswith("-DWEBP_LIBRARY="):
                cmake_args[i] = f"-DWEBP_LIBRARY={install_dir.resolve()}/lib/webp.lib"
    elif platform_name == "macos":
        cmake_args.extend([
            "-DCMAKE_OSX_ARCHITECTURES=arm64",
            "-DCMAKE_OSX_DEPLOYMENT_TARGET=11.0"
        ])
    
    env = os.environ.copy()
    env["CFLAGS"] = f"-I{install_dir.resolve()}/include -I{sdl2_dir.resolve()}/include"
    env["LDFLAGS"] = f"-L{install_dir.resolve()}/lib -L{sdl2_dir.resolve()}/lib"
    
    run_command(cmake_args, cwd=build_path, env=env)
    run_command(["cmake", "--build", ".", "--config", "Release"], cwd=build_path)
    run_command(["cmake", "--install", "."], cwd=build_path)

def main():
    platform_name = get_platform()
    print(f"Building SDL_image for {platform_name}")

    # Determine architecture
    # Only macOS uses arm64 (for Apple Silicon), everything else uses x86_64
    if platform_name == "macos":
        arch = "arm64"
    else:
        arch = "x86_64"

    # Setup directories with absolute paths
    build_dir = Path.cwd() / "build" / "sdl_image"
    install_dir = Path.cwd() / "prebuilt" / platform_name / arch
    
    build_dir.mkdir(parents=True, exist_ok=True)
    install_dir.mkdir(parents=True, exist_ok=True)
    
    # Ensure lib and include dirs exist before building dependencies
    (install_dir / "lib").mkdir(parents=True, exist_ok=True)
    (install_dir / "include").mkdir(parents=True, exist_ok=True)
    
    # Build dependencies directly into main install dir so SDL_image can find them
    build_zlib(build_dir, install_dir, platform_name)
    build_libpng(build_dir, install_dir, platform_name)
    build_libjpeg(build_dir, install_dir, platform_name)
    build_libwebp(build_dir, install_dir, platform_name)
    
    # Build SDL_image
    build_sdl_image(build_dir, install_dir, platform_name)
    
    print(f"\nSDL_image built successfully!")
    print(f"Libraries installed to: {install_dir}")
    
    # List what was built
    lib_dir = install_dir / "lib"
    if lib_dir.exists():
        print("\nInstalled libraries:")
        for lib in lib_dir.glob("*SDL*_image*"):
            print(f"  - {lib.name}")

if __name__ == "__main__":
    main()