#!/usr/bin/env python3
"""
One-command build script for ImGui + Rock integration
Usage: ./build.py
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

# Platform-specific settings
if IS_WINDOWS:
    LIB_EXT = ".dll"
    CC = "cl"
    CXX = "cl"
    EXTRA_CFLAGS = []
    EXTRA_LDFLAGS = ["-lSDL2", "-lopengl32"]
    SDL_INCLUDE = "C:/SDL2/include"  # Adjust as needed
elif IS_MACOS:
    LIB_EXT = ".dylib"
    CC = "clang"
    CXX = "clang++"
    EXTRA_CFLAGS = ["-stdlib=libc++"]
    EXTRA_LDFLAGS = ["-lSDL2", "-framework", "OpenGL"]
    SDL_INCLUDE = "/usr/local/include/SDL2"  # Homebrew default
else:  # Linux
    LIB_EXT = ".so"
    CC = "gcc"
    CXX = "g++"
    EXTRA_CFLAGS = []
    # Use the SDL2 library from bindings instead of system
    EXTRA_LDFLAGS = ["-L../bindings", "-lSDL2-2.0", "-lGL", "-ldl", "-Wl,-rpath,$ORIGIN/../bindings"]
    SDL_INCLUDE = "bindings/SDL2-2.32.4/include"  # Use headers from bindings too!

# Colors for output
class Colors:
    GREEN = '\033[92m' if not IS_WINDOWS else ''
    YELLOW = '\033[93m' if not IS_WINDOWS else ''
    RED = '\033[91m' if not IS_WINDOWS else ''
    BLUE = '\033[94m' if not IS_WINDOWS else ''
    ENDC = '\033[0m' if not IS_WINDOWS else ''
    BOLD = '\033[1m' if not IS_WINDOWS else ''

def print_step(msg):
    print(f"\n{Colors.BLUE}{Colors.BOLD}==> {msg}{Colors.ENDC}")

def print_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.ENDC}")

def print_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.ENDC}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.ENDC}")

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
    print_step("Building ImGui library...")
    
    # Copy our wrapper files into cimgui temporarily
    print("  Copying wrapper files...")
    shutil.copy("imgui_backends/cimgui_sdl2_opengl3.cpp", "cimgui/")
    shutil.copy("imgui_backends/cimgui_sdl2_opengl3.h", "cimgui/")
    
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
        obj = src.replace(".cpp", ".o").replace("/", "_")
        
        cmd = [CXX, "-O2", "-fPIC", "-c", src, "-o", obj]
        cmd += ["-I.", "-Iimgui", "-Iimgui/backends"]
        
        # Add SDL2 include path from bindings (we're in cimgui dir, so go up one level)
        cmd += [f"-I../{SDL_INCLUDE}"]
        
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
    
    # Copy successful build to libs
    if not failed and os.path.exists(output):
        os.chdir("..")
        shutil.copy(f"cimgui/{output}", f"libs/{output}")
        os.remove(f"cimgui/{output}")
        print_success(f"Library built: libs/{output}")
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
    print(f"{Colors.BOLD}{'='*60}")
    print(f"   ImGui + Rock Build System")
    print(f"   Platform: {SYSTEM}")
    print(f"{'='*60}{Colors.ENDC}")
    
    # Check everything
    if not check_dependencies():
        print_error("\nBuild aborted: Missing dependencies")
        return 1
    
    if not check_submodule():
        print_error("\nBuild aborted: Submodule issues")
        return 1
    
    if not ensure_directories():
        print_error("\nBuild aborted: Directory setup failed")
        return 1
    
    # Build
    if not build_library():
        print_error("\nBuild failed!")
        return 1
    
    # Update Rock file
    if not update_rock_file():
        print_warning("\nCould not update Rock file")
    
    # Test
    if test_build():
        print(f"\n{Colors.GREEN}{Colors.BOLD}{'='*60}")
        print(f"   ✅ BUILD SUCCESSFUL!")
        print(f"{'='*60}{Colors.ENDC}")
        print(f"\nLibrary location: libs/cimgui_complete{LIB_EXT}")
        print(f"You can now compile and run test_gl_triangle.rock")
    else:
        print_warning("\nBuild completed but test failed")
        print("The library was built but may have issues")
    
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