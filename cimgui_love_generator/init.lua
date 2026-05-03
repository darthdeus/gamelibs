-- cimgui Lua FFI bindings (gamelibs build)
--
-- Generated from the cimgui submodule pinned in this repo and the cimgui-love
-- generator vendored under cimgui_love_generator/. The dynamic library shipped
-- alongside (libcimgui_complete.{so,dylib,dll}) is built from the same cimgui
-- SHA, so cdef + dylib are guaranteed to be in lockstep. See
-- cimgui_love_generator/README.md for regeneration instructions.

local path = (...):gsub(".init$", "") .. "."

require(path .. "cdef")

local M = require(path .. "master")
local ffi = require("ffi")

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

local ok, lib = pcall(ffi.load, lib_name)
if not ok then
    ok, lib = pcall(ffi.load, "cimgui_complete")
end
if not ok then
    error("Failed to load cimgui library: " .. tostring(lib) ..
          "\nEnsure the runtime library search path includes the gamelibs lib directory")
end

M.C = lib

require(path .. "enums")
require(path .. "wrap")

M._common = nil

return M
