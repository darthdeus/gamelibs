#!/usr/bin/env python3
"""
Universal build script for cimgui with SDL2 and OpenGL3 backends
Usage: 
  ./build_imgui.py                                    # Use default paths
  ./build_imgui.py <SDL2_PREFIX> <INSTALL_PREFIX>     # Specify paths
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

# Parse command line arguments
if len(sys.argv) == 3:
    SDL2_PREFIX = Path(sys.argv[1]).resolve()
    INSTALL_PREFIX = Path(sys.argv[2]).resolve()
    CI_MODE = True
else:
    # Default paths for local development
    SDL2_PREFIX = None
    INSTALL_PREFIX = Path.cwd() / "libs"
    CI_MODE = False

# Platform-specific settings
if IS_WINDOWS:
    LIB_EXT = ".dll"
    LIB_PREFIX = ""
    # On Windows CI, we need to use the full path or setup the environment
    CC = "cl.exe"
    CXX = "cl.exe"
    EXTRA_CFLAGS = ["/nologo", "/MD"]
    if CI_MODE and SDL2_PREFIX:
        # Windows might have SDL2 headers directly in include/
        SDL_INCLUDE_DIRS = [f"{SDL2_PREFIX}/include", f"{SDL2_PREFIX}/include/SDL2"]
        SDL_LIB_DIR = f"{SDL2_PREFIX}/lib"
        EXTRA_LDFLAGS = [f"/LIBPATH:{SDL_LIB_DIR}", "SDL2.lib", "SDL2main.lib", "opengl32.lib"]
    else:
        EXTRA_LDFLAGS = ["-lSDL2", "-lopengl32"]
        SDL_INCLUDE_DIRS = ["C:/SDL2/include"]
elif IS_MACOS:
    LIB_EXT = ".dylib"
    LIB_PREFIX = "lib"
    CC = "clang"
    CXX = "clang++"
    EXTRA_CFLAGS = ["-stdlib=libc++"]
    if CI_MODE and SDL2_PREFIX:
        SDL_INCLUDE_DIRS = [f"{SDL2_PREFIX}/include/SDL2", f"{SDL2_PREFIX}/include"]
        SDL_LIB_DIR = f"{SDL2_PREFIX}/lib"
        EXTRA_LDFLAGS = [f"-L{SDL_LIB_DIR}", "-lSDL2", "-framework", "OpenGL"]
    else:
        EXTRA_LDFLAGS = ["-lSDL2", "-framework", "OpenGL"]
        SDL_INCLUDE_DIRS = ["/usr/local/include/SDL2"]
else:  # Linux
    LIB_EXT = ".so"
    LIB_PREFIX = "lib"
    CC = "gcc"
    CXX = "g++"
    EXTRA_CFLAGS = []
    if CI_MODE and SDL2_PREFIX:
        # Try both paths since SDL2 CMake install might use either
        SDL_INCLUDE_DIRS = [f"{SDL2_PREFIX}/include/SDL2", f"{SDL2_PREFIX}/include"]
        SDL_LIB_DIR = f"{SDL2_PREFIX}/lib"
        EXTRA_LDFLAGS = [f"-L{SDL_LIB_DIR}", "-lSDL2", "-lGL", "-ldl", "-lm"]
    else:
        EXTRA_LDFLAGS = ["-L../bindings", "-lSDL2-2.0", "-lGL", "-ldl", "-Wl,-rpath,$ORIGIN/../bindings"]
        SDL_INCLUDE_DIRS = ["bindings/SDL2-2.32.4/include"]

# Simple text output - no colors to avoid encoding issues

def print_step(msg):
    print(f"\n==> {msg}")

def print_success(msg):
    print(f"[OK] {msg}")

def print_error(msg):
    print(f"[ERROR] {msg}")

def print_warning(msg):
    print(f"[WARNING] {msg}")

def run_cmd(cmd, cwd=None, capture=False):
    """Run a command and return success status"""
    if capture:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    else:
        result = subprocess.run(cmd, cwd=cwd)
        return result.returncode == 0

def check_dependencies():
    """Check if required tools are installed"""
    print_step("Checking dependencies...")
    
    deps_ok = True
    
    # Check compiler
    if IS_WINDOWS:
        if not shutil.which("cl"):
            print_error("MSVC compiler (cl) not found. Please install Visual Studio.")
            deps_ok = False
    else:
        if not shutil.which(CXX):
            print_error(f"{CXX} not found. Please install a C++ compiler.")
            deps_ok = False
    
    # Check git
    if not shutil.which("git"):
        print_error("git not found. Please install git.")
        deps_ok = False
    
    # Check SDL2 (we use our own from bindings/)
    if not IS_WINDOWS:
        sdl_lib = Path("bindings/libSDL2-2.0.so")
        if not sdl_lib.exists():
            print_error("SDL2 library not found in bindings/libSDL2-2.0.so")
            deps_ok = False
        else:
            print_success(f"Using SDL2 library from: {sdl_lib}")
        
        # Check headers in bindings
        sdl_headers = Path(SDL_INCLUDE)
        if not sdl_headers.exists():
            print_error(f"SDL2 headers not found in {SDL_INCLUDE}")
            print("  The bindings/SDL2-2.32.4/include directory is missing")
            deps_ok = False
        else:
            print_success(f"Using SDL2 headers from: {sdl_headers}")
    
    # Check OpenGL headers
    if IS_LINUX:
        gl_header = Path("/usr/include/GL/gl.h")
        if not gl_header.exists():
            print_warning("OpenGL headers not found. You may need to install them.")
            print(f"  On Ubuntu/Debian: sudo apt install libgl1-mesa-dev")
    
    if deps_ok:
        print_success("All required dependencies found")
    
    return deps_ok

def check_submodule():
    """Initialize and update cimgui submodule if needed"""
    print_step("Checking cimgui submodule...")
    
    cimgui_dir = Path("cimgui")
    
    # Check if submodule is initialized
    if not cimgui_dir.exists() or not (cimgui_dir / "imgui").exists():
        print("  Initializing submodule...")
        if not run_cmd(["git", "submodule", "update", "--init", "--recursive"]):
            print_error("Failed to initialize submodule")
            return False
    
    # Check if submodule is clean (no uncommitted changes)
    success, stdout, _ = run_cmd(["git", "status", "--porcelain"], cwd="cimgui", capture=True)
    if success and stdout.strip():
        print_warning("cimgui submodule has uncommitted changes")
        response = input("  Reset submodule to clean state? (y/n): ")
        if response.lower() == 'y':
            run_cmd(["git", "reset", "--hard"], cwd="cimgui")
            run_cmd(["git", "clean", "-fd"], cwd="cimgui")
            print_success("Submodule reset to clean state")
        else:
            print_warning("Continuing with modified submodule...")
    
    print_success("Submodule ready")
    return True

def ensure_directories():
    """Create necessary directories"""
    print_step("Setting up directories...")
    
    dirs = ["libs", "imgui_backends"]
    for d in dirs:
        Path(d).mkdir(exist_ok=True)
    
    # Check our wrapper files exist
    wrapper_cpp = Path("imgui_backends/cimgui_sdl2_opengl3.cpp")
    wrapper_h = Path("imgui_backends/cimgui_sdl2_opengl3.h")
    
    if not wrapper_cpp.exists() or not wrapper_h.exists():
        print_error("Wrapper files not found in imgui_backends/")
        print("  Expected: cimgui_sdl2_opengl3.cpp and cimgui_sdl2_opengl3.h")
        return False
    
    print_success("Directories ready")
    return True

def build_library():
    """Build the complete ImGui library"""
    print_step("Building cimgui library...")
    
    # Ensure install directory exists
    INSTALL_PREFIX.mkdir(parents=True, exist_ok=True)
    
    # Copy our wrapper files into cimgui temporarily (if they exist)
    wrapper_cpp = Path("imgui_backends/cimgui_sdl2_opengl3.cpp")
    wrapper_h = Path("imgui_backends/cimgui_sdl2_opengl3.h")
    has_wrappers = wrapper_cpp.exists() and wrapper_h.exists()
    
    if has_wrappers:
        print("  Including SDL2/OpenGL3 wrappers...")
        shutil.copy(wrapper_cpp, "cimgui/")
        shutil.copy(wrapper_h, "cimgui/")
    
    # Change to cimgui directory
    os.chdir("cimgui")
    
    # Source files to compile
    sources = [
        "cimgui.cpp",
        "imgui/imgui.cpp",
        "imgui/imgui_draw.cpp",
        "imgui/imgui_tables.cpp", 
        "imgui/imgui_widgets.cpp",
        "imgui/imgui_demo.cpp",
        "imgui/backends/imgui_impl_sdl2.cpp",
        "imgui/backends/imgui_impl_opengl3.cpp",
        "cimgui_sdl2_opengl3.cpp"
    ]
    
    # Compile each source file
    obj_files = []
    failed = False
    
    for i, src in enumerate(sources, 1):
        print(f"  [{i}/{len(sources)}] Compiling {src}...")
        
        if IS_WINDOWS:
            obj = src.replace(".cpp", ".obj").replace("/", "_")
            cmd = [CXX, "/c", src, f"/Fo{obj}", "/O2", "/EHsc"]
            cmd += ["/I.", "/Iimgui", "/Iimgui/backends"]
            
            # Add SDL2 include paths
            for inc_dir in SDL_INCLUDE_DIRS:
                cmd += [f"/I{inc_dir}"]
            
            cmd += ["/D_WINDOWS", "/DNDEBUG"]
            cmd += EXTRA_CFLAGS
        else:
            obj = src.replace(".cpp", ".o").replace("/", "_")
            cmd = [CXX, "-O2", "-fPIC", "-c", src, "-o", obj]
            cmd += ["-I.", "-Iimgui", "-Iimgui/backends"]
            
            # Add SDL2 include paths
            if CI_MODE:
                for inc_dir in SDL_INCLUDE_DIRS:
                    cmd += [f"-I{inc_dir}"]
            else:
                for inc_dir in SDL_INCLUDE_DIRS:
                    cmd += [f"-I../{inc_dir}"]
            
            cmd += ["-D_REENTRANT"]
            cmd += EXTRA_CFLAGS
        
        if not run_cmd(cmd):
            print_error(f"Failed to compile {src}")
            failed = True
            break
        obj_files.append(obj)
    
    if not failed:
        # Link into shared library
        print("  Linking library...")
        output = f"cimgui_complete{LIB_EXT}"
        
        if IS_WINDOWS:
            cmd = ["link.exe", "/DLL", f"/OUT:{output}"] + obj_files
            cmd += EXTRA_LDFLAGS
        else:
            cmd = [CXX, "-shared"] + obj_files + ["-o", output]
            cmd += EXTRA_LDFLAGS
        
        if not run_cmd(cmd):
            print_error("Failed to link library")
            failed = True
    
    # Clean up regardless of success
    print("  Cleaning up...")
    
    # Remove our copied files
    if os.path.exists("cimgui_sdl2_opengl3.cpp"):
        os.remove("cimgui_sdl2_opengl3.cpp")
    if os.path.exists("cimgui_sdl2_opengl3.h"):
        os.remove("cimgui_sdl2_opengl3.h")
    
    # Remove object files
    for obj in obj_files:
        if os.path.exists(obj):
            os.remove(obj)
    
    # Copy successful build to install location
    if not failed and os.path.exists(output):
        os.chdir("..")
        
        # Install library
        if CI_MODE:
            # For CI, install to proper directories
            lib_dir = INSTALL_PREFIX / "lib"
            bin_dir = INSTALL_PREFIX / "bin"
            inc_dir = INSTALL_PREFIX / "include" / "cimgui"
            
            lib_dir.mkdir(parents=True, exist_ok=True)
            inc_dir.mkdir(parents=True, exist_ok=True)
            
            if IS_WINDOWS:
                bin_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy(f"cimgui/{output}", bin_dir / output)
                # Also need .lib file for Windows
                lib_output = output.replace(".dll", ".lib")
                if os.path.exists(f"cimgui/{lib_output}"):
                    shutil.copy(f"cimgui/{lib_output}", lib_dir / lib_output)
            else:
                shutil.copy(f"cimgui/{output}", lib_dir / output)
            
            # Install headers
            shutil.copy("cimgui/cimgui.h", inc_dir / "cimgui.h")
            if has_wrappers:
                shutil.copy(wrapper_h, inc_dir / "cimgui_sdl2_opengl3.h")
        else:
            # For local development, just put in libs/
            shutil.copy(f"cimgui/{output}", INSTALL_PREFIX / output)
        
        os.remove(f"cimgui/{output}")
        print_success(f"Library installed to: {INSTALL_PREFIX}")
        return True
    
    os.chdir("..")
    return False

def update_rock_file():
    """Update test_gl_triangle.rock to use the built library"""
    print_step("Updating Rock test file...")
    
    test_file = Path("test_gl_triangle.rock")
    if not test_file.exists():
        print_warning("test_gl_triangle.rock not found, skipping update")
        return True
    
    # Read current content
    content = test_file.read_text()
    
    # Get absolute path to library
    lib_path = (Path.cwd() / "libs" / f"cimgui_complete{LIB_EXT}").resolve()
    
    # Update library path
    old_patterns = [
        "/home/darth/projects/rock-headers/libs/libcimgui.so",
        "/home/darth/projects/rock-headers/libs/libcimgui_backends.so",
        "/home/darth/projects/rock-headers/libs/cimgui_complete.so"
    ]
    
    for pattern in old_patterns:
        content = content.replace(pattern, str(lib_path))
    
    # Ensure we're using single library loading
    if "local cimgui = ffi.load" in content and "local backends = ffi.load" in content:
        # Fix double library loading
        content = content.replace(
            """local cimgui = ffi.load""",
            """local lib = ffi.load"""
        )
        # Remove second load
        lines = content.split('\n')
        new_lines = []
        skip_next = False
        for line in lines:
            if skip_next:
                skip_next = False
                continue
            if "local backends = ffi.load" in line:
                skip_next = True
                continue
            new_lines.append(line)
        content = '\n'.join(new_lines)
        
        # Update function references
        content = content.replace("cimgui.", "lib.")
        content = content.replace("backends.", "lib.")
    
    # Write back
    test_file.write_text(content)
    print_success("Rock file updated")
    return True

def test_build():
    """Quick test to verify the build works"""
    print_step("Testing build...")
    
    test_script = f"""
local ffi = require("ffi")
ffi.cdef[[
    typedef struct ImGuiContext ImGuiContext;
    ImGuiContext* igCreateContext(void* shared_font_atlas);
    void igDestroyContext(ImGuiContext* ctx);
]]

local lib = ffi.load("./libs/cimgui_complete{LIB_EXT}")
local ctx = lib.igCreateContext(nil)
if ctx ~= nil then
    lib.igDestroyContext(ctx)
    print("SUCCESS: Library loads and initializes correctly")
    os.exit(0)
else
    print("FAILED: Could not create ImGui context")
    os.exit(1)
end
"""
    
    # Write test script
    with open("test_build.lua", "w") as f:
        f.write(test_script)
    
    # Run test
    success = run_cmd(["luajit", "test_build.lua"])
    
    # Clean up
    os.remove("test_build.lua")
    
    if success:
        print_success("Library test passed")
    else:
        print_error("Library test failed")
    
    return success

def main():
    print(f"{'='*60}")
    print(f"   cimgui Build System")
    print(f"   Platform: {SYSTEM}")
    print(f"   Mode: {'CI' if CI_MODE else 'Local Development'}")
    if CI_MODE:
        print(f"   SDL2: {SDL2_PREFIX}")
        print(f"   Install: {INSTALL_PREFIX}")
    print(f"{'='*60}")
    
    # In CI mode, skip some checks
    if not CI_MODE:
        if not check_dependencies():
            print_error("\nBuild aborted: Missing dependencies")
            return 1
    
    if not check_submodule():
        print_error("\nBuild aborted: Submodule issues")
        return 1
    
    if not CI_MODE:
        if not ensure_directories():
            print_error("\nBuild aborted: Directory setup failed")
            return 1
    
    # Build
    if not build_library():
        print_error("\nBuild failed!")
        return 1
    
    # Only update Rock files and test in local mode
    if not CI_MODE:
        if not update_rock_file():
            print_warning("\nCould not update Rock file")
        
        if test_build():
            print(f"\n{'='*60}")
            print(f"   BUILD SUCCESSFUL!")
            print(f"{'='*60}")
            print(f"\nLibrary location: {INSTALL_PREFIX}/{LIB_PREFIX}cimgui_complete{LIB_EXT}")
        else:
            print_warning("\nBuild completed but test failed")
    else:
        print(f"\n{'='*60}")
        print(f"   BUILD SUCCESSFUL!")
        print(f"{'='*60}")
        print(f"\nLibrary installed to: {INSTALL_PREFIX}")
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nBuild interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)