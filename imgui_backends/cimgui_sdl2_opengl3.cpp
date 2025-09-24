// C wrapper for SDL2 and OpenGL3 backends
#include "../cimgui/imgui/imgui.h"
#include "../cimgui/imgui/backends/imgui_impl_sdl2.h"
#include "../cimgui/imgui/backends/imgui_impl_opengl3.h"
#include <SDL.h>

extern "C" {

// SDL2 Backend Functions
bool cImGui_ImplSDL2_InitForOpenGL(SDL_Window* window, void* sdl_gl_context) {
    return ImGui_ImplSDL2_InitForOpenGL(window, sdl_gl_context);
}

void cImGui_ImplSDL2_Shutdown() {
    ImGui_ImplSDL2_Shutdown();
}

void cImGui_ImplSDL2_NewFrame() {
    ImGui_ImplSDL2_NewFrame();
}

bool cImGui_ImplSDL2_ProcessEvent(const SDL_Event* event) {
    return ImGui_ImplSDL2_ProcessEvent(event);
}

// OpenGL3 Backend Functions
bool cImGui_ImplOpenGL3_Init(const char* glsl_version) {
    return ImGui_ImplOpenGL3_Init(glsl_version);
}

void cImGui_ImplOpenGL3_Shutdown() {
    ImGui_ImplOpenGL3_Shutdown();
}

void cImGui_ImplOpenGL3_NewFrame() {
    ImGui_ImplOpenGL3_NewFrame();
}

void cImGui_ImplOpenGL3_RenderDrawData(ImDrawData* draw_data) {
    ImGui_ImplOpenGL3_RenderDrawData(draw_data);
}

bool cImGui_ImplOpenGL3_CreateDeviceObjects() {
    return ImGui_ImplOpenGL3_CreateDeviceObjects();
}

void cImGui_ImplOpenGL3_DestroyDeviceObjects() {
    ImGui_ImplOpenGL3_DestroyDeviceObjects();
}

} // extern "C"