# Portability Issues Found in Release v0.1.2

## Critical Issues

### 1. FreeType has system dependencies
- **Problem**: Links to system libpng16, libbz2, libz
- **Fix**: Add CMake flags to disable these features:
  ```cmake
  -DFT_DISABLE_PNG=ON
  -DFT_DISABLE_BZIP2=ON
  -DFT_DISABLE_ZLIB=ON
  ```

### 2. cimgui links to system SDL2
- **Problem**: cimgui_complete.so depends on system libSDL2-2.0.so.0
- **Fix**: Set rpath to use bundled SDL2:
  ```bash
  -Wl,-rpath,'$ORIGIN'
  ```

### 3. C++ runtime dependencies
- **Less critical**: libstdc++.so.6, libgcc_s.so.1
- **Potential fix**: Static link or accept as baseline requirement

## Current Dependencies Summary

**Good (minimal deps):**
- SDL2: Only libc, libm
- LuaJIT: Only libc, libm, libgcc_s

**Problematic:**
- FreeType: libpng16, libbz2, libz (system specific versions)
- cimgui: Links to system SDL2 instead of bundled

## Recommended Actions

1. Update FreeType build to disable external deps
2. Fix cimgui build to use relative rpath
3. Test on clean system without dev packages
4. Consider fully static builds for maximum portability