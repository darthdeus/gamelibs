#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "lua.h"
#include "lauxlib.h"
#include "lualib.h"
#include "luajit-health.h"
static uint64_t count(lua_State *L, const char *key)
{
  uint64_t n;
  lua_getglobal(L,"test_callback_counts"); lua_getfield(L,-1,key);
  n=(uint64_t)lua_tonumber(L,-1); lua_pop(L,2); return n;
}
int main(int argc, char **argv)
{
  lua_State *L=luaL_newstate(); luaJIT_Health h;
  struct { luaJIT_HealthCoal ring[3]; uint64_t canary; } out;
  uint64_t aborts=0, i; int n;
  assert(argc==2); luaL_openlibs(L);
  assert(luaJIT_health_configure(L,1,2));
  if (luaL_dofile(L,argv[1])) { fprintf(stderr,"%s\n",lua_tostring(L,-1)); return 1; }
  assert(luaJIT_health_read(L,1,&h,sizeof(h)));
  assert(h.ring_next>64 && h.ring_overflow==h.ring_next-64);
  memset(&out,0,sizeof(out)); out.canary=12345;
  n=luaJIT_health_coalescing(L,1,0,out.ring,sizeof(out.ring[0]),3);
  assert(n==3 && out.canary==12345);
  for(i=0;i<3;i++) {
    luaJIT_HealthCoal *c=&out.ring[i];
    assert(c->sequence==h.ring_next-64+i && c->occurrences>1);
    assert(c->parent_uid>0 && c->parent>0 && c->subreason>=1 && c->subreason<=4);
    assert(c->snapshot_entries>=40 && c->slot_count+c->slots_truncated==c->snapshot_entries);
    assert(c->inherited>0 && c->failed_slot<c->snapshot_slots);
    if(c->subreason==1) assert(c->allow_fpr==0);
    assert(c->slots[c->slot_count-1].child_ref!=UINT32_MAX);
  }
  assert(luaJIT_health_coalescing(L,1,h.ring_next-1,out.ring,sizeof(out.ring[0]),1)==1);
  assert(h.emitted_mcode_bytes==count(L,"bytes"));
  lua_getglobal(L,"test_live"); assert(h.live_traces==(uint64_t)lua_tonumber(L,-1)); lua_pop(L,1);
  lua_getglobal(L,"test_live_bytes"); assert(h.live_mcode_bytes==(uint64_t)lua_tonumber(L,-1)); lua_pop(L,1);
  assert(luaJIT_health_coalescing(L,2,0,out.ring,sizeof(out.ring[0]),3)==-1);
  assert(luaJIT_health_coalescing(L,1,h.ring_next,out.ring,sizeof(out.ring[0]),3)==0);
  for(i=0;i<64;i++) aborts+=h.aborts[i];
  assert(h.root_starts+h.side_starts==count(L,"start"));
  assert(h.root_compiles+h.side_compiles==count(L,"stop"));
  assert(aborts==count(L,"abort") && h.flushes==count(L,"flush"));
  printf("PASS coalescing first examples/repeats/context/truncation/overflow/cursor; callbacks agree: starts=%llu compiles=%llu aborts=%llu ring=%llu overflow=%llu\n",(unsigned long long)(h.root_starts+h.side_starts),(unsigned long long)(h.root_compiles+h.side_compiles),(unsigned long long)aborts,(unsigned long long)h.ring_next,(unsigned long long)h.ring_overflow);
  lua_close(L); return 0;
}
