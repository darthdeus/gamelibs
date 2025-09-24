#ifndef CIMGUI_SDL2_OPENGL3_H
#define CIMGUI_SDL2_OPENGL3_H

#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

// Forward declarations
struct SDL_Window;
union SDL_Event;
struct ImDrawData;

// SDL2 Backend Functions
bool cImGui_ImplSDL2_InitForOpenGL(struct SDL_Window* window, void* sdl_gl_context);
void cImGui_ImplSDL2_Shutdown();
void cImGui_ImplSDL2_NewFrame();
bool cImGui_ImplSDL2_ProcessEvent(const union SDL_Event* event);

// OpenGL3 Backend Functions  
bool cImGui_ImplOpenGL3_Init(const char* glsl_version);
void cImGui_ImplOpenGL3_Shutdown();
void cImGui_ImplOpenGL3_NewFrame();
void cImGui_ImplOpenGL3_RenderDrawData(struct ImDrawData* draw_data);
bool cImGui_ImplOpenGL3_CreateDeviceObjects();
void cImGui_ImplOpenGL3_DestroyDeviceObjects();

#ifdef __cplusplus
}
#endif

#endif // CIMGUI_SDL2_OPENGL3_H