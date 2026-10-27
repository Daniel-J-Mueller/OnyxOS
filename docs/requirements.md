# Requirements and evidence

Status on project creation: **design** unless a row explicitly identifies a partial host model. There is no native OS implementation. Requirement IDs remain stable as the implementation changes.

| ID | Requirement | Acceptance evidence | Current evidence / owner document |
| --- | --- | --- | --- |
| ONX-001 | Run on ordinary PC hardware that can run Ubuntu/Windows | Published tested hardware matrix; boot, storage, networking, input, display and recovery checks for each supported device | Design: [hardware](hardware.md); no application/guest compatibility requirement |
| ONX-002 | One key toggles Fit Mode and restores standard mode | One dispatch per non-repeated press; exact restoration of surviving windows' bounds, focus, order, output and workspace under unchanged topology | Partial host geometry model; [Fit Mode](fit-mode.md) |
| ONX-003 | Minimize unused screen area without destructive cropping | Deterministic constrained layout; measure content, border, reserved, letterbox and unused areas separately; compare against feasible candidates | Partial host layout model; [Fit Mode](fit-mode.md) |
| ONX-004 | Normally 2–3 physical pixels of framing | Pixel-level tests across DPI, transforms and output boundaries; text remains readable and image edges are preserved | Partial host border geometry; [Fit Mode](fit-mode.md) |
| ONX-005 | Compact controls enlarge on approach | Deterministic hit tests, stable target during click/drag, no timed expansion, keyboard and touch equivalents, usability trials | Partial host state model; [Fit Mode](fit-mode.md) |
| ONX-006 | Separate previous/next desktop controls | Both visible buttons and optional remappable keys; mode switch preserves applications and has no shell animation | Partial host preset state; [desktop modes](desktop-modes.md) |
| ONX-007 | Desktop environment variety | Native preset policy and semantic UI API; inspectable theme/layout configuration; no requirement to execute Ubuntu/GNOME binaries | Design: [desktop modes](desktop-modes.md) |
| ONX-008 | Immediate system interactions | No decorative animations, easing, artificial sleeps or minimum loading dwell; instrument input-to-submit and input-to-photon latency | Design: [performance](performance.md) |
| ONX-009 | Efficient GPU-oriented display | Damage, occlusion, synchronization and scanout tests; GPU resets recover; idle surfaces cause no redraw loop | Design: [graphics](graphics.md) |
| ONX-010 | Efficient safe memory allocation | Ownership and lifetime checks; allocator bounds/failure tests; quotas; no unbounded allocation on input/display critical paths | Design: [security](security.md), [toolchain](toolchain.md) |
| ONX-011 | Build a minimal original low-level language/toolchain | Defined semantics; negative safety tests; typed IR; deterministic native code; audited bootstrap chain and comparison benchmarks | Design: [toolchain](toolchain.md) |
| ONX-012 | Every system activity has an accountable identity | Reconcile task/service/thread/interrupt/deferred/GPU/I/O work with resource totals; include unknown/unattributed buckets; privilege-safe visualization | Design: [observability](observability.md) |
| ONX-013 | Rapid cold boot and VM startup | Repeatable cold-boot milestones and distributions; snapshots separately labeled; observable readiness and recovery | Design: [performance](performance.md), [roadmap](roadmap.md) |
| ONX-014 | Scale from Raspberry Pi-class hardware to large systems | Separate architecture builds from common source; board tests; SMP/NUMA resource and fault tests; headless operation | Design: [hardware](hardware.md), [architecture](architecture.md) |
| ONX-015 | Safe OS and reliable lifecycle | Threat-model-driven tests; authenticated updates and recovery; least privilege; no security bypass for speed | Design: [security](security.md) |
| ONX-016 | Use resources effectively without waste | Throughput and tail latency alongside CPU/GPU time, memory pressure, energy and thermal measurements; retain useful idle headroom | Design: [performance](performance.md) |
| ONX-017 | Broad, explicit subsystem plan | Account for boot, kernel, drivers, storage, network, UI, tools, install/update/recovery, power, accessibility, operations and application APIs | Design: [architecture](architecture.md), [roadmap](roadmap.md) |

## Interpreting the goals precisely

“Instantaneous” means no intentional shell delay and the lowest measured practical latency; hardware, work queues, storage and display scanout still take time. “Perfect fit” names the feature; it cannot guarantee a mathematical global optimum for arbitrary applications. Safety, readability, focus stability and complete content take priority over filling an impossible rectangle.

“Maximize utilization” means maximize useful work per resource budget. A desktop that consumes every idle CPU/GPU cycle is wasting power and reducing responsiveness. Priority, isolation, reserve capacity and admission control are part of performance.

“No target tailored system” means avoid maintaining a separate OS design per machine. CPU instruction sets, firmware interfaces, drivers and some board descriptions still differ. Architecture builds use a conservative baseline plus feature discovery and validated optional fast paths.

The root requirements come from the owner's founding description and clarification that Ubuntu/Windows compatibility means **hardware only**. Proposed binding choices and numeric budgets are revisable defaults. New language names and ABI details remain provisional until specified and tested.
