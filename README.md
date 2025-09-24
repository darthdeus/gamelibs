this repo serves a single purpose, precompile commonly used game libraries, with the intention of vendoring them

## Libraries Included

- **SDL2** - Cross-platform multimedia library
- **SDL_image** - Image loading library (PNG, JPEG, WebP support)
- **SDL_mixer** - Audio mixing library (WAV, OGG/Vorbis, FLAC, MP3* support)
- **FreeType** - Font rendering library
- **cimgui** - C wrapper for Dear ImGui with SDL2/OpenGL3 backends
- **LuaJIT** - Just-In-Time Lua compiler

## TODO

- [ ] **mpg123 Windows support** - Currently MP3 support in SDL_mixer is unavailable on Windows due to mpg123 lacking CMake build files. Need to either:
  - Add Windows build support for mpg123
  - Use an alternative MP3 decoder on Windows
  - Create CMake build files for mpg123

## License

MPL, check LICENSE.md
