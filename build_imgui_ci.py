#!/usr/bin/env python3
"""
CI-friendly build script for ImGui/cimgui
Builds cimgui with SDL2 and OpenGL3 backends
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
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode == 0

def build_cimgui(sdl_prefix, install_prefix):
    """Build cimgui library with SDL2 and OpenGL3 backends"""
    
    print(f"\n==> Building cimgui for {SYSTEM}")
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
    
    # Platform-specific settings
    if IS_WINDOWS:
        lib_name = "cimgui.dll"
        # Use cmake to handle MSVC properly
        use_cmake = True
    elif IS_MACOS:
        lib_name = "libcimgui.dylib"
        cc = "clang"
        cxx = "clang++"
        extra_cflags = ["-stdlib=libc++"]
        extra_ldflags = ["-lSDL2", "-framework", "OpenGL", "-framework", "CoreFoundation"]
    else:  # Linux
        lib_name = "libcimgui.so"
        cc = "gcc"
        cxx = "g++"
        extra_cflags = []
        extra_ldflags = ["-lSDL2", "-lGL", "-ldl", "-lm"]
    
    # Build directory
    build_dir = Path("build/cimgui")
    build_dir.mkdir(parents=True, exist_ok=True)
    
    # Source files
    sources = [
        str(cimgui_dir / "cimgui.cpp"),
        str(imgui_dir / "imgui.cpp"),
        str(imgui_dir / "imgui_draw.cpp"),
        str(imgui_dir / "imgui_tables.cpp"),
        str(imgui_dir / "imgui_widgets.cpp"),
        str(imgui_dir / "imgui_demo.cpp"),
        str(imgui_dir / "backends" / "imgui_impl_sdl2.cpp"),
        str(imgui_dir / "backends" / "imgui_impl_opengl3.cpp"),
    ]
    
    # Add wrapper if it exists
    wrapper_cpp = Path("imgui_backends/cimgui_sdl2_opengl3.cpp")
    if wrapper_cpp.exists():
        sources.append(str(wrapper_cpp))
        print("Including SDL2/OpenGL3 wrapper")
    
    # Include directories
    includes = [
        f"-I{cimgui_dir}",
        f"-I{imgui_dir}",
        f"-I{imgui_dir}/backends",
        f"-I{sdl_prefix}/include",
        f"-I{sdl_prefix}/include/SDL2",
    ]
    
    # Library directories
    lib_dirs = [
        f"-L{sdl_prefix}/lib",
    ]
    
    # Compile flags
    if IS_WINDOWS:
        compile_flags = ["/O2", "/MD", "/D_WINDOWS", "/DNDEBUG"]
    else:
        compile_flags = ["-O2", "-fPIC", "-shared", "-D_REENTRANT"]
    
    # Build command
    if IS_WINDOWS:
        # Windows needs separate compile and link
        obj_files = []
        for src in sources:
            obj = str(build_dir / Path(src).stem) + ".obj"
            cmd = [cxx] + compile_flags + includes + ["/c", src, f"/Fo{obj}"]
            if not run_cmd(cmd):
                print(f"ERROR: Failed to compile {src}")
                return False
            obj_files.append(obj)
        
        # Link
        output = str(build_dir / lib_name)
        cmd = [cxx] + obj_files + [f"/Fe{output}", "/LD"] + lib_dirs + extra_ldflags
        if not run_cmd(cmd):
            print("ERROR: Failed to link library")
            return False
    else:
        # Unix-like systems can compile and link in one step
        output = str(build_dir / lib_name)
        cmd = [cxx] + compile_flags + includes + sources + lib_dirs + extra_ldflags + ["-o", output]
        
        if not run_cmd(cmd):
            print("ERROR: Failed to build library")
            return False
    
    # Install library
    lib_install_dir = Path(install_prefix) / "lib"
    lib_install_dir.mkdir(parents=True, exist_ok=True)
    
    shutil.copy(output, lib_install_dir / lib_name)
    print(f"Installed: {lib_install_dir / lib_name}")
    
    # Install headers
    include_install_dir = Path(install_prefix) / "include" / "cimgui"
    include_install_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy cimgui headers
    for header in ["cimgui.h"]:
        src = cimgui_dir / header
        if src.exists():
            shutil.copy(src, include_install_dir / header)
            print(f"Installed: {include_install_dir / header}")
    
    # Copy wrapper header if exists
    wrapper_h = Path("imgui_backends/cimgui_sdl2_opengl3.h")
    if wrapper_h.exists():
        shutil.copy(wrapper_h, include_install_dir / "cimgui_sdl2_opengl3.h")
        print(f"Installed: {include_install_dir / 'cimgui_sdl2_opengl3.h'}")
    
    # Copy essential header if exists
    essential_h = Path("imgui_backends/cimgui_essential.h")
    if essential_h.exists():
        shutil.copy(essential_h, include_install_dir / "cimgui_essential.h")
        print(f"Installed: {include_install_dir / 'cimgui_essential.h'}")
    
    print(f"\n✓ cimgui built successfully!")
    return True

def main():
    if len(sys.argv) != 3:
        print("Usage: build_imgui_ci.py <SDL2_PREFIX> <INSTALL_PREFIX>")
        print("  SDL2_PREFIX: Path where SDL2 is installed")
        print("  INSTALL_PREFIX: Path where cimgui should be installed")
        return 1
    
    sdl_prefix = sys.argv[1]
    install_prefix = sys.argv[2]
    
    if not Path(sdl_prefix).exists():
        print(f"ERROR: SDL2 prefix does not exist: {sdl_prefix}")
        return 1
    
    if build_cimgui(sdl_prefix, install_prefix):
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())