LuaJIT native health tests run against a local Linux x86_64 installation:

```bash
./apply-luajit-patches.sh
make -C luajit -j8 PREFIX="$PWD/prebuilt/linux/x86_64"
make -C luajit install PREFIX="$PWD/prebuilt/linux/x86_64"
./tests/test-luajit-health.sh "$PWD/prebuilt/linux/x86_64"
```

The public contract is `luajit-health.h`, installed beside `luajit.h`.
The source remains pinned to upstream a4c064539ea931274d407e1249b4bb575424a0f4.
`patches/luajit-health.patch` carries the gamelibs changes. Local and CI LuaJIT
builds apply it; CI keys include the patch, header and applicator. This does
not publish a release. Rock's v0.6.11 binary does not have the capability.

All reads require the owning VM thread. Snapshot and ring reads allocate
nothing and never call Lua. Counters are always active and increment only at
trace compiler lifecycle seams. Coalescing details are off by default;
explicit configuration allocates one fixed native ring, freed at VM close.
Hooks never allocate, format strings, log, or call back into Lua.

`flushes`/`generation` count successful whole-VM flushes, matching the trace
callback's flush event. Selective root unlinking does not free code or trace
objects and does not increment generation. Starts and final aborts match trace
events; internal assembler retries do not count as aborts. Stitched traces
are classified as roots, matching the compiler's zero-parent convention.
`live_traces` counts published objects until GC or a whole-VM flush, including
selectively unlinked roots. `live_mcode_bytes` sums their trace code sizes.
Emitted bytes are cumulative successful trace code, distinct from arena
occupancy and from code/stub bytes retained after trace metadata collection.

The ring keeps first examples per parent compile UID, exit, subreason and
failed IR reference; retained signatures accumulate occurrences. Overwriting
an old signature increments overflow. Reads are nondestructive, in sequence
order, and bounded by caller capacity. Parent UIDs are monotonic across
flushes within a VM. Snapshot slots are bounded separately and report
truncation. Pointer-valued prototype identities are opaque, not references
that keep prototypes alive. Resolve debug/source metadata while traces are
available; register numbers and masks follow the target's `lj_target.h`.

The tests cover schema/size rejection, nonallocating reads, root and side
success, aborts, flush/reuse, independent VMs and new VM lifetimes. A generated
caller preserves forty floating values across a hot guard, exercises real
coalescing failures, repeat aggregation, ring overflow and bounded reads, and
reconciles native starts/compiles/aborts/emitted bytes/live population against
LuaJIT's existing callbacks and introspection. It changes no JIT policy.
