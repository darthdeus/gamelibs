local ffi = require("ffi")

-- Platform detection and library loading
local os_name = jit.os
local lib_path = ""
local lib_ext = ""

if os_name == "Linux" then
    lib_path = "./prebuilt/linux/x86_64"
    lib_ext = ".so"
elseif os_name == "Windows" then
    lib_path = "./prebuilt/windows/x86_64"
    lib_ext = ".dll"
elseif os_name == "OSX" then
    lib_path = "./prebuilt/macos/x86_64"
    lib_ext = ".dylib"
else
    error("Unsupported platform: " .. os_name)
end

print("Platform: " .. os_name)
print("Library path: " .. lib_path)

-- SDL2 C definitions
ffi.cdef[[
    typedef struct SDL_Window SDL_Window;
    typedef struct SDL_Surface SDL_Surface;
    typedef enum {
        SDL_INIT_VIDEO = 0x00000020,
        SDL_INIT_TIMER = 0x00000001
    } SDL_InitFlag;
    
    typedef enum {
        SDL_WINDOWPOS_UNDEFINED = 0x1FFF0000,
        SDL_WINDOW_SHOWN = 0x00000004,
        SDL_WINDOW_OPENGL = 0x00000002,
        SDL_WINDOW_RESIZABLE = 0x00000020,
        SDL_WINDOW_ALLOW_HIGHDPI = 0x00002000
    } SDL_WindowFlags;
    
    typedef union SDL_Event {
        uint32_t type;
        struct {
            uint32_t type;
            uint32_t timestamp;
            uint32_t windowID;
            uint8_t state;
            uint8_t repeat;
            uint8_t padding2;
            uint8_t padding3;
            int32_t scancode;
            int32_t sym;
            uint16_t mod;
            uint32_t unused;
        } key;
        char padding[56];
    } SDL_Event;
    
    typedef enum {
        SDL_QUIT = 0x100,
        SDL_KEYDOWN = 0x300,
        SDL_WINDOWEVENT = 0x200
    } SDL_EventType;
    
    typedef enum {
        SDLK_ESCAPE = 27
    } SDL_Keycode;

    typedef void* SDL_GLContext;
    
    int SDL_Init(uint32_t flags);
    void SDL_Quit(void);
    SDL_Window* SDL_CreateWindow(const char* title, int x, int y, int w, int h, uint32_t flags);
    void SDL_DestroyWindow(SDL_Window* window);
    int SDL_PollEvent(SDL_Event* event);
    void SDL_Delay(uint32_t ms);
    int SDL_SetHint(const char* name, const char* value);
    uint32_t SDL_GetTicks(void);
    void SDL_GetWindowSize(SDL_Window* window, int* w, int* h);
    int SDL_GL_SetAttribute(int attr, int value);
    
    // OpenGL context functions
    SDL_GLContext SDL_GL_CreateContext(SDL_Window* window);
    void SDL_GL_DeleteContext(SDL_GLContext context);
    int SDL_GL_SetSwapInterval(int interval);
    void SDL_GL_SwapWindow(SDL_Window* window);
    void* SDL_GL_GetProcAddress(const char* proc);
]]

-- ImGui C definitions (from cimgui)
ffi.cdef[[
    typedef struct ImGuiContext ImGuiContext;
    typedef struct ImDrawData ImDrawData;
    typedef struct ImFont ImFont;
    typedef struct ImVec2 { float x, y; } ImVec2;
    typedef struct ImVec4 { float x, y, z, w; } ImVec4;
    
    // ImGuiIO structure - partial definition with fields we need
    typedef struct ImGuiIO {
        int ConfigFlags;
        int BackendFlags;
        ImVec2 DisplaySize;
        ImVec2 DisplayFramebufferScale;
        float DeltaTime;
        // ... many config fields we skip ...
        char _padding[256]; // Padding to reach the metrics fields
        float Framerate;
        int MetricsRenderVertices;
        int MetricsRenderIndices;
        int MetricsRenderWindows;
        int MetricsActiveWindows;
    } ImGuiIO;
    
    // Core ImGui functions
    ImGuiContext* igCreateContext(ImFont* shared_font_atlas);
    void igDestroyContext(ImGuiContext* ctx);
    ImGuiIO* igGetIO_Nil(void);  // cimgui uses _Nil suffix for no-arg version
    void igNewFrame(void);
    void igRender(void);
    ImDrawData* igGetDrawData(void);
    void igShowDemoWindow(bool* p_open);
    bool igBegin(const char* name, bool* p_open, int flags);
    void igEnd(void);
    void igText(const char* fmt, ...);
    bool igButton(const char* label, ImVec2 size);
    bool igSliderFloat(const char* label, float* v, float v_min, float v_max, const char* format, int flags);
    bool igColorEdit3(const char* label, float col[3], int flags);
    bool igCheckbox(const char* label, bool* v);
    
    // SDL2 backend functions (from our wrapper)
    bool cImGui_ImplSDL2_InitForOpenGL(SDL_Window* window, void* sdl_gl_context);
    void cImGui_ImplSDL2_Shutdown(void);
    void cImGui_ImplSDL2_NewFrame(void);
    bool cImGui_ImplSDL2_ProcessEvent(const SDL_Event* event);
    
    // OpenGL3 backend functions (from our wrapper)
    bool cImGui_ImplOpenGL3_Init(const char* glsl_version);
    void cImGui_ImplOpenGL3_Shutdown(void);
    void cImGui_ImplOpenGL3_NewFrame(void);
    void cImGui_ImplOpenGL3_RenderDrawData(ImDrawData* draw_data);
]]

-- OpenGL constants and types
local GL_COLOR_BUFFER_BIT = 0x00004000
local GL_TRIANGLES = 0x0004
local GL_VERTEX_SHADER = 0x8B31
local GL_FRAGMENT_SHADER = 0x8B30
local GL_COMPILE_STATUS = 0x8B81
local GL_LINK_STATUS = 0x8B82
local GL_ARRAY_BUFFER = 0x8892
local GL_STATIC_DRAW = 0x88E4
local GL_FLOAT = 0x1406
local GL_FALSE = 0

-- OpenGL function pointers
local glClear, glClearColor, glDrawArrays, glViewport
local glCreateShader, glShaderSource, glCompileShader, glGetShaderiv
local glCreateProgram, glAttachShader, glLinkProgram, glUseProgram, glGetProgramiv
local glGenBuffers, glBindBuffer, glBufferData
local glGenVertexArrays, glBindVertexArray, glVertexAttribPointer, glEnableVertexAttribArray

-- Load SDL2 library from prebuilt directory
print("Loading SDL2 from prebuilt libraries...")
local SDL
if os_name == "Windows" then
    SDL = ffi.load(lib_path .. "/lib/SDL2" .. lib_ext)
else
    SDL = ffi.load(lib_path .. "/lib/libSDL2-2.0" .. lib_ext)
end

-- Load cimgui complete (includes ImGui + backends)
print("Loading cimgui...")
local imgui = ffi.load(lib_path .. "/lib/cimgui_complete" .. lib_ext)

-- Helper function to load OpenGL functions
local function loadGLFunction(name)
    local proc = SDL.SDL_GL_GetProcAddress(name)
    if proc == nil then
        error("Failed to load OpenGL function: " .. name)
    end
    return proc
end

-- Initialize SDL
print("Initializing SDL...")
if SDL.SDL_Init(bit.bor(SDL.SDL_INIT_VIDEO, SDL.SDL_INIT_TIMER)) < 0 then
    error("Failed to initialize SDL")
end

-- Setup SDL OpenGL attributes
SDL.SDL_GL_SetAttribute(3, 3) -- SDL_GL_CONTEXT_MAJOR_VERSION
SDL.SDL_GL_SetAttribute(4, 3) -- SDL_GL_CONTEXT_MINOR_VERSION
SDL.SDL_GL_SetAttribute(5, 2) -- SDL_GL_CONTEXT_PROFILE_MASK = CORE

-- Set hint to prevent window from grabbing focus
SDL.SDL_SetHint("SDL_HINT_WINDOW_NO_ACTIVATION_WHEN_SHOWN", "1")

-- Create window
print("Creating SDL window with OpenGL support...")
local window = SDL.SDL_CreateWindow(
    "Lua + ImGui Demo (Prebuilt Libs)",
    SDL.SDL_WINDOWPOS_UNDEFINED,
    SDL.SDL_WINDOWPOS_UNDEFINED,
    1280, 720,
    bit.bor(SDL.SDL_WINDOW_SHOWN, SDL.SDL_WINDOW_OPENGL, SDL.SDL_WINDOW_RESIZABLE, SDL.SDL_WINDOW_ALLOW_HIGHDPI)
)

if window == nil then
    SDL.SDL_Quit()
    error("Failed to create window")
end

-- Create OpenGL context
print("Creating OpenGL context...")
local gl_context = SDL.SDL_GL_CreateContext(window)
if gl_context == nil then
    SDL.SDL_DestroyWindow(window)
    SDL.SDL_Quit()
    error("Failed to create OpenGL context")
end

-- Enable VSync
SDL.SDL_GL_SetSwapInterval(1)

-- Load OpenGL functions
print("Loading OpenGL functions...")
glClear = ffi.cast("void (*)(unsigned int)", loadGLFunction("glClear"))
glClearColor = ffi.cast("void (*)(float, float, float, float)", loadGLFunction("glClearColor"))
glDrawArrays = ffi.cast("void (*)(unsigned int, int, int)", loadGLFunction("glDrawArrays"))
glViewport = ffi.cast("void (*)(int, int, int, int)", loadGLFunction("glViewport"))
glCreateShader = ffi.cast("unsigned int (*)(unsigned int)", loadGLFunction("glCreateShader"))
glShaderSource = ffi.cast("void (*)(unsigned int, int, const char**, const int*)", loadGLFunction("glShaderSource"))
glCompileShader = ffi.cast("void (*)(unsigned int)", loadGLFunction("glCompileShader"))
glGetShaderiv = ffi.cast("void (*)(unsigned int, unsigned int, int*)", loadGLFunction("glGetShaderiv"))
glCreateProgram = ffi.cast("unsigned int (*)(void)", loadGLFunction("glCreateProgram"))
glAttachShader = ffi.cast("void (*)(unsigned int, unsigned int)", loadGLFunction("glAttachShader"))
glLinkProgram = ffi.cast("void (*)(unsigned int)", loadGLFunction("glLinkProgram"))
glUseProgram = ffi.cast("void (*)(unsigned int)", loadGLFunction("glUseProgram"))
glGetProgramiv = ffi.cast("void (*)(unsigned int, unsigned int, int*)", loadGLFunction("glGetProgramiv"))
glGenBuffers = ffi.cast("void (*)(int, unsigned int*)", loadGLFunction("glGenBuffers"))
glBindBuffer = ffi.cast("void (*)(unsigned int, unsigned int)", loadGLFunction("glBindBuffer"))
glBufferData = ffi.cast("void (*)(unsigned int, long, const void*, unsigned int)", loadGLFunction("glBufferData"))
glGenVertexArrays = ffi.cast("void (*)(int, unsigned int*)", loadGLFunction("glGenVertexArrays"))
glBindVertexArray = ffi.cast("void (*)(unsigned int)", loadGLFunction("glBindVertexArray"))
glVertexAttribPointer = ffi.cast("void (*)(unsigned int, int, unsigned int, unsigned char, int, const void*)", loadGLFunction("glVertexAttribPointer"))
glEnableVertexAttribArray = ffi.cast("void (*)(unsigned int)", loadGLFunction("glEnableVertexAttribArray"))

-- Setup ImGui
print("Initializing ImGui...")
imgui.igCreateContext(nil)

-- Initialize ImGui backends
if not imgui.cImGui_ImplSDL2_InitForOpenGL(window, gl_context) then
    error("Failed to initialize ImGui SDL2 backend")
end

if not imgui.cImGui_ImplOpenGL3_Init("#version 130") then
    error("Failed to initialize ImGui OpenGL3 backend")
end

-- Shader source code
local vertexShaderSource = [[
#version 330 core
layout (location = 0) in vec3 aPos;
void main()
{
    gl_Position = vec4(aPos.x, aPos.y, aPos.z, 1.0);
}
]]

local fragmentShaderSource = [[
#version 330 core
out vec4 FragColor;
void main()
{
    FragColor = vec4(1.0f, 0.5f, 0.2f, 1.0f);
}
]]

-- Create and compile vertex shader
local vertexShader = glCreateShader(GL_VERTEX_SHADER)
local vertexSourcePtr = ffi.new("const char*[1]")
vertexSourcePtr[0] = vertexShaderSource
glShaderSource(vertexShader, 1, vertexSourcePtr, nil)
glCompileShader(vertexShader)

-- Check vertex shader compilation
local success = ffi.new("int[1]")
glGetShaderiv(vertexShader, GL_COMPILE_STATUS, success)
if success[0] == GL_FALSE then
    error("Failed to compile vertex shader")
end

-- Create and compile fragment shader
local fragmentShader = glCreateShader(GL_FRAGMENT_SHADER)
local fragmentSourcePtr = ffi.new("const char*[1]")
fragmentSourcePtr[0] = fragmentShaderSource
glShaderSource(fragmentShader, 1, fragmentSourcePtr, nil)
glCompileShader(fragmentShader)

-- Check fragment shader compilation
glGetShaderiv(fragmentShader, GL_COMPILE_STATUS, success)
if success[0] == GL_FALSE then
    error("Failed to compile fragment shader")
end

-- Create shader program
local shaderProgram = glCreateProgram()
glAttachShader(shaderProgram, vertexShader)
glAttachShader(shaderProgram, fragmentShader)
glLinkProgram(shaderProgram)

-- Check program linking
glGetProgramiv(shaderProgram, GL_LINK_STATUS, success)
if success[0] == GL_FALSE then
    error("Failed to link shader program")
end

-- Triangle vertices
local vertices = ffi.new("float[9]", {
    -0.5, -0.5, 0.0,
     0.5, -0.5, 0.0,
     0.0,  0.5, 0.0
})

-- Create VAO and VBO
local VAO = ffi.new("unsigned int[1]")
local VBO = ffi.new("unsigned int[1]")

glGenVertexArrays(1, VAO)
glGenBuffers(1, VBO)

glBindVertexArray(VAO[0])
glBindBuffer(GL_ARRAY_BUFFER, VBO[0])
glBufferData(GL_ARRAY_BUFFER, ffi.sizeof(vertices), vertices, GL_STATIC_DRAW)

glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * ffi.sizeof("float"), nil)
glEnableVertexAttribArray(0)

print("Setup complete!")
print("Using libraries from: " .. lib_path)
print("Press Escape or close window to exit...")

-- ImGui demo window state
local show_demo = ffi.new("bool[1]", true)
local show_another = ffi.new("bool[1]", false)
local clear_color = ffi.new("float[3]", {0.2, 0.3, 0.3})
local counter = 0
local slider_value = ffi.new("float[1]", 0.5)
local checkbox_value = ffi.new("bool[1]", false)

-- FPS tracking
local frame_count = 0
local last_time = SDL.SDL_GetTicks()
local fps = 0.0

-- Main event loop
local event = ffi.new("SDL_Event")
local running = true

while running do
    -- FPS calculation
    frame_count = frame_count + 1
    local current_time = SDL.SDL_GetTicks()
    if current_time - last_time >= 1000 then
        fps = frame_count * 1000.0 / (current_time - last_time)
        frame_count = 0
        last_time = current_time
    end
    
    -- Poll events
    while SDL.SDL_PollEvent(event) ~= 0 do
        imgui.cImGui_ImplSDL2_ProcessEvent(event)
        
        if event.type == SDL.SDL_QUIT then
            running = false
        elseif event.type == SDL.SDL_KEYDOWN then
            if event.key.sym == SDL.SDLK_ESCAPE then
                running = false
            end
        end
    end
    
    -- Start ImGui frame
    imgui.cImGui_ImplOpenGL3_NewFrame()
    imgui.cImGui_ImplSDL2_NewFrame()
    imgui.igNewFrame()
    
    -- Show demo window
    if show_demo[0] then
        imgui.igShowDemoWindow(show_demo)
    end
    
    -- Create a custom window
    if imgui.igBegin("Hello from Lua!", nil, 0) then
        imgui.igText("This is ImGui running in LuaJIT!")
        imgui.igText("Libraries loaded from: " .. lib_path)
        
        imgui.igCheckbox("Demo Window", show_demo)
        imgui.igCheckbox("Another Window", show_another)
        
        imgui.igSliderFloat("Triangle Size", slider_value, 0.1, 1.0, "%.3f", 0)
        imgui.igColorEdit3("Clear color", clear_color, 0)
        
        if imgui.igButton("Button", ffi.new("ImVec2", {0, 0})) then
            counter = counter + 1
        end
        imgui.igText(string.format("Button clicked %d times", counter))
        
        imgui.igCheckbox("Show Triangle", checkbox_value)
        
        -- FPS display
        imgui.igText(string.format("FPS: %.1f", fps))
    end
    imgui.igEnd()
    
    -- Show another window
    if show_another[0] then
        if imgui.igBegin("Another Window", show_another, 0) then
            imgui.igText("Hello from another window!")
            if imgui.igButton("Close Me", ffi.new("ImVec2", {0, 0})) then
                show_another[0] = false
            end
        end
        imgui.igEnd()
    end
    
    -- Rendering
    imgui.igRender()
    
    local display_w = ffi.new("int[1]")
    local display_h = ffi.new("int[1]")
    SDL.SDL_GetWindowSize(window, display_w, display_h)
    glViewport(0, 0, display_w[0], display_h[0])
    glClearColor(clear_color[0], clear_color[1], clear_color[2], 1.0)
    glClear(GL_COLOR_BUFFER_BIT)
    
    -- Draw triangle if checkbox is enabled
    if checkbox_value[0] then
        -- Update triangle vertices based on slider
        local size = slider_value[0]
        vertices[0] = -0.5 * size  -- bottom left x
        vertices[3] = 0.5 * size   -- bottom right x
        vertices[7] = 0.5 * size   -- top y
        
        glBindBuffer(GL_ARRAY_BUFFER, VBO[0])
        glBufferData(GL_ARRAY_BUFFER, ffi.sizeof(vertices), vertices, GL_STATIC_DRAW)
        
        glUseProgram(shaderProgram)
        glBindVertexArray(VAO[0])
        glDrawArrays(GL_TRIANGLES, 0, 3)
    end
    
    imgui.cImGui_ImplOpenGL3_RenderDrawData(imgui.igGetDrawData())
    
    SDL.SDL_GL_SwapWindow(window)
end

-- Cleanup
print("Cleaning up...")
imgui.cImGui_ImplOpenGL3_Shutdown()
imgui.cImGui_ImplSDL2_Shutdown()
imgui.igDestroyContext(nil)

SDL.SDL_GL_DeleteContext(gl_context)
SDL.SDL_DestroyWindow(window)
SDL.SDL_Quit()
print("Done!")