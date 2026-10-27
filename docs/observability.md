# Every activity has an identity

**Status: proposed design.** No kernel registry, process inspector, task tracing service, or telemetry implementation exists yet. This document defines contracts for future implementation, not a screenshot or claim of current functionality.

## User-visible contract

An authorized system owner must be able to inspect every OS-managed schedulable activity and resource-owning entity. A task without an application window still has a stable identifier, a useful type, an owner, and a reason for existing. The system inspector is a first-class interface, with a text/serial equivalent for headless and recovery use.

Show activity immediately when selected: searchable hierarchy, state, CPU/memory/I/O/GPU usage, permissions, origin, and related work. No entrance animations, artificial loading delays, hover timers, or decorative motion. If details require real I/O, show the available identity and measured progress immediately, keeping cancellation and navigation usable.

Do not represent opaque firmware as if it were an ordinary inspectable process. Show the device, firmware identity when available, known work, and the visibility limitation. A registry explains OS-managed work; it cannot prove that hardware or compromised privileged code is doing nothing else.

## Identity and attribution schema

| Field | Requirement |
| --- | --- |
| Identity | Boot/session namespace plus non-reused lifetime identity; distinguish local handles from persistent package identity |
| Type | Process, thread, service, driver, interrupt source, deferred work, GPU context/job, I/O operation, or other explicit kind |
| Display label | Bounded, sanitized human-readable name; safe fallback such as `unnamed task <id>` |
| Verified origin | Executable/package digest, available signing identity, service definition, and launch mechanism; no implication that signed means safe |
| Ownership | User/security principal, resource account, creator, supervisor, and policy domain |
| Cause | Parent and initiating request/activity identifiers; explicit unknown or many-to-one attribution |
| State | Created/runnable/running/blocked/stopped/exited; reason and timestamps where available |
| Resources | CPU time, resident/committed/shared/pinned memory, handles, I/O, GPU resources, limits, and measurement quality |
| Authority | Effective capability categories, grants, and relevant delegations, filtered by inspection privilege |
| Lifecycle | Start/end, exit/fault reason, restart count, build identity, and retention status |

Labels are untrusted descriptions. Kernel-assigned identity and verified executable origin must remain visually distinct from a name supplied by an application. Prevent control-character injection, bidirectional-text spoofing, unbounded strings, and identifier reuse from merging unrelated tasks in the inspector.

Represent kernel worker pools and per-CPU interrupt work explicitly. Account work to a causal owner where available, otherwise to a named shared/system bucket; do not charge the same CPU interval twice. GPU contexts and jobs retain links to submitting processes, queue/fence state, and device-reset events. Shared service work should report shared attribution instead of inventing a single owner.

If guest hosting is ever added, represent the VM, its host threads, memory, and devices. Guest-internal tasks require a separately trusted guest agent or introspection design and must be labeled as such. Hosting Ubuntu/Windows guests is not a current requirement or implemented feature.

## Registry versus tracing

Maintain an authoritative bounded registry for live entities. Optional high-volume traces describe events over time and may lose history under pressure. Do not make the live task list depend on a lossy event stream. Creation/destruction and registry snapshots need a versioned reconciliation protocol so a slow inspector cannot silently lose a task or show a reused ID as the old task.

Trace records use a versioned binary schema, explicit clock domain, timestamp, sequence number, event type, activity identity, parent/correlation identity, and bounded payload. Capture monotonic timestamps for durations; identify resets and clock discontinuities. CPU, GPU, and distributed clocks require calibrated mappings with uncertainty, not assumed equality.

Use bounded per-CPU or per-producer buffers with a documented producer/consumer protocol. Writers cannot block scheduler or interrupt paths waiting for a viewer. Define overwrite/drop policy, event-loss counters, producer quotas, snapshots, and flush behavior. A consumer crash must not stop the workload. Perfetto documents a useful reference pattern of bounded shared-memory production and explicit data loss; it is a design reference, not an OnyxOS dependency or implementation. See [Perfetto buffers and dataflow](https://perfetto.dev/docs/concepts/buffers).

Keep low-cost lifecycle/resource counters available by default. Enable detailed scheduler, allocation, syscall, I/O, and GPU traces only with an explicit profile and budget. Separate security audit records from best-effort performance events: specify durability, storage-full behavior, and recovery for the security audit path before relying on it for authorization evidence. Never silently describe dropped audit records as a complete history.

## Privacy and access control

- An ordinary user inspects their own permitted activities. A privileged inspector can enumerate the full OS registry. Other users' details are redacted or aggregated according to policy, with the limitation visible.
- Listing an identity does not grant control, memory access, process termination, debugging, or access to its handles. Each operation requires separate authority and audit where appropriate.
- Treat command lines, filenames, environment values, addresses, keystrokes, clipboard contents, network payloads, and document text as potentially sensitive. Do not collect their contents by default.
- Keep traces local by default, with bounded retention and explicit export. Show export scope and redactions. Crash reports must not silently include another user's memory or secrets.
- Authenticate trace producers, separate their buffers, validate all payloads, and show application-supplied events as untrusted. Inspection tools must remain usable when producers emit malformed or excessive data.
- Report permission denial, unavailable counters, estimation, sampling, and dropped data clearly. A missing value is not zero resource consumption.

## Performance evidence

Measure baseline, default observability, and detailed tracing separately on the same workload and hardware. Report CPU cost, memory footprint, allocation, wakeups, event throughput/loss, storage bandwidth, and effects on p50/p95/p99 input latency and boot time. Set and publish numerical budgets after the first measured baseline; no observability overhead target has been achieved yet.

For a click-to-display path, correlate input arrival -> routing -> application handling -> layout/render -> GPU submission -> completion -> presentation. State which stages are observed and which are estimated. A CPU timestamp at submission is not a physical input-to-photon measurement. For boot, distinguish firmware time, loader time, kernel initialization, service readiness, and first usable interaction.

Provide static tables and timelines without forcing continuous rendering. Update views on meaningful changes, coalesce display work within an explicit freshness budget, and allow manual snapshots. Continuous polling or redrawing at maximum rate would consume resources the OS is meant to make available to useful work.

## Acceptance tests

1. Spawn, crash, restart, and exit many tasks while an inspector falls behind; reconcile with the registry with no lifetime confusion.
2. Attribute interrupt/deferred work, service requests, I/O completion, and GPU work; retain explicitly unknown/shared categories.
3. Saturate every trace buffer and kill the consumer; maintain system responsiveness and expose all loss counters.
4. Attempt cross-user inspection, malicious labels, forged producers, and unauthorized control; enforce policy and preserve a usable viewer.
5. Apply CPU, memory, storage, and GPU pressure; keep a bounded recovery/inspection path and explain unavailable details.
6. Compare headless/serial and graphical inventories, and verify that instrumentation profiles meet their published overhead budgets.

Open decisions: lifetime-ID representation, kernel registry storage bounds, capability-inspection policy, default retention, audit durability, GPU attribution support, and export format. Resolve these alongside [security.md](security.md) and [toolchain.md](toolchain.md), not after the first desktop ships.
