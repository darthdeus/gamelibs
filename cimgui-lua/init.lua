-- Dear Imgui version: 1.88
-- Lua FFI bindings for cimgui (Dear ImGui C wrapper)
-- These bindings are based on cimgui-love, modified for Stone/Rock

local path = (...):gsub(".init$", "") .. "."

require(path .. "cdef")

local M = require(path .. "master")
local ffi = require("ffi")

-- Determine library name based on OS
local lib_name
if ffi.os == "Linux" then
    lib_name = "libcimgui_complete.so"
elseif ffi.os == "Windows" then
    lib_name = "cimgui_complete.dll"
elseif ffi.os == "OSX" then
    lib_name = "libcimgui_complete.dylib"
else
    error("Unsupported platform: " .. ffi.os)
end

-- Try to load the library - relies on LD_LIBRARY_PATH/DYLD_LIBRARY_PATH being set
-- by the rock runtime (which includes prebuilt/gamelibs-*/lib)
local ok, lib = pcall(ffi.load, lib_name)
if not ok then
    -- Fallback: try loading by name only (without extension)
    ok, lib = pcall(ffi.load, "cimgui_complete")
end
if not ok then
    error("Failed to load cimgui library: " .. tostring(lib) ..
          "\nMake sure LD_LIBRARY_PATH includes the prebuilt gamelibs lib directory")
end

M.C = lib

require(path .. "enums")
require(path .. "wrap")
require(path .. "shortcuts")

-- remove access to M._common
M._common = nil

return M
