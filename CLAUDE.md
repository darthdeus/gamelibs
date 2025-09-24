# GameLibs Project

## Purpose
Build and maintain precompiled game development libraries for Rock projects, with automated CI/CD via GitHub Actions.

## Libraries to Build
- **ImGui** (cimgui) - Immediate mode GUI with SDL2/OpenGL3 backends
- **SDL2** - Cross-platform multimedia library  
- **Others TBD** - As needed by Rock game projects

## Structure
```
gamelibs/
├── imgui/
│   ├── build.py          # Build script for ImGui
│   ├── wrappers/          # C wrappers for backends
│   └── prebuilt/          # Compiled binaries per platform
├── sdl2/
│   ├── build.py          # Build script for SDL2
│   └── prebuilt/          # Compiled binaries per platform
└── .github/
    └── workflows/         # GitHub Actions for automated builds
```

## Goals
1. **Self-contained builds** - Each library builds independently
2. **Cross-platform** - Linux, macOS, Windows binaries
3. **Automated CI** - GitHub Actions builds on every commit
4. **Version control** - Tag releases for stable versions
5. **Easy integration** - Rock projects can just grab prebuilt binaries

## ImGui Specific Notes
- Build cimgui + backends into single .so/.dylib/.dll
- Include SDL2 and OpenGL3 backends
- C wrappers for backend functions (already created)
- No submodules - vendor source snapshots or download during build

## Build Requirements
- Download source archives during build (no submodules)
- All dependencies explicit and versioned
- Reproducible builds
- Output to standardized paths for easy consumption