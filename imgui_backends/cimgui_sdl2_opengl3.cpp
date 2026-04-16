// C wrapper for SDL2 and OpenGL3 backends
#include "../cimgui/imgui/imgui.h"
#include "../cimgui/imgui/backends/imgui_impl_sdl2.h"
#include "../cimgui/imgui/backends/imgui_impl_opengl3.h"
#include <SDL.h>

#ifdef _WIN32
  #define CIMGUI_BACKEND_API __declspec(dllexport)
#else
  #define CIMGUI_BACKEND_API
#endif

extern "C" {

// SDL2 Backend Functions
CIMGUI_BACKEND_API bool cImGui_ImplSDL2_InitForOpenGL(SDL_Window* window, void* sdl_gl_context) {
    return ImGui_ImplSDL2_InitForOpenGL(window, sdl_gl_context);
}

CIMGUI_BACKEND_API void cImGui_ImplSDL2_Shutdown() {
    ImGui_ImplSDL2_Shutdown();
}

CIMGUI_BACKEND_API void cImGui_ImplSDL2_NewFrame() {
    ImGui_ImplSDL2_NewFrame();
}

CIMGUI_BACKEND_API bool cImGui_ImplSDL2_ProcessEvent(const SDL_Event* event) {
    return ImGui_ImplSDL2_ProcessEvent(event);
}

// OpenGL3 Backend Functions
CIMGUI_BACKEND_API bool cImGui_ImplOpenGL3_Init(const char* glsl_version) {
    return ImGui_ImplOpenGL3_Init(glsl_version);
}

CIMGUI_BACKEND_API void cImGui_ImplOpenGL3_Shutdown() {
    ImGui_ImplOpenGL3_Shutdown();
}

CIMGUI_BACKEND_API void cImGui_ImplOpenGL3_NewFrame() {
    ImGui_ImplOpenGL3_NewFrame();
}

CIMGUI_BACKEND_API void cImGui_ImplOpenGL3_RenderDrawData(ImDrawData* draw_data) {
    ImGui_ImplOpenGL3_RenderDrawData(draw_data);
}

CIMGUI_BACKEND_API bool cImGui_ImplOpenGL3_CreateDeviceObjects() {
    return ImGui_ImplOpenGL3_CreateDeviceObjects();
}

CIMGUI_BACKEND_API void cImGui_ImplOpenGL3_DestroyDeviceObjects() {
    ImGui_ImplOpenGL3_DestroyDeviceObjects();
}

} // extern "C"