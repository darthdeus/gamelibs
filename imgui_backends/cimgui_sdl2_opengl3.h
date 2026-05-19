#ifndef CIMGUI_SDL2_OPENGL3_H
#define CIMGUI_SDL2_OPENGL3_H

#include <stdbool.h>

#ifdef _WIN32
  #define CIMGUI_BACKEND_API __declspec(dllexport)
#else
  #define CIMGUI_BACKEND_API
#endif

#ifdef __cplusplus
extern "C" {
#endif

// Forward declarations
struct SDL_Window;
union SDL_Event;
struct ImDrawData;

// SDL2 Backend Functions
CIMGUI_BACKEND_API bool cImGui_ImplSDL2_InitForOpenGL(struct SDL_Window* window, void* sdl_gl_context);
CIMGUI_BACKEND_API void cImGui_ImplSDL2_Shutdown();
CIMGUI_BACKEND_API void cImGui_ImplSDL2_NewFrame();
CIMGUI_BACKEND_API bool cImGui_ImplSDL2_ProcessEvent(const union SDL_Event* event);

// OpenGL3 Backend Functions
CIMGUI_BACKEND_API bool cImGui_ImplOpenGL3_Init(const char* glsl_version);
CIMGUI_BACKEND_API void cImGui_ImplOpenGL3_Shutdown();
CIMGUI_BACKEND_API void cImGui_ImplOpenGL3_NewFrame();
CIMGUI_BACKEND_API void cImGui_ImplOpenGL3_RenderDrawData(struct ImDrawData* draw_data);
CIMGUI_BACKEND_API bool cImGui_ImplOpenGL3_CreateDeviceObjects();
CIMGUI_BACKEND_API void cImGui_ImplOpenGL3_DestroyDeviceObjects();

#ifdef __cplusplus
}
#endif

#endif // CIMGUI_SDL2_OPENGL3_H
