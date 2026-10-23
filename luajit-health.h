/* Rock LuaJIT health ABI. All operations run on the owning VM thread.
 * No allocation, callbacks or I/O. Version/size mismatch returns 0 without
 * writing. Counters last for one VM lifetime; flushes do not reset them.
 * Build identity is the upstream SHA plus the gamelibs patch schema.
 */
#ifndef LUAJIT_HEALTH_H
#define LUAJIT_HEALTH_H
#include "lua.h"
#include <stdint.h>
#define LUAJIT_HEALTH_VERSION 1
#define LUAJIT_HEALTH_COUNTERS 1
#define LUAJIT_HEALTH_COALESCING 2
#define LUAJIT_HEALTH_VMCATEGORY 4
#define LUAJIT_HEALTH_REASONS 64
#define LUAJIT_HEALTH_RING 64
#define LUAJIT_HEALTH_SLOTS 64
/* reason index is the pinned lj_traceerr.h ordinal (also jit.vmdef.traceerr).
 * Root includes stitched traces (J->parent == 0), matching trace-start ABI.
 * Live means published trace objects, including unlinked roots, until GC/free.
 * emitted_mcode_bytes sums successful trace szmcode, never decremented.
 * arena_bytes includes MCLink/unwind metadata, stubs and fragmentation.
 * arena_occupied_bytes excludes unused gaps, includes metadata and exit stubs.
 * code_reserved_bytes excludes per-arena MCLink/unwind metadata.
 * code_current_free_bytes is the only immediately reservable code span.
 */
typedef struct luaJIT_Health {
  uint32_t version, size;
  uint64_t capabilities;
  char build_id[64];
  uint64_t root_starts, side_starts, root_compiles, side_compiles;
  uint64_t aborts[LUAJIT_HEALTH_REASONS];
  uint64_t flushes, generation, emitted_mcode_bytes;
  uint64_t live_traces, live_mcode_bytes;
  uint64_t arena_bytes, arena_occupied_bytes, code_reserved_bytes;
  uint64_t code_current_free_bytes, ring_next, ring_overflow;
} luaJIT_Health;
/* 1=no reload register, 2=no GPR cycle temp, 3=no FPR cycle temp,
 * 4=inherited slot limit. Registers/masks use the target's lj_target.h IDs.
 * Slots are parent snapshot slots; child_ref/type/reg/spill describe the
 * matching inherited SLOAD, or UINT32_MAX when none exists. Context is the
 * first example of a (parent UID, exit, subreason, failed IR) signature.
 * occurrence count updates while retained. Overwrites count in ring_overflow.
 * Numeric proto addresses are opaque observations, never dereference later.
 */
typedef struct luaJIT_HealthSlot {
  uint32_t slot, parent_ref, parent_regsp, child_ref;
  uint32_t child_type, child_reg, child_spill, flags;
} luaJIT_HealthSlot;
typedef struct luaJIT_HealthCoal {
  uint64_t sequence, occurrences, generation, parent_uid;
  uint64_t start_proto, failure_proto;
  uint64_t allow_gpr, allow_fpr, free_gpr, free_fpr, live_gpr, live_fpr;
  uint32_t parent, exitno, subreason, start_pc, failure_pc;
  int32_t framedepth;
  uint32_t baseslot, maxslot, snapshot, snapshot_entries;
  uint32_t snapshot_slots, inherited, failed_ref, failed_slot;
  uint32_t failed_type, parent_regsp, target_reg, target_spill;
  uint32_t slot_count, slots_truncated;
  luaJIT_HealthSlot slots[LUAJIT_HEALTH_SLOTS];
} luaJIT_HealthCoal;
/* Configure flags: 0 counters only, COALESCING enables details. Never resets.
 * Enabling details reserves one fixed native ring; configure may return 0
 * on allocation failure. Reads and compiler hooks never allocate.
 * read_coalescing copies retained entries from sequence >= first, oldest first.
 * It does not drain: callers may reread to see occurrences. Snapshot ring_next
 * and ring_overflow expose sequence gaps/overwrites. No lifecycle/exit ring.
 * vmcategory: 0 mutator, 1 JIT compiler, 2 collector; -1 ABI unavailable.
 */
LUA_API int luaJIT_health_read(lua_State *L, uint32_t version, void *out, size_t size);
LUA_API int luaJIT_health_configure(lua_State *L, uint32_t version, uint32_t flags);
LUA_API int luaJIT_health_coalescing(lua_State *L, uint32_t version, uint64_t first,
                                   void *out, size_t stride, uint32_t capacity);
LUA_API int luaJIT_vmcategory(lua_State *L);
#endif
