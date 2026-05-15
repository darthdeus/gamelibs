# GameLibs Project

## Purpose
Build and maintain precompiled game development libraries for Rock projects, with automated CI/CD via GitHub Actions.

## Libraries to Build
- **SDL2** - Cross-platform multimedia library
- **SDL_image** - Image loading (PNG, JPEG, WebP support) 
- **SDL_mixer** - Audio mixing (WAV, OGG, FLAC, MP3 support)
- **ImGui** (cimgui) - Immediate mode GUI with SDL2/OpenGL3 backends
- **FreeType** - Font rendering library
- **LuaJIT** - Just-in-time compiler for Lua
- **libmpv + ffmpeg** (IN PROGRESS - see `BUILD_MPV.md`) - Media playback and
  screen capture for Anvil. Uses mpv-build to produce a self-contained
  libmpv.dylib/.so with the ffmpeg libs (libavcodec, libavformat,
  libavdevice, libavutil, libswscale, libswresample) as separate shared libs
  alongside it. Both stone-video (playback via libmpv) and the Anvil recorder
  (screen capture via libavdevice) link against these vendored builds,
  guaranteeing version consistency. Living plan + phase status + pinned
  versions + the root incident that motivated it: **`BUILD_MPV.md`**.
  See also `anvil/docs/recorder-design.md` and `anvil/TODO.md`.

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
- Vendor main libraries (SDL_image, SDL_mixer) for reproducible builds
- Download dependencies during build as needed (zlib, libpng, etc.)
- All dependencies explicit and versioned
- Reproducible builds
- Output to standardized paths for easy consumption

## Vendored Sources
- **SDL2_image-2.8.2/** - Vendored SDL_image source
- **SDL2_mixer-2.8.0/** - Vendored SDL_mixer source
- Dependencies (zlib, libpng, libvorbis, etc.) downloaded during build