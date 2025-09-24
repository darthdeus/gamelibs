#!/usr/bin/env python3
"""
CMake-based build script for cimgui with SDL2 and OpenGL3 backends
Works consistently across all platforms
"""

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path

# Detect platform
SYSTEM = platform.system()
IS_WINDOWS = SYSTEM == "Windows"
IS_MACOS = SYSTEM == "Darwin"
IS_LINUX = SYSTEM == "Linux"

def run_cmd(cmd, cwd=None):
    """Run a command and return success status"""
    print(f"Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    if IS_WINDOWS and not isinstance(cmd, list):
        result = subprocess.run(cmd, cwd=cwd, shell=True)
    else:
        result = subprocess.run(cmd, cwd=cwd, shell=False)
    return result.returncode == 0

def write_cmakelists(build_dir, sdl_prefix):
    """Generate CMakeLists.txt for cimgui"""
    cmakelists = f"""cmake_minimum_required(VERSION 3.10)
project(cimgui)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 11)

# Find SDL2
set(SDL2_DIR "{sdl_prefix}/lib/cmake/SDL2" "{sdl_prefix}")
find_package(SDL2 REQUIRED)

# Find OpenGL
find_package(OpenGL REQUIRED)

# Source files
set(IMGUI_DIR "${{CMAKE_CURRENT_SOURCE_DIR}}/../../cimgui/imgui")
set(CIMGUI_DIR "${{CMAKE_CURRENT_SOURCE_DIR}}/../../cimgui")
set(BACKENDS_DIR "${{CMAKE_CURRENT_SOURCE_DIR}}/../../imgui_backends")

set(SOURCES
    ${{CIMGUI_DIR}}/cimgui.cpp
    ${{IMGUI_DIR}}/imgui.cpp
    ${{IMGUI_DIR}}/imgui_draw.cpp
    ${{IMGUI_DIR}}/imgui_tables.cpp
    ${{IMGUI_DIR}}/imgui_widgets.cpp
    ${{IMGUI_DIR}}/imgui_demo.cpp
    ${{IMGUI_DIR}}/backends/imgui_impl_sdl2.cpp
    ${{IMGUI_DIR}}/backends/imgui_impl_opengl3.cpp
)

# Add wrapper if exists
if(EXISTS "${{BACKENDS_DIR}}/cimgui_sdl2_opengl3.cpp")
    list(APPEND SOURCES "${{BACKENDS_DIR}}/cimgui_sdl2_opengl3.cpp")
endif()

# Create shared library
add_library(cimgui SHARED ${{SOURCES}})

# Include directories
target_include_directories(cimgui PUBLIC
    ${{CIMGUI_DIR}}
    ${{IMGUI_DIR}}
    ${{IMGUI_DIR}}/backends
    ${{BACKENDS_DIR}}
    ${{SDL2_INCLUDE_DIRS}}
)

# Compile definitions
target_compile_definitions(cimgui PRIVATE
    IMGUI_IMPL_API=extern\\ \"C\"
    CIMGUI_IMPL_API=extern\\ \"C\"
)

if(WIN32)
    target_compile_definitions(cimgui PRIVATE
        _WINDOWS
        IMGUI_API=__declspec(dllexport)
    )
endif()

# Link libraries
if(WIN32)
    target_link_libraries(cimgui
        ${{SDL2_LIBRARIES}}
        ${{OPENGL_LIBRARIES}}
        imm32
    )
else()
    target_link_libraries(cimgui
        ${{SDL2_LIBRARIES}}
        ${{OPENGL_LIBRARIES}}
        m
        dl
    )
endif()

# Set output name
set_target_properties(cimgui PROPERTIES
    OUTPUT_NAME "cimgui"
    PREFIX "${{CMAKE_SHARED_LIBRARY_PREFIX}}"
)

# Install rules
install(TARGETS cimgui
    RUNTIME DESTINATION bin
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
)

install(FILES
    ${{CIMGUI_DIR}}/cimgui.h
    DESTINATION include/cimgui
)

if(EXISTS "${{BACKENDS_DIR}}/cimgui_sdl2_opengl3.h")
    install(FILES "${{BACKENDS_DIR}}/cimgui_sdl2_opengl3.h"
        DESTINATION include/cimgui)
endif()

if(EXISTS "${{BACKENDS_DIR}}/cimgui_essential.h")
    install(FILES "${{BACKENDS_DIR}}/cimgui_essential.h"
        DESTINATION include/cimgui)
endif()
"""
    
    cmake_file = build_dir / "CMakeLists.txt"
    cmake_file.write_text(cmakelists)
    print(f"Generated {cmake_file}")

def build_cimgui(sdl_prefix, install_prefix):
    """Build cimgui library with SDL2 and OpenGL3 backends using CMake"""
    
    print(f"\n==> Building cimgui for {SYSTEM} using CMake")
    print(f"    SDL2 prefix: {sdl_prefix}")
    print(f"    Install prefix: {install_prefix}")
    
    # Ensure cimgui directory exists
    cimgui_dir = Path("cimgui")
    if not cimgui_dir.exists():
        print("ERROR: cimgui directory not found")
        return False
    
    # Ensure imgui submodule is present
    imgui_dir = cimgui_dir / "imgui"
    if not imgui_dir.exists():
        print("Initializing imgui submodule...")
        if not run_cmd(["git", "submodule", "update", "--init"], cwd="cimgui"):
            print("ERROR: Failed to initialize imgui submodule")
            return False
    
    # Build directory
    build_dir = Path("build/cimgui")
    build_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate CMakeLists.txt
    write_cmakelists(build_dir, sdl_prefix)
    
    # Configure with CMake
    cmake_cmd = [
        "cmake",
        ".",
        f"-DCMAKE_INSTALL_PREFIX={install_prefix}",
        f"-DCMAKE_PREFIX_PATH={sdl_prefix}",
        "-DCMAKE_BUILD_TYPE=Release"
    ]
    
    if IS_WINDOWS:
        cmake_cmd.extend(["-G", "Visual Studio 17 2022", "-A", "x64"])
    else:
        # Use Ninja if available, otherwise default
        if shutil.which("ninja"):
            cmake_cmd.extend(["-G", "Ninja"])
    
    if not run_cmd(cmake_cmd, cwd=build_dir):
        print("ERROR: CMake configuration failed")
        return False
    
    # Build
    build_cmd = ["cmake", "--build", ".", "--config", "Release"]
    if not IS_WINDOWS:
        build_cmd.extend(["--parallel", str(os.cpu_count())])
    
    if not run_cmd(build_cmd, cwd=build_dir):
        print("ERROR: Build failed")
        return False
    
    # Install
    install_cmd = ["cmake", "--install", ".", "--config", "Release"]
    if not run_cmd(install_cmd, cwd=build_dir):
        print("ERROR: Installation failed")
        return False
    
    print(f"\n✓ cimgui built successfully!")
    return True

def main():
    if len(sys.argv) != 3:
        print("Usage: build_cimgui_cmake.py <SDL2_PREFIX> <INSTALL_PREFIX>")
        print("  SDL2_PREFIX: Path where SDL2 is installed")
        print("  INSTALL_PREFIX: Path where cimgui should be installed")
        return 1
    
    sdl_prefix = Path(sys.argv[1]).resolve()
    install_prefix = Path(sys.argv[2]).resolve()
    
    if not sdl_prefix.exists():
        print(f"ERROR: SDL2 prefix does not exist: {sdl_prefix}")
        return 1
    
    if build_cimgui(sdl_prefix, install_prefix):
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())