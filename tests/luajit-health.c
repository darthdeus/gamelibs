#define _GNU_SOURCE
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <dlfcn.h>
#include "lua.h"
#include "lauxlib.h"
#include "lualib.h"
#include "luajit-health.h"
static unsigned calls;
struct allocator { lua_Alloc f; void *ud; };
static void *count_alloc(void *ud, void *p, size_t old, size_t n)
{
  struct allocator *a = (struct allocator *)ud;
  calls++;
  return a->f(a->ud, p, old, n);
}
static void run(lua_State *L, const char *s) { if (luaL_dostring(L,s)) { fprintf(stderr,"%s\n",lua_tostring(L,-1)); assert(0); } }
int main(void)
{
  int (*readstats)(lua_State *,uint32_t,void *,size_t) = dlsym(RTLD_DEFAULT,"luaJIT_health_read");
  assert(readstats && "native health capability absent");
  lua_State *L = luaL_newstate(), *other = luaL_newstate();
  luaJIT_Health a, b, isolated;
  luaL_openlibs(L);
  memset(&a,0x5a,sizeof(a)); b=a;
  assert(!readstats(L,2,&a,sizeof(a)) && !memcmp(&a,&b,sizeof(a)));
  assert(!readstats(L,1,&a,sizeof(a)-1) && !memcmp(&a,&b,sizeof(a)));
  assert(readstats(L,1,&a,sizeof(a)) && (a.capabilities&7)==7);
  int (*configure)(lua_State *,uint32_t,uint32_t) = dlsym(RTLD_DEFAULT,"luaJIT_health_configure");
  int (*category)(lua_State *) = dlsym(RTLD_DEFAULT,"luaJIT_vmcategory");
  int (*ring)(lua_State *,uint32_t,uint64_t,void *,size_t,uint32_t) = dlsym(RTLD_DEFAULT,"luaJIT_health_coalescing");
  assert(configure && category && ring && category(L)==0);
  assert(configure(L,1,2) && !configure(L,1,8));
  run(L,"jit.opt.start('hotloop=2','hotexit=1'); local x=0; for j=1,80 do for i=1,100 do if i%3==0 then x=x+i else x=x-i end end end; _G.x=x");
  assert(readstats(L,1,&b,sizeof(b)));
  assert(b.root_starts>a.root_starts && b.root_compiles>a.root_compiles);
  assert(b.side_starts>a.side_starts && b.side_compiles>a.side_compiles);
  assert(b.emitted_mcode_bytes>0 && b.live_traces>0 && b.arena_bytes>0);
  assert(b.arena_occupied_bytes<=b.arena_bytes && b.code_reserved_bytes<=b.arena_bytes);
  run(L,"for j=1,60 do for i=1,100 do local f=function() return i end; _G.x=f() end end");
  assert(readstats(L,1,&a,sizeof(a))); unsigned i; uint64_t aborts=0;
  for(i=0;i<64;i++) aborts+=a.aborts[i];
  assert(aborts>0);
  void *ud; lua_Alloc f=lua_getallocf(L,&ud);
  struct allocator allocdata = {f, ud};
  lua_setallocf(L,count_alloc,&allocdata); calls=0;
  for(i=0;i<1000;i++) assert(readstats(L,1,&b,sizeof(b)));
  assert(calls==0); lua_setallocf(L,f,ud);
  run(L,"jit.flush()"); assert(readstats(L,1,&b,sizeof(b)));
  assert(b.flushes>a.flushes && b.generation==a.generation+1);
  assert(b.emitted_mcode_bytes>=a.emitted_mcode_bytes && b.live_traces==0 && b.arena_bytes==0);
  assert(readstats(other,1,&isolated,sizeof(isolated)) && isolated.root_starts==0 && isolated.emitted_mcode_bytes==0);
  lua_close(other); lua_close(L);
  L=luaL_newstate(); assert(readstats(L,1,&b,sizeof(b)) && b.root_starts==0 && b.ring_overflow==0); lua_close(L);
  puts("PASS health ABI/version/size, root+side, aborts, flush, nonallocation, VM isolation/lifetimes");
  return 0;
}
