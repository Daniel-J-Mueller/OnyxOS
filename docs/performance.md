# Performance contract and measurement plan

Status: provisional engineering budgets. No values below are achieved benchmark results or hardware-independent promises. Initial numbers prioritize measurement and reveal expensive paths; revise them through recorded evidence rather than quietly changing a failing target.

“Instantaneous” means no artificial shell delay, transition animation or unnecessary blocking. CPU execution, storage, network traffic, display scanout and physical input devices impose real latency. Optimize useful completed work and tail latency while maintaining isolation, correctness and thermal limits. Empty busy loops or 100% utilization at idle are regressions.

## Reference profiles

Every result must name the source revision, compiler and flags, firmware, CPU and topology, RAM, storage, GPU, display timing, driver versions, power policy, temperature, background load and instrumentation. VM results additionally identify the host, QEMU version, exact machine/CPU model, acceleration mode and guest resources. Pin a concrete machine before treating a target as a release gate.

- **VM-minimal:** x86-64 UEFI VM, 2 vCPUs, 512 MiB RAM, serial/task service and virtual storage; no compositor. Measure native hardware virtualization separately from software emulation.
- **Desktop-reference:** selected x86-64 PC, at least 4 cores and 8 GiB RAM, local SSD, supported GPU, 1920×1080 display at 60 Hz and 120 Hz. Exact model is a milestone decision.
- **Small-board:** one selected AArch64 Pi model, initially a 1 GiB memory envelope, headless and desktop measured separately. Do not infer its result from the desktop budget.
- **Compute-reference:** named multi-socket NUMA system, then a small cluster. Report scaling efficiency, throughput and service jitter with a documented workload.

## Provisional budgets

| Metric | Initial objective | Boundary and method |
| --- | --- | --- |
| Artificial shell animation/dwell | 0 ms | Inspect transition paths and event traces; no aesthetic delay |
| Minimal VM boot | p95 ≤ 500 ms | Onyx loader entry to ready task/control service; excludes VM launch and firmware, which are reported separately |
| Desktop readiness | p95 ≤ 2 s | Onyx loader entry to input-responsive shell on the reference PC; cold/warm runs separate |
| Fit layout computation | p99 ≤ 1 ms for 32 visible windows | Input constraints to computed geometry, excluding application re-render and presentation |
| Shell input dispatch | p99 ≤ 1 ms while idle; ≤ 4 ms under defined stress | Event receipt in OS to shell handler start; device polling excluded and separately reported |
| Compositor CPU work | p99 ≤ 1 ms for the reference 1080p workload | Ready surfaces to submitted frame; exclude client rendering, report separately |
| Composition GPU work | p99 ≤ 2 ms for the reference 1080p workload | GPU timestamp interval where supported; show fill and bandwidth counters |
| Visible response | Next feasible refresh; initial p99 objective ≤ 2 refresh periods plus measured device latency | Input-to-photon instrumented on supported hardware; 16.67 ms/60 Hz and 8.33 ms/120 Hz per period |
| Deadline misses | < 0.1% on a defined 10-minute interaction workload | Count late ready frames against actual presentation deadlines |
| Warm native utility launch | p95 ≤ 50 ms | Accepted launch request to usable first frame; also publish cold launch and utility definition |
| Minimal headless memory | ≤ 64 MiB total resident software memory after boot | Include kernel, drivers and services; report reserved, cache and device memory separately |
| Minimal desktop memory | ≤ 256 MiB resident software memory at 1080p | Include kernel/services/compositor; separately account scanout, GPU allocations and reclaimable caches |
| Idle composition | 0 new frame submissions for an unchanged desktop | 60-second trace with cursors and periodic app content held static |
| Allocation hot path | No general heap allocation in interrupt or steady-state composition deadline path | Allocation tracing; fallible bounded pools and overflow tests |
| Local IPC | Establish baseline first; guard against unexplained > 5% regression | Fixed payload and shared-buffer workloads; p50/p95/p99, cycles and context switches |

The latency budgets are not additive guarantees: pipelines overlap, missed deadlines add a refresh, and clients can be late. Name each timestamp's clock and synchronize clock domains before subtracting them. Measure release builds separately from debug/sanitized builds. A virtual framebuffer timing result is not a physical-display timing result.

## Benchmark suite

| Workload | What it reveals |
| --- | --- |
| Cold boot, warm reboot and repeated VM creation | Critical-path dependencies and firmware versus OS cost |
| Idle desktop and headless idle | Wakeups, memory, power and unnecessary drawing |
| Pointer motion, text input, drag and Fit toggle | Event latency, layout stability and visible completion |
| 1/8/32/128 windows; mixed minimum sizes | Packing complexity, damage cost and graceful constraint handling |
| 1080p/4K, mixed DPI, multi-monitor, video and scrolling | Fill cost, bandwidth, scaling and presentation policy |
| CPU/GPU/storage/network saturation during interaction | Priority inversion, queue limits and fairness |
| Allocation churn and low-memory pressure | Fragmentation, tail latency, reclaim and ownership accounting |
| IPC ping-pong and streamed shared buffers | Context-switch cost, copying threshold and synchronization |
| Filesystem small-file, sequential and random I/O with forced interruption | Caching policy and durability versus acknowledged throughput |
| Driver crash, GPU hang, device removal and service restart | Recovery latency and preservation of useful state |
| Parallel compute across cores and NUMA nodes | Throughput, locality, contention and scheduler overhead |
| Multi-node compute and node failure | Network/coordination cost; separate from local kernel scalability |

CPU isolation and reduced timer interruption are workload-dependent techniques, not universal improvements. They can transfer work to housekeeping cores and increase transition costs. Onyx must test both interactive and compute profiles before selecting policy. [Linux CPU-isolation tradeoffs](https://docs.kernel.org/admin-guide/cpu-isolation.html)

## Evidence and regression policy

Store raw samples and machine metadata with each report. For boot, collect at least 30 independent runs per condition. For frame/input percentiles, collect at least 10,000 events with defined idle and stressed workloads; publish the distribution, worst cases, missed deadlines and enough repeats to distinguish noise. Include confidence intervals or repeat variability. Do not merge samples from different machines into a single percentile.

Run thermal steady-state trials as well as short bursts. Keep power and quality settings equivalent when comparing platforms. If claiming an advantage over another OS, use the same hardware and workload, document unavoidable API differences and publish both systems' configuration. Do not remove security features or reduce rendering quality on only one side.

Gate performance changes on correctness first. Investigate a repeatable > 5% regression or a missed absolute budget; an approved exception must state the reason, affected profile, owner and expiry/review milestone. Improvements must show where work was removed, reduced or overlapped, and retain long-run memory and failure recovery behavior.

Optional tracing uses bounded per-CPU buffers, sampling and explicit drop counters. Keep enough always-on task accounting for visibility, but measure its overhead. Report results both with minimal production instrumentation and diagnostic tracing so observability cost is visible.
