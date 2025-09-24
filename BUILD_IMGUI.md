# Building ImGui for Rock

## Quick Start

Just run:
```bash
./build.py
```

This will:
1. Check all dependencies (compiler, SDL2, OpenGL)
2. Initialize/update the cimgui submodule
3. Build everything into a single library (`libs/cimgui_complete.so`)
4. Update Rock files to use the correct paths
5. Test that the library works

## Prerequisites

### Linux
```bash
sudo apt install g++ libsdl2-dev libgl1-mesa-dev  # Ubuntu/Debian
sudo dnf install gcc-c++ SDL2-devel mesa-libGL-devel  # Fedora
```

### macOS
```bash
brew install sdl2
```

### Windows
- Install Visual Studio with C++ support
- Download SDL2 development libraries
- Adjust paths in `build.py` if needed

## Project Structure

```
rock-headers/
├── cimgui/                    # Git submodule (don't modify)
├── imgui_backends/            # Our C wrapper files
│   ├── cimgui_sdl2_opengl3.cpp
│   ├── cimgui_sdl2_opengl3.h
│   └── cimgui_essential.h
├── libs/                      # Built libraries go here
│   └── cimgui_complete.so
├── test_gl_triangle.rock      # Example using ImGui
└── build.py                   # Build script
```

## How It Works

1. The build script temporarily copies our wrapper files into the cimgui directory
2. Compiles everything together (cimgui + imgui + backends + our wrappers)
3. Creates a single shared library with all symbols
4. Cleans up the cimgui directory (removes temporary files)
5. The cimgui submodule remains clean for easy updates

## Updating ImGui

To update to a newer version of ImGui:

```bash
cd cimgui
git pull origin master
cd ..
./build.py
```

## Troubleshooting

If the build fails:
- Check the error messages for missing dependencies
- Ensure the cimgui submodule is initialized: `git submodule update --init --recursive`
- Reset the submodule if it's dirty: `cd cimgui && git reset --hard && cd ..`
- Check that SDL2 development files are installed
- On Linux, you may need to run with `LD_LIBRARY_PATH=libs luajit test_gl_triangle.lua`

## Testing

After building, test with:
```bash
cargo run --bin rock compile test_gl_triangle.rock test_gl_triangle.lua
luajit test_gl_triangle.lua
```

You should see a window with an orange triangle and the ImGui demo window.