#!/usr/bin/env python3
"""
Build script for SoLoud
Builds SoLoud audio engine with various backends
"""

import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path

# Version configuration
SOLOUD_VERSION = "RELEASE_20200207"
# SoLoud is now vendored in the repository

def get_platform():
    """Detect the current platform"""
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    elif system == "windows":
        return "windows"
    return "linux"

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

def create_cmake_lists(soloud_src, platform_name):
    """Create a CMakeLists.txt for building SoLoud as a shared library"""
    cmake_content = """cmake_minimum_required(VERSION 3.10)
project(soloud VERSION 1.0.0 LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# SoLoud core sources
set(SOLOUD_CORE_SOURCES
    src/core/soloud.cpp
    src/core/soloud_audiosource.cpp
    src/core/soloud_bus.cpp
    src/core/soloud_core_3d.cpp
    src/core/soloud_core_basicops.cpp
    src/core/soloud_core_faderops.cpp
    src/core/soloud_core_filterops.cpp
    src/core/soloud_core_getters.cpp
    src/core/soloud_core_setters.cpp
    src/core/soloud_core_voicegroup.cpp
    src/core/soloud_core_voiceops.cpp
    src/core/soloud_fader.cpp
    src/core/soloud_fft.cpp
    src/core/soloud_fft_lut.cpp
    src/core/soloud_file.cpp
    src/core/soloud_filter.cpp
    src/core/soloud_misc.cpp
    src/core/soloud_queue.cpp
    src/core/soloud_thread.cpp
)

# Audio source modules
set(SOLOUD_SOURCES
    src/audiosource/wav/dr_impl.cpp
    src/audiosource/wav/soloud_wav.cpp
    src/audiosource/wav/soloud_wavstream.cpp
    src/audiosource/wav/stb_vorbis.c
)

# Filter modules
set(SOLOUD_FILTERS
    src/filter/soloud_bassboostfilter.cpp
    src/filter/soloud_biquadresonantfilter.cpp
    src/filter/soloud_dcremovalfilter.cpp
    src/filter/soloud_echofilter.cpp
    src/filter/soloud_eqfilter.cpp
    src/filter/soloud_fftfilter.cpp
    src/filter/soloud_flangerfilter.cpp
    src/filter/soloud_freeverbfilter.cpp
    src/filter/soloud_lofifilter.cpp
    src/filter/soloud_robotizefilter.cpp
    src/filter/soloud_waveshaperfilter.cpp
)

# Platform-specific backend
"""

    if platform_name == "linux":
        cmake_content += """
set(SOLOUD_BACKEND
    src/backend/alsa/soloud_alsa.cpp
)
set(BACKEND_LIBS asound pthread)
add_definitions(-DWITH_ALSA)
"""
    elif platform_name == "windows":
        cmake_content += """
set(SOLOUD_BACKEND
    src/backend/winmm/soloud_winmm.cpp
)
set(BACKEND_LIBS winmm)
add_definitions(-DWITH_WINMM)
"""
    elif platform_name == "macos":
        cmake_content += """
set(SOLOUD_BACKEND
    src/backend/coreaudio/soloud_coreaudio.cpp
)
find_library(COREAUDIO_LIBRARY CoreAudio REQUIRED)
find_library(AUDIOUNIT_LIBRARY AudioUnit REQUIRED)
set(BACKEND_LIBS ${COREAUDIO_LIBRARY} ${AUDIOUNIT_LIBRARY})
add_definitions(-DWITH_COREAUDIO)
"""

    cmake_content += """
# Create shared library
add_library(soloud SHARED
    ${SOLOUD_CORE_SOURCES}
    ${SOLOUD_SOURCES}
    ${SOLOUD_FILTERS}
    ${SOLOUD_BACKEND}
)

target_include_directories(soloud PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

target_link_libraries(soloud PRIVATE ${BACKEND_LIBS})

# Set version
set_target_properties(soloud PROPERTIES
    VERSION 1.0.0
    SOVERSION 1
)

# Installation
install(TARGETS soloud
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
    RUNTIME DESTINATION bin
)

install(DIRECTORY include/
    DESTINATION include
    FILES_MATCHING PATTERN "*.h"
)
"""

    cmake_path = soloud_src / "CMakeLists.txt"
    with open(cmake_path, 'w') as f:
        f.write(cmake_content)
    print(f"Created CMakeLists.txt at {cmake_path}")

def build_soloud(build_dir, install_dir, platform_name):
    """Build SoLoud"""
    print("\n=== Building SoLoud ===")

    # Use vendored source
    vendored_src = Path(f"soloud-{SOLOUD_VERSION}")
    soloud_src = build_dir / f"soloud-{SOLOUD_VERSION}"

    if not vendored_src.exists():
        print(f"Error: Vendored SoLoud source not found at {vendored_src}")
        print(f"Please ensure soloud-{SOLOUD_VERSION} directory exists in the project root")
        sys.exit(1)

    # Copy vendored source to build directory
    if soloud_src.exists():
        shutil.rmtree(soloud_src)
    print(f"Copying vendored source from {vendored_src} to {soloud_src}")
    shutil.copytree(vendored_src, soloud_src)

    # Create CMakeLists.txt for building
    create_cmake_lists(soloud_src, platform_name)

    # Build with CMake
    build_path = soloud_src / "build"
    build_path.mkdir(exist_ok=True)

    cmake_args = [
        "cmake", "..",
        f"-DCMAKE_INSTALL_PREFIX={install_dir}",
        "-DCMAKE_BUILD_TYPE=Release",
    ]

    if platform_name == "windows":
        cmake_args.extend(["-G", "Visual Studio 17 2022", "-A", "x64"])
    elif platform_name == "macos":
        cmake_args.extend([
            "-DCMAKE_OSX_ARCHITECTURES=arm64",
            "-DCMAKE_OSX_DEPLOYMENT_TARGET=11.0"
        ])

    run_command(cmake_args, cwd=build_path)
    run_command(["cmake", "--build", ".", "--config", "Release", "--parallel"], cwd=build_path)
    run_command(["cmake", "--install", "."], cwd=build_path)

def main():
    platform_name = get_platform()
    print(f"Building SoLoud for {platform_name}")

    # Determine architecture based on platform
    if platform_name == "macos":
        arch = "arm64"  # Apple Silicon
    else:
        arch = "x86_64"  # Linux and Windows use x86_64

    # Setup directories with absolute paths
    build_dir = Path.cwd() / "build" / "soloud"
    install_dir = Path.cwd() / "prebuilt" / platform_name / arch

    build_dir.mkdir(parents=True, exist_ok=True)
    install_dir.mkdir(parents=True, exist_ok=True)

    # Ensure lib and include dirs exist
    (install_dir / "lib").mkdir(parents=True, exist_ok=True)
    (install_dir / "include").mkdir(parents=True, exist_ok=True)
    if platform_name == "windows":
        (install_dir / "bin").mkdir(parents=True, exist_ok=True)

    # Build SoLoud
    build_soloud(build_dir, install_dir, platform_name)

    print(f"\nSoLoud built successfully!")
    print(f"Libraries installed to: {install_dir}")

    # List what was built
    lib_dir = install_dir / "lib"
    if lib_dir.exists():
        print("\nInstalled libraries:")
        for lib in lib_dir.glob("*soloud*"):
            print(f"  - {lib.name}")

    bin_dir = install_dir / "bin"
    if bin_dir.exists() and platform_name == "windows":
        print("\nInstalled DLLs:")
        for dll in bin_dir.glob("*soloud*"):
            print(f"  - {dll.name}")

    print("\nSoLoud Features:")
    print("  - Portable audio engine")
    if platform_name == "linux":
        print("  - ALSA backend")
    elif platform_name == "windows":
        print("  - WinMM backend")
    elif platform_name == "macos":
        print("  - CoreAudio backend")
    print("  - WAV, OGG support via stb_vorbis")
    print("  - Built-in audio filters (reverb, echo, etc.)")
    print("  - 3D audio positioning")

if __name__ == "__main__":
    main()
