local ffi = require("ffi")

-- SDL2 C definitions
ffi.cdef[[
    typedef struct SDL_Window SDL_Window;
    typedef struct SDL_Surface SDL_Surface;
    typedef enum {
        SDL_INIT_VIDEO = 0x00000020
    } SDL_InitFlag;
    
    typedef enum {
        SDL_WINDOWPOS_UNDEFINED = 0x1FFF0000,
        SDL_WINDOW_SHOWN = 0x00000004,
        SDL_WINDOW_OPENGL = 0x00000002
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
        SDL_KEYDOWN = 0x300
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
    
    // OpenGL context functions
    SDL_GLContext SDL_GL_CreateContext(SDL_Window* window);
    void SDL_GL_DeleteContext(SDL_GLContext context);
    int SDL_GL_SetSwapInterval(int interval);
    void SDL_GL_SwapWindow(SDL_Window* window);
    void* SDL_GL_GetProcAddress(const char* proc);
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
local glClear, glClearColor, glDrawArrays
local glCreateShader, glShaderSource, glCompileShader, glGetShaderiv
local glCreateProgram, glAttachShader, glLinkProgram, glUseProgram, glGetProgramiv
local glGenBuffers, glBindBuffer, glBufferData
local glGenVertexArrays, glBindVertexArray, glVertexAttribPointer, glEnableVertexAttribArray

-- Load SDL2 library from current directory
print("Loading local SDL2 library...")
local SDL = ffi.load("./bindings/libSDL2-2.0.so")

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
if SDL.SDL_Init(SDL.SDL_INIT_VIDEO) < 0 then
    error("Failed to initialize SDL")
end

-- Set hint to prevent window from grabbing focus
SDL.SDL_SetHint("SDL_HINT_WINDOW_NO_ACTIVATION_WHEN_SHOWN", "1")

-- Create window
print("Creating SDL window with OpenGL support...")
local window = SDL.SDL_CreateWindow(
    "Lua OpenGL Triangle",
    SDL.SDL_WINDOWPOS_UNDEFINED,
    SDL.SDL_WINDOWPOS_UNDEFINED,
    800, 600,
    bit.bor(SDL.SDL_WINDOW_SHOWN, SDL.SDL_WINDOW_OPENGL)
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

-- Load OpenGL functions
print("Loading OpenGL functions...")
glClear = ffi.cast("void (*)(unsigned int)", loadGLFunction("glClear"))
glClearColor = ffi.cast("void (*)(float, float, float, float)", loadGLFunction("glClearColor"))
glDrawArrays = ffi.cast("void (*)(unsigned int, int, int)", loadGLFunction("glDrawArrays"))
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

-- Enable VSync
SDL.SDL_GL_SetSwapInterval(1)

print("OpenGL triangle setup complete!")
print("Press Escape or close window to exit...")

-- Main event loop
local event = ffi.new("SDL_Event")
local running = true

while running do
    while SDL.SDL_PollEvent(event) ~= 0 do
        if event.type == SDL.SDL_QUIT then
            running = false
        elseif event.type == SDL.SDL_KEYDOWN then
            if event.key.sym == SDL.SDLK_ESCAPE then
                running = false
            end
        end
    end
    
    -- Render
    glClearColor(0.2, 0.3, 0.3, 1.0)
    glClear(GL_COLOR_BUFFER_BIT)
    
    glUseProgram(shaderProgram)
    glBindVertexArray(VAO[0])
    glDrawArrays(GL_TRIANGLES, 0, 3)
    
    SDL.SDL_GL_SwapWindow(window)
end

-- Cleanup
print("Cleaning up...")
SDL.SDL_GL_DeleteContext(gl_context)
SDL.SDL_DestroyWindow(window)
SDL.SDL_Quit()
print("Done!")
