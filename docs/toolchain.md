# Original systems language and toolchain

**Status: proposed research program.** There is no OnyxOS language implementation, compiler, assembler, linker, runtime, or bootable kernel. The host-side Python geometry model is a design aid and does not implement this toolchain or establish OS performance.

## Direction and scope

Develop a small original systems language, provisionally called **Onyx Core**. The name is a working label, not a uniqueness or trademark claim. It should express kernel, driver, compositor, and service code with predictable costs and checked memory access. Architecture-specific assembly remains a narrow, separately reviewed layer for entry code and instructions that cannot be expressed safely.

A new language is not inherently faster or safer than an established one. It adds substantial compiler, semantics, optimizer, tooling, and ecosystem risk. Its value must be demonstrated through generated code, defect detection, auditability, code size, and measured latency against equivalent implementations. Do not claim that replacing a language automatically improves frame rate.

Host tools in existing languages may bootstrap research, run tests, inspect binaries, and generate prototypes. They are development dependencies, not a requirement to ship their interpreters or large runtimes in OnyxOS. Any existing compiler backend used experimentally must be pinned and documented. A custom language, native backends, and eventual self-hosting remain explicit milestones, not current capabilities.

## Minimum language contract

| Area | Proposed semantics |
| --- | --- |
| Values and layout | Fixed-width integers, booleans, explicit enums, tagged unions, structs, arrays, slices; specified alignment, padding, and ABI layout |
| Lifetimes | Ownership and non-escaping borrows; no safe use after free, double free, or dangling reference; no implicit reference-counting overhead |
| Aliasing | Exclusive mutation or explicitly synchronized sharing; alias guarantees preserved in generated code |
| Indexing | Bounds checks by default, removed only after a valid proof; checked pointer/slice length construction |
| Arithmetic | Checked integer overflow, division, shifts, casts, and size calculations; wrapping and saturating operations explicit |
| Errors | Typed error results; no hidden exception unwinding; specified trap behavior for irrecoverable contract failures |
| Allocation | Explicit allocator/region parameter; fallible allocation; ownership and quota attribution visible at interfaces |
| Concurrency | Typed transfer/share rules, atomics with specified ordering, reviewed synchronization; no safe unsynchronized conflicting access |
| Effects | Interfaces state allocation, blocking, privilege, and unsafe effects; interrupt-safe code cannot call a blocking or allocating interface accidentally |
| Foreign interfaces | Narrow C/machine ABI adapters with explicit ownership, lifetime, layout, and validation contracts |
| Low-level access | Unsafe modules for MMIO, raw pointers, page tables, interrupts, and DMA; volatile access is distinct from ordering and synchronization |
| Execution | Ahead-of-time native code; no mandatory tracing GC, JIT, interpreter, or background optimizer |

The first version should omit features that make cost or proof obligations difficult to inspect. Specify integer and pointer semantics, object initialization, destructors, cancellation, stack limits, recursion policy, atomics, and panic/trap handling before extending syntax. Safe source code is only as safe as its compiler, runtime, unsafe dependencies, and hardware assumptions.

Maintain machine-readable unsafe-boundary inventories with an owner, invariant, callers, tests, and review state. An unsafe block is not an optimization permission slip. Shared DMA/GPU memory needs an ownership protocol covering device completion, not merely CPU reference lifetimes.

## Allocation model

Use explicit domains: boot arena, per-process heap, per-service pools, bounded interrupt resources, per-frame command storage, and separately charged DMA/GPU buffers. Regions help make lifetimes and bulk release predictable; they do not guarantee bounded allocation latency unless capacity and operations are bounded too.

Preallocate measured steady-state resources on latency-critical paths. Set capacity, refill rules, overflow behavior, ownership, and metrics for each pool. Exhaustion must return a typed error, shed optional work, or apply documented backpressure; it must never trigger unbounded retries or silent memory corruption. Bound allocator metadata and cache retention so performance caches cannot evade quotas.

Start with simple auditable allocators. Compare fragmentation, peak residency, p50/p95/p99 latency, worst observed stalls, cross-core contention, zeroing costs, and reclamation behavior before adopting more complex designs. Publish workload and machine details; a constant-time algorithm alone does not establish a whole-system real-time bound.

## Compiler pipeline and correctness

Proposed pipeline: source -> parsed syntax -> typed/effect-checked representation -> ownership-checked typed IR -> explicit control-flow and memory IR -> target lowering -> machine code/object file -> linked boot or service image.

Keep pointer provenance, lifetimes, bounds, alignment, effects, and capability use visible until the pass that justifies removing or lowering them. Every pass must state preserved invariants and have an IR verifier. Maintain a simple executable semantics/reference interpreter for the defined language subset, a minimally optimized baseline, and differential comparison against optimized outputs.

Do not lower checked arithmetic or invalid inputs into backend undefined behavior accidentally. LLVM's documentation distinguishes immediate undefined behavior from deferred poison values; an experimental LLVM backend must respect that contract rather than assume its IR inherits source-language safety. See [LLVM's undefined-behavior manual](https://llvm.org/docs/UndefinedBehavior.html).

Test malformed source, hostile complexity, type errors, lifetime errors, parser nesting, integer boundaries, atomics, register allocation, calling conventions, relocation, stack layout, and link failures. Compiler resource quotas matter because source and build inputs may be untrusted. Fuzz parsers and IR passes; minimize and retain failures; test both successful compilation and intentional rejection.

Formal methods begin with small properties: type/ownership preservation, capability checks, allocator invariants, and selected transformations. Track proved subsets and assumptions precisely. Existing verified compilers still identify unverified front-end or toolchain components; see [CompCert's documented verification boundary](https://compcert.org/man/manual001.html). OnyxOS has no compiler proof today.

## Bootstrap and self-hosting milestones

| Stage | Deliverable | Exit evidence |
| --- | --- | --- |
| T0: specification | Grammar, core semantics, cost/effect model, memory model, IR schema, ABI draft | Executable examples and rejection cases; independent design review |
| T1: host research compiler | Small pinned host implementation and reference interpreter | Differential semantics tests; bounded malformed-input handling |
| T2: native baseline | x86-64 machine-code path, minimal object writer/link path, reviewed entry assembly | Known instruction/ABI vectors; executable tests under emulator and real hardware |
| T3: portable semantics | AArch64 backend with explicit platform layer | Cross-target conformance corpus; architecture-specific atomic/memory tests |
| T4: OS subset | Small kernel/services use the defined safe subset and audited unsafe modules | Isolation, allocation-failure, crash, and performance evidence |
| T5: self-hosting | Compiler builds its own supported source subset | Repeatable stage comparisons and independent bootstrap review |
| T6: optimization | Measured optimizations and broader device/library support | Correctness evidence retained; speed, size, energy, and tail-latency results |

Self-hosting is a maintenance milestone, not a correctness certificate. Maintain the small host implementation long enough to provide an independent comparison. Record the initial compiler binaries, source, versions, hashes, build environment, and every generated stage; investigate independent or diverse bootstrap methods before claiming resistance to a compromised compiler.

Architecture portability means shared source contracts and target backends. One executable cannot transparently execute different instruction sets. Keep CPU feature dispatch, endianness, page sizes, cache/DMA coherency, atomics, interrupt control, and ABI differences explicit. Raspberry Pi and supercomputer aspirations require their own hardware support work; neither follows automatically from x86-64 support.

## Builds and performance acceptance

Use hermetic, version-pinned builds with normalized timestamps/paths, deterministic ordering, offline dependency manifests, and reproducible output comparison. Record debug symbols separately without losing crash attribution. Reproducibility means recreating identical specified artifacts from defined inputs and environment; it does not establish correctness. See [Reproducible Builds' definition](https://reproducible-builds.org/docs/definition/).

Run optimized and debug variants through the same semantic conformance tests. Debug builds may add diagnostics and poisoning; release builds retain security-relevant checks unless validly eliminated. Do not change language meaning or disable essential bounds checks just to meet a benchmark.

Benchmark equivalent algorithms at equal correctness and safety settings. Report compiler time/RAM, binary size, code quality, boot contribution, CPU and GPU submission cost, allocation tails, and end-to-end interactive latency. Hold complex optimizer work until a measured bottleneck justifies it. Custom GPU shader compilation is a later separate decision, not implied by having a CPU compiler.
