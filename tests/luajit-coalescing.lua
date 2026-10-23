-- Preserve a real caller snapshot: 40 floating values live across a guard.
-- Each separately loaded function supplies a distinct parent identity.
jit.off(debug.getinfo(1, 'f').func, true)
jit.opt.start('hotloop=2', 'hotexit=1', 'maxtrace=4000')
local function witness(width)
  local src = {'return function(t,n) local acc=0; for i=1,n do local x=t[i]'}
  local names = {}
  for k=1,width do
    names[k] = 'v'..k
    src[#src+1] = 'local v'..k..'=x+'..k..'.5'
  end
  src[#src+1] = 'if x>120 then acc=acc+1 end'
  src[#src+1] = 'acc=acc+'..table.concat(names,'+')..'; end; return acc; end'
  local f = assert(loadstring(table.concat(src,'\n')))()
  local t = {}; for i=1,1000 do t[i]=i%150 end
  local result=0; for rep=1,3 do result=result+f(t,1000) end
  assert(result>0)
end
local counts={start=0,stop=0,abort=0,flush=0,bytes=0}
local util=require("jit.util")
local function cb(what, trace)
  counts[what]=counts[what]+1
  if what=='stop' then counts.bytes=counts.bytes+#util.tracemc(trace) end
end
jit.attach(cb,'trace')
for i=1,70 do witness(40) end
jit.attach(cb)
_G.test_callback_counts=counts
local live, bytes=0,0
for i=1,4000 do
  if util.traceinfo(i) then live=live+1; bytes=bytes+#util.tracemc(i) end
end
_G.test_live=live
_G.test_live_bytes=bytes
