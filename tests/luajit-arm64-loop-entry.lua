-- Run with JIT enabled: luajit tests/luajit-arm64-loop-entry.lua
assert(jit.status())
for _, width in ipairs({31, 32, 33, 48}) do
  local src, names = {"local iters = ..."}, {}
  for i = 1, width do
    names[i] = "v" .. i
    src[#src+1] = ("local v%d = %d.5"):format(i, i)
  end
  src[#src+1] = "local acc = 0.0; for i = 1, iters do"
  for _, name in ipairs(names) do
    src[#src+1] = ("%s = %s * 1.000001 + 0.0000001"):format(name, name)
  end
  src[#src+1] = "if i % 997 == 0 then acc = acc + " .. table.concat(names, " + ")
      .. " end end return acc"
  local loop = assert(loadstring(table.concat(src, "\n"), "=wide-float-loop"))
  jit.off(loop)
  local expected = loop(2000)
  jit.on(loop)
  local actual = loop(2000)
  assert(actual == expected, ("width %d: JIT %.17g, interpreter %.17g")
      :format(width, actual, expected))
end
