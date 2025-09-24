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

    // Surface functions for screenshots
    typedef struct SDL_Surface {
        uint32_t flags;
        void* format;
        int w, h;
        int pitch;
        void* pixels;
        void* userdata;
        int locked;
        void* lock_data;
        void* clip_rect;
        void* map;
        int refcount;
    } SDL_Surface;

    SDL_Surface* SDL_CreateRGBSurfaceWithFormat(uint32_t flags, int width, int height, int depth, uint32_t format);
    void SDL_FreeSurface(SDL_Surface* surface);

    // File I/O
    typedef struct SDL_RWops SDL_RWops;
    SDL_RWops* SDL_RWFromFile(const char* file, const char* mode);
    int SDL_SaveBMP_RW(SDL_Surface* surface, SDL_RWops* dst, int freedst);
    int SDL_RWclose(SDL_RWops* ctx);
]]

-- FreeType C definitions
ffi.cdef[[
    typedef struct FT_LibraryRec_* FT_Library;
    typedef struct FT_FaceRec_* FT_Face;
    typedef int FT_Error;
    typedef long FT_Long;
    typedef unsigned long FT_ULong;
    typedef int FT_Int;
    typedef unsigned int FT_UInt;
    typedef int FT_Int32;
    typedef short FT_Short;
    typedef unsigned short FT_UShort;
    typedef signed long FT_Pos;
    typedef signed long FT_Fixed;
    typedef signed long FT_F26Dot6;

    typedef struct FT_Vector_ {
        FT_Pos x;
        FT_Pos y;
    } FT_Vector;

    typedef struct FT_BBox_ {
        FT_Pos xMin, yMin;
        FT_Pos xMax, yMax;
    } FT_BBox;

    typedef struct FT_Bitmap_ {
        unsigned int rows;
        unsigned int width;
        int pitch;
        unsigned char* buffer;
        unsigned short num_grays;
        unsigned char pixel_mode;
        unsigned char palette_mode;
        void* palette;
    } FT_Bitmap;

    typedef struct FT_Glyph_Metrics_ {
        FT_Pos width;
        FT_Pos height;
        FT_Pos horiBearingX;
        FT_Pos horiBearingY;
        FT_Pos horiAdvance;
        FT_Pos vertBearingX;
        FT_Pos vertBearingY;
        FT_Pos vertAdvance;
    } FT_Glyph_Metrics;

    typedef struct FT_GlyphSlotRec_* FT_GlyphSlot;

    typedef struct FT_GlyphSlotRec_ {
        FT_Library library;
        FT_Face face;
        FT_GlyphSlot next;
        FT_UInt glyph_index;
        FT_ULong generic_generic;
        void* generic_data;
        FT_Glyph_Metrics metrics;
        FT_Fixed linearHoriAdvance;
        FT_Fixed linearVertAdvance;
        FT_Vector advance;
        int format;
        FT_Bitmap bitmap;
        FT_Int bitmap_left;
        FT_Int bitmap_top;
        // ... more fields we don't need
    } FT_GlyphSlotRec;

    typedef struct FT_Size_Metrics_ {
        FT_UShort x_ppem;
        FT_UShort y_ppem;
        FT_Fixed x_scale;
        FT_Fixed y_scale;
        FT_Pos ascender;
        FT_Pos descender;
        FT_Pos height;
        FT_Pos max_advance;
    } FT_Size_Metrics;

    typedef struct FT_SizeRec_* FT_Size;

    typedef struct FT_FaceRec_ {
        FT_Long num_faces;
        FT_Long face_index;
        FT_Long face_flags;
        FT_Long style_flags;
        FT_Long num_glyphs;
        char* family_name;
        char* style_name;
        FT_Int num_fixed_sizes;
        void* available_sizes;
        FT_Int num_charmaps;
        void* charmaps;
        void* generic_data;
        void* generic_destructor;
        FT_BBox bbox;
        FT_UShort units_per_EM;
        FT_Short ascender;
        FT_Short descender;
        FT_Short height;
        FT_Short max_advance_width;
        FT_Short max_advance_height;
        FT_Short underline_position;
        FT_Short underline_thickness;
        FT_GlyphSlot glyph;
        FT_Size size;
        void* charmap;
        // ... more fields
    } FT_FaceRec;

    // FreeType functions
    FT_Error FT_Init_FreeType(FT_Library* library);
    FT_Error FT_New_Face(FT_Library library, const char* filepathname, FT_Long face_index, FT_Face* aface);
    FT_Error FT_New_Memory_Face(FT_Library library, const unsigned char* file_base, FT_Long file_size, FT_Long face_index, FT_Face* aface);
    FT_Error FT_Set_Pixel_Sizes(FT_Face face, FT_UInt pixel_width, FT_UInt pixel_height);
    FT_Error FT_Set_Char_Size(FT_Face face, FT_F26Dot6 char_width, FT_F26Dot6 char_height, FT_UInt horz_resolution, FT_UInt vert_resolution);
    FT_UInt FT_Get_Char_Index(FT_Face face, FT_ULong charcode);
    FT_Error FT_Load_Glyph(FT_Face face, FT_UInt glyph_index, FT_Int32 load_flags);
    FT_Error FT_Load_Char(FT_Face face, FT_ULong char_code, FT_Int32 load_flags);
    FT_Error FT_Render_Glyph(FT_GlyphSlot slot, int render_mode);
    FT_Error FT_Done_Face(FT_Face face);
    FT_Error FT_Done_FreeType(FT_Library library);

    // Load flags
    static const int FT_LOAD_DEFAULT = 0;
    static const int FT_LOAD_RENDER = 4;

    // Render modes
    static const int FT_RENDER_MODE_NORMAL = 0;
    static const int FT_RENDER_MODE_MONO = 1;
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
    bool igSliderInt(const char* label, int* v, int v_min, int v_max, const char* format, int flags);
    bool igColorEdit3(const char* label, float col[3], int flags);
    bool igCheckbox(const char* label, bool* v);
    void igSeparator(void);

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
local GL_DYNAMIC_DRAW = 0x88E8
local GL_FLOAT = 0x1406
local GL_FALSE = 0
local GL_TEXTURE_2D = 0x0DE1
local GL_TEXTURE0 = 0x84C0
local GL_UNSIGNED_BYTE = 0x1401
local GL_RED = 0x1903
local GL_ALPHA = 0x1906
local GL_TEXTURE_MIN_FILTER = 0x2801
local GL_TEXTURE_MAG_FILTER = 0x2800
local GL_LINEAR = 0x2601
local GL_TEXTURE_WRAP_S = 0x2802
local GL_TEXTURE_WRAP_T = 0x2803
local GL_CLAMP_TO_EDGE = 0x812F
local GL_BLEND = 0x0BE2
local GL_SRC_ALPHA = 0x0302
local GL_ONE_MINUS_SRC_ALPHA = 0x0303
local GL_UNPACK_ALIGNMENT = 0x0CF5
local GL_RGBA = 0x1908
local GL_PACK_ALIGNMENT = 0x0D05

-- OpenGL function pointers
local glClear, glClearColor, glDrawArrays, glViewport
local glCreateShader, glShaderSource, glCompileShader, glGetShaderiv
local glCreateProgram, glAttachShader, glLinkProgram, glUseProgram, glGetProgramiv
local glGenBuffers, glBindBuffer, glBufferData
local glGenVertexArrays, glBindVertexArray, glVertexAttribPointer, glEnableVertexAttribArray
local glGenTextures, glBindTexture, glTexImage2D, glTexParameteri, glActiveTexture
local glEnable, glBlendFunc, glDisable
local glGetUniformLocation, glUniform1i, glUniformMatrix4fv

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

-- Load FreeType
print("Loading FreeType...")
local ft = ffi.load(lib_path .. "/lib/libfreetype" .. lib_ext)

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
glBufferSubData = ffi.cast("void (*)(unsigned int, long, long, const void*)", loadGLFunction("glBufferSubData"))
glPixelStorei = ffi.cast("void (*)(unsigned int, int)", loadGLFunction("glPixelStorei"))
glGenVertexArrays = ffi.cast("void (*)(int, unsigned int*)", loadGLFunction("glGenVertexArrays"))
glBindVertexArray = ffi.cast("void (*)(unsigned int)", loadGLFunction("glBindVertexArray"))
glVertexAttribPointer = ffi.cast("void (*)(unsigned int, int, unsigned int, unsigned char, int, const void*)", loadGLFunction("glVertexAttribPointer"))
glEnableVertexAttribArray = ffi.cast("void (*)(unsigned int)", loadGLFunction("glEnableVertexAttribArray"))
glGenTextures = ffi.cast("void (*)(int, unsigned int*)", loadGLFunction("glGenTextures"))
glBindTexture = ffi.cast("void (*)(unsigned int, unsigned int)", loadGLFunction("glBindTexture"))
glTexImage2D = ffi.cast("void (*)(unsigned int, int, int, int, int, int, unsigned int, unsigned int, const void*)", loadGLFunction("glTexImage2D"))
glTexParameteri = ffi.cast("void (*)(unsigned int, unsigned int, int)", loadGLFunction("glTexParameteri"))
glActiveTexture = ffi.cast("void (*)(unsigned int)", loadGLFunction("glActiveTexture"))
glEnable = ffi.cast("void (*)(unsigned int)", loadGLFunction("glEnable"))
glDisable = ffi.cast("void (*)(unsigned int)", loadGLFunction("glDisable"))
glBlendFunc = ffi.cast("void (*)(unsigned int, unsigned int)", loadGLFunction("glBlendFunc"))
local glReadPixels = ffi.cast("void (*)(int, int, int, int, unsigned int, unsigned int, void*)", loadGLFunction("glReadPixels"))
glGetUniformLocation = ffi.cast("int (*)(unsigned int, const char*)", loadGLFunction("glGetUniformLocation"))
glUniform1i = ffi.cast("void (*)(int, int)", loadGLFunction("glUniform1i"))
glUniform3f = ffi.cast("void (*)(int, float, float, float)", loadGLFunction("glUniform3f"))
glUniformMatrix4fv = ffi.cast("void (*)(int, int, unsigned char, const float*)", loadGLFunction("glUniformMatrix4fv"))

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

-- Initialize FreeType
print("Initializing FreeType...")
local ft_library = ffi.new("FT_Library[1]")
if ft.FT_Init_FreeType(ft_library) ~= 0 then
    error("Failed to initialize FreeType")
end

-- Load a font (try to find a system font)
local font_paths = {
    "/usr/share/fonts/TTF/FantasqueSansMono-Regular.ttf",  -- Arch Linux
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Helvetica.ttc",  -- macOS
    "C:/Windows/Fonts/arial.ttf",  -- Windows
    "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
}

local ft_face = ffi.new("FT_Face[1]")
local font_loaded = false

for _, path in ipairs(font_paths) do
    local file = io.open(path, "r")
    if file then
        file:close()
        if ft.FT_New_Face(ft_library[0], path, 0, ft_face) == 0 then
            print("Loaded font: " .. path)
            font_loaded = true
            break
        end
    end
end

if not font_loaded then
    print("Warning: Could not load a system font")
end

-- Initial font rasterization size
local raster_size = ffi.new("int[1]", 48)
if font_loaded then
    ft.FT_Set_Pixel_Sizes(ft_face[0], 0, raster_size[0])
end

-- Shader source code for triangle
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

-- Shader source code for text rendering
-- NOTE: We use Y-up coordinate system (OpenGL default)
-- Positive Y goes upward, origin at center of screen
-- Text baseline calculations assume Y-up
local textVertexShaderSource = [[
#version 330 core
layout (location = 0) in vec4 vertex;
out vec2 TexCoord;
void main()
{
    gl_Position = vec4(vertex.xy, 0.0, 1.0);
    TexCoord = vertex.zw;
}
]]

local textFragmentShaderSource = [[
#version 330 core
in vec2 TexCoord;
out vec4 FragColor;
uniform sampler2D text;
uniform vec3 textColor;
void main()
{
    vec4 sampled = vec4(1.0, 1.0, 1.0, texture(text, TexCoord).r);
    FragColor = vec4(textColor, 1.0) * sampled;
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

-- Create text shader program
local textVertexShader = glCreateShader(GL_VERTEX_SHADER)
local textVertexSourcePtr = ffi.new("const char*[1]")
textVertexSourcePtr[0] = textVertexShaderSource
glShaderSource(textVertexShader, 1, textVertexSourcePtr, nil)
glCompileShader(textVertexShader)

glGetShaderiv(textVertexShader, GL_COMPILE_STATUS, success)
if success[0] == GL_FALSE then
    error("Failed to compile text vertex shader")
end

local textFragmentShader = glCreateShader(GL_FRAGMENT_SHADER)
local textFragmentSourcePtr = ffi.new("const char*[1]")
textFragmentSourcePtr[0] = textFragmentShaderSource
glShaderSource(textFragmentShader, 1, textFragmentSourcePtr, nil)
glCompileShader(textFragmentShader)

glGetShaderiv(textFragmentShader, GL_COMPILE_STATUS, success)
if success[0] == GL_FALSE then
    error("Failed to compile text fragment shader")
end

local textShaderProgram = glCreateProgram()
glAttachShader(textShaderProgram, textVertexShader)
glAttachShader(textShaderProgram, textFragmentShader)
glLinkProgram(textShaderProgram)

glGetProgramiv(textShaderProgram, GL_LINK_STATUS, success)
if success[0] == GL_FALSE then
    error("Failed to link text shader program")
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

-- Create text rendering VAO and VBO
local textVAO = ffi.new("unsigned int[1]")
local textVBO = ffi.new("unsigned int[1]")

glGenVertexArrays(1, textVAO)
glGenBuffers(1, textVBO)

glBindVertexArray(textVAO[0])
glBindBuffer(GL_ARRAY_BUFFER, textVBO[0])

-- Reserve space for a quad (2 triangles, 6 vertices, 4 floats each: x,y,u,v)
glBufferData(GL_ARRAY_BUFFER, 6 * 4 * ffi.sizeof("float"), nil, GL_DYNAMIC_DRAW)

-- Setup vertex attribute (position and texture coordinates combined)
glEnableVertexAttribArray(0)
glVertexAttribPointer(0, 4, GL_FLOAT, GL_FALSE, 4 * ffi.sizeof("float"), nil)

glBindBuffer(GL_ARRAY_BUFFER, 0)
glBindVertexArray(0)

-- Create texture for text
local textTexture = ffi.new("unsigned int[1]")

print("Setup complete!")
print("Using libraries from: " .. lib_path)
print("Press Escape or close window to exit...")

-- Unused function - kept for reference, should be removed or integrated with texture atlas approach
-- local function renderChar(char, x, y, scale)
--     -- Function body removed for code cleanliness
-- end

-- ImGui demo window state
local show_demo = ffi.new("bool[1]", false)  -- Hidden for debugging
local show_another = ffi.new("bool[1]", false)
local clear_color = ffi.new("float[3]", {0.2, 0.3, 0.3})
local counter = 0
local slider_value = ffi.new("float[1]", 0.5)
local checkbox_value = ffi.new("bool[1]", false)

-- FPS tracking
local frame_count = 0
local last_time = SDL.SDL_GetTicks()
local fps = 0.0

-- Screenshot tracking
local total_frames = 0
local screenshot_taken = false

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

    -- Create a custom window with FreeType controls
    if imgui.igBegin("FreeType Controls", nil, 0) then
        -- FreeType rasterization controls
        imgui.igText("FreeType Text Rendering")
        imgui.igSeparator()

        if font_loaded then
            local face = ft_face[0]
            imgui.igText(string.format("Font: %s", ffi.string(face.family_name or "Unknown")))

            -- Rasterization size slider
            if imgui.igSliderInt("Raster Size", raster_size, 12, 200, "%d pixels", 0) then
                -- Re-set the pixel size when slider changes
                ft.FT_Set_Pixel_Sizes(ft_face[0], 0, raster_size[0])
            end

            imgui.igText(string.format("Current: %dx%d pixels", raster_size[0], raster_size[0]))
            imgui.igText("Tip: Higher = sharper text")
        else
            imgui.igText("FreeType: No font loaded")
        end

        imgui.igSeparator()
        imgui.igColorEdit3("Background", clear_color, 0)
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

    -- Draw FreeType text
    if font_loaded then
        -- Enable blending for text
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        -- Setup text shader
        glUseProgram(textShaderProgram)

        -- Set text color uniform (white)
        local textColorLoc = glGetUniformLocation(textShaderProgram, "textColor")
        glUniform3f(textColorLoc, 1.0, 1.0, 1.0)

        -- Bind texture uniform
        local textureLoc = glGetUniformLocation(textShaderProgram, "text")
        glUniform1i(textureLoc, 0)

        -- Render text string
        -- TODO: Optimize text rendering with texture atlas to avoid per-character texture uploads
        -- Current implementation re-uploads texture for every character which is inefficient
        local text = "Hello FreeType!"
        local text_x = -0.8  -- Use a different variable name
        local text_y = -0.2
        -- Scale based on rasterization size to maintain consistent visual size
        -- Target visual size: about 48 pixels, adjust based on actual raster size
        local scale = 0.003 * (48.0 / raster_size[0])

        for i = 1, #text do
            local char = text:sub(i,i)
            if char == " " then
                text_x = text_x + 0.02  -- Space width (adjusted for scale)
            else
                -- Load and render character
                if ft.FT_Load_Char(ft_face[0], string.byte(char), ft.FT_LOAD_RENDER) == 0 then
                    local glyph = ft_face[0].glyph
                    local bitmap = glyph.bitmap

                    if bitmap.width > 0 and bitmap.rows > 0 then
                        -- Generate or reuse texture
                        if textTexture[0] == 0 then
                            glGenTextures(1, textTexture)
                        end
                        glBindTexture(GL_TEXTURE_2D, textTexture[0])

                        -- Upload glyph bitmap to texture
                        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
                        glTexImage2D(GL_TEXTURE_2D, 0, GL_RED, bitmap.width, bitmap.rows,
                                     0, GL_RED, GL_UNSIGNED_BYTE, bitmap.buffer)

                        -- Set texture parameters
                        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
                        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
                        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
                        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

                        -- Calculate size and position with proper baseline
                        local w = bitmap.width * scale
                        local h = bitmap.rows * scale
                        local xpos = text_x + glyph.bitmap_left * scale
                        local ypos = text_y - (bitmap.rows - glyph.bitmap_top) * scale

                        -- Update VBO with quad for this character
                        -- Keep original texture coordinates (no flip)
                        local quadVertices = ffi.new("float[24]", {
                            -- positions           -- texture coords
                            xpos,     ypos + h,    0.0, 0.0,  -- top left
                            xpos,     ypos,        0.0, 1.0,  -- bottom left
                            xpos + w, ypos,        1.0, 1.0,  -- bottom right

                            xpos,     ypos + h,    0.0, 0.0,  -- top left
                            xpos + w, ypos,        1.0, 1.0,  -- bottom right
                            xpos + w, ypos + h,    1.0, 0.0   -- top right
                        })

                        glBindBuffer(GL_ARRAY_BUFFER, textVBO[0])
                        glBufferSubData(GL_ARRAY_BUFFER, 0, ffi.sizeof(quadVertices), quadVertices)

                        -- Draw this character immediately
                        glActiveTexture(GL_TEXTURE0)
                        glBindTexture(GL_TEXTURE_2D, textTexture[0])
                        glBindVertexArray(textVAO[0])
                        glDrawArrays(GL_TRIANGLES, 0, 6)

                        -- Move to next character position
                        -- advance.x is in 26.6 fixed-point format (1/64 pixels)
                        local advance_pixels = tonumber(glyph.advance.x) / 64
                        text_x = text_x + advance_pixels * scale

                    end
                end
            end
        end

        glDisable(GL_BLEND)
    end

    imgui.cImGui_ImplOpenGL3_RenderDrawData(imgui.igGetDrawData())

    -- Take screenshot on 5th frame
    total_frames = total_frames + 1
    if total_frames == 5 and not screenshot_taken then
        screenshot_taken = true

        -- Get window size
        local w = ffi.new("int[1]")
        local h = ffi.new("int[1]")
        SDL.SDL_GetWindowSize(window, w, h)
        local width = w[0]
        local height = h[0]

        -- Allocate buffer for pixels
        local pixels = ffi.new("uint8_t[?]", width * height * 4)

        -- Read pixels from OpenGL framebuffer
        glPixelStorei(GL_PACK_ALIGNMENT, 1)
        glReadPixels(0, 0, width, height, GL_RGBA, GL_UNSIGNED_BYTE, pixels)

        -- Create SDL surface (note: OpenGL pixels are upside down)
        local surface = SDL.SDL_CreateRGBSurfaceWithFormat(0, width, height, 32, 0x16762004) -- SDL_PIXELFORMAT_ABGR8888

        if surface ~= nil then
            -- Copy pixels to surface (flip vertically)
            local surface_pixels = ffi.cast("uint8_t*", surface.pixels)
            for y = 0, height - 1 do
                for x = 0, width - 1 do
                    local src_idx = ((height - 1 - y) * width + x) * 4
                    local dst_idx = (y * width + x) * 4
                    surface_pixels[dst_idx] = pixels[src_idx]       -- R
                    surface_pixels[dst_idx + 1] = pixels[src_idx + 1] -- G
                    surface_pixels[dst_idx + 2] = pixels[src_idx + 2] -- B
                    surface_pixels[dst_idx + 3] = pixels[src_idx + 3] -- A
                end
            end

            -- Convert to PNG using stb_image_write or save as BMP
            -- For now, save as BMP then convert
            local rw = SDL.SDL_RWFromFile("screenshot.bmp", "wb")
            if rw ~= nil then
                SDL.SDL_SaveBMP_RW(surface, rw, 1) -- 1 means close the RW after saving
                print("Screenshot saved as screenshot.bmp")
            else
                print("Failed to open file for writing")
            end

            -- Convert BMP to PNG using ImageMagick if available
            os.execute("convert screenshot.bmp screenshot.png 2>/dev/null && rm screenshot.bmp && echo 'Converted to screenshot.png' || echo 'PNG conversion failed, kept as BMP'")

            SDL.SDL_FreeSurface(surface)
        else
            print("Failed to create surface for screenshot")
        end
    end

    SDL.SDL_GL_SwapWindow(window)
end

-- Cleanup
print("Cleaning up...")
imgui.cImGui_ImplOpenGL3_Shutdown()
imgui.cImGui_ImplSDL2_Shutdown()
imgui.igDestroyContext(nil)

if font_loaded then
    ft.FT_Done_Face(ft_face[0])
end
ft.FT_Done_FreeType(ft_library[0])

SDL.SDL_GL_DeleteContext(gl_context)
SDL.SDL_DestroyWindow(window)
SDL.SDL_Quit()
print("Done!")