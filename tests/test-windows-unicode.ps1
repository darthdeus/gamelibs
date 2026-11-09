param([Parameter(Mandatory=$true)][string]$Prefix)
$ErrorActionPreference = 'Stop'
$Prefix = (Resolve-Path $Prefix).Path
$work = Join-Path ([IO.Path]::GetTempPath()) ('luajit-unicode-' + [guid]::NewGuid())
New-Item -ItemType Directory "$work/bin", "$work/source", "$work/unrelated" | Out-Null
function Checked([scriptblock]$Command) {
    & $Command
    if ($LASTEXITCODE -ne 0) { throw "Command failed with exit $LASTEXITCODE" }
}
try {
    Copy-Item "$Prefix/bin/luajit.exe", "$Prefix/bin/lua51.dll" "$work/bin"
    '__declspec(dllexport) int fixture_dependency(void) { return 41; }' | Set-Content -Encoding ascii "$work/source/dep.c"
    @'
#include "lua.h"
__declspec(dllimport) int fixture_dependency(void);
__declspec(dllexport) int fixture_value(void) { return fixture_dependency() + 1; }
__declspec(dllexport) int luaopen_unicode_fixture(lua_State *L) {
  lua_pushinteger(L, fixture_value()); return 1;
}
'@ | Set-Content -Encoding ascii "$work/source/fixture.c"
    Push-Location "$work/source"
    try {
        Checked { cl /nologo /LD /MT dep.c /link /out:unicode_dep.dll /implib:unicode_dep.lib }
        Checked { cl /nologo /LD /MT "/I$Prefix/include" fixture.c /link "/libpath:$Prefix/lib" lua51.lib unicode_dep.lib /out:unicode_fixture.dll }
    } finally { Pop-Location }
    @'
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <assemblyIdentity type="win32" name="UnicodeLoaderTest" version="1.0.0.0"/>
  <application xmlns="urn:schemas-microsoft-com:asm.v3"><windowsSettings>
    <activeCodePage xmlns="http://schemas.microsoft.com/SMI/2019/WindowsSettings">UTF-8</activeCodePage>
  </windowsSettings></application>
</assembly>
'@ | Set-Content -Encoding ascii "$work/utf8.manifest"
    Copy-Item "$work/bin/luajit.exe" "$work/bin/luajit-utf8.exe"
    Checked { mt.exe -nologo -manifest "$work/utf8.manifest" "-outputresource:$work/bin/luajit-utf8.exe;#1" }
    # Each directory is outside the executable directory and the current directory.
    $names = @('space folder', ('accent-' + [char]0xc1), ('cjk-' + [char]0x6f22),
               ('cyrillic-' + [char]0x416), ('emoji-' + [char]::ConvertFromUtf32(0x1f680)))
    foreach ($name in $names) {
        $directory = Join-Path $work $name
        New-Item -ItemType Directory $directory | Out-Null
        Copy-Item "$work/source/unicode_*.dll" $directory
        $path = (Join-Path $directory 'unicode_fixture.dll').Replace('\','/')
        $encoded = ([Text.Encoding]::UTF8.GetBytes($path) | ForEach-Object { '\' + $_.ToString('000') }) -join ''
        @"
local ffi = require('ffi')
ffi.cdef[[int fixture_value(void); unsigned int GetACP(void);]]
local acp = tonumber(ffi.C.GetACP())
print('ANSI code page: ' .. acp)
assert((acp == 65001) == (arg[2] == 'utf8'), 'expected legacy and UTF-8 code page coverage')
local path = '$encoded'
if arg[1] == 'relocated' then
  assert(package.cpath:gsub(string.char(92), '/'):find(path:match('^(.*)/'), 1, true))
  assert(require('unicode_fixture') == 42)
end
local lib = ffi.load(path)
assert(lib.fixture_value() == 42)
local open = assert(package.loadlib(path, 'luaopen_unicode_fixture'))
assert(open() == 42)
assert(not pcall(function() return lib.missing_symbol end))
assert(not pcall(ffi.load, path .. '.missing'))
assert(not pcall(ffi.load, string.char(255) .. path))
lib, open = nil, nil
collectgarbage(); collectgarbage()
assert(ffi.load(path).fixture_value() == 42)
print('PASS Unicode native library and adjacent dependency')
"@ | Set-Content -Encoding ascii "$work/test.lua"
        Push-Location "$work/unrelated"
        try {
            foreach ($exe in @('luajit.exe','luajit-utf8.exe')) {
                Checked { & "$work/bin/$exe" "$work/test.lua" direct $(if ($exe -eq 'luajit-utf8.exe') { 'utf8' } else { 'legacy' }) }
            }
        } finally { Pop-Location }
        Copy-Item "$work/bin/luajit.exe", "$work/bin/lua51.dll" $directory
        Checked { & "$directory/luajit.exe" "$work/test.lua" relocated }
    }
    # A dependent DLL must not be borrowed from the current directory.
    $missing = Join-Path $work 'missing-dependency'
    New-Item -ItemType Directory $missing | Out-Null
    Copy-Item "$work/source/unicode_fixture.dll" $missing
    Copy-Item "$work/source/unicode_dep.dll" "$work/unrelated"
    $path = (Join-Path $missing 'unicode_fixture.dll').Replace('\','/')
    $encoded = ([Text.Encoding]::UTF8.GetBytes($path) | ForEach-Object { '\' + $_.ToString('000') }) -join ''
    "assert(not pcall(require('ffi').load, '$encoded')); print('PASS missing dependency')" | Set-Content -Encoding ascii "$work/test.lua"
    Push-Location "$work/unrelated"
    try { Checked { & "$work/bin/luajit.exe" "$work/test.lua" } } finally { Pop-Location }
} finally {
    Remove-Item -Recurse -Force $work
}
