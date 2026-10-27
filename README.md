# OnyxOS

An original operating-system research project for a compact, immediate desktop and efficient computing across hardware classes.

**Status: architecture and executable host reference models. There is no bootable OnyxOS kernel, installer, GPU driver, or native application runtime yet.** Performance numbers in the specifications are proposed acceptance targets, not measured OS results. Security properties are requirements, not a certification.

## The intent

- **Fit Mode:** one configurable key toggles between the saved standard desktop and a content-aware layout that minimizes unused area. Window/image framing is normally 2–3 physical pixels. Content stays intact and readable.
- **Approach-to-expand controls:** compact controls become immediately larger as the pointer approaches their region. Stable hit areas, keyboard access, and touch alternatives keep them usable.
- **Desktop presets:** visible previous/next buttons and optional separate key bindings cycle native layouts without restarting applications. An Ubuntu-inspired layout is a design preset, not the Ubuntu operating system.
- **Immediate shell:** zero decorative animations, fades, easing, or artificial loading delays. Actual I/O, security checks, synchronization, and application work remain observable.
- **Efficient graphics:** damage-driven rendering, bounded queues, explicit synchronization, and direct scanout where supported. Compare against measured baselines; existing operating systems also accelerate graphics.
- **Safe resource use:** explicit ownership, bounded allocation, isolation, and attribution of CPU, GPU, memory, and I/O work.
- **Small to large:** common portable source with architecture backends and runtime device discovery. Separate machine-code builds and some board-specific support remain necessary.
- **A small original systems language:** develop a minimal, auditable language and compiler alongside the kernel design; prove its safety rules and benchmark its generated code before trusting it.

The hardware goal is machines of the kind that run Ubuntu or Windows. This does **not** promise Linux/Windows application compatibility, bundled guest operating systems, or immediate support for every such machine. Raspberry Pi and large NUMA systems are later hardware milestones.

## Try the reference model

Install Python 3.11 or later on a development host. No third-party packages are required.

```sh
python -m unittest discover -s tests -v
python -m prototype.demo
python tools/check_repository.py
```

On Windows, `py -3` can replace `python`. The JSON demo exercises desktop layout behavior; it does not change your display settings or manage real windows. Python is development scaffolding, not the planned OnyxOS implementation language or a dependency of the future boot image.

## Project map

| Document | Purpose |
| --- | --- |
| [Requirements](docs/requirements.md) | User intent, requirement IDs, evidence and acceptance criteria |
| [Fit Mode](docs/fit-mode.md) | Layout, scaling, controls, reversibility and failure behavior |
| [Desktop modes](docs/desktop-modes.md) | Native presets, bindings, accessibility and lifecycle |
| [Architecture](docs/architecture.md) | Kernel, services, subsystem boundaries and interfaces |
| [Graphics](docs/graphics.md) | Rendering, scanout, synchronization and fallbacks |
| [Hardware](docs/hardware.md) | CPU architectures, firmware, devices and support tiers |
| [Security](docs/security.md) | Threat model, isolation, trusted boot, updates and recovery |
| [Observability](docs/observability.md) | Labeled activity graph, accounting and privacy |
| [Toolchain](docs/toolchain.md) | Original language, bootstrap and compiler validation |
| [Performance](docs/performance.md) | Measurement protocol and provisional budgets |
| [Roadmap](docs/roadmap.md) | Dependency order and milestone exit criteria |
| [Decisions](docs/decisions.md) | Initial architectural decisions and unresolved choices |
| [Contributing](CONTRIBUTING.md) | Evidence required to change a design or implementation |

The executable model lives in `prototype/`; host tests live in `tests/`. The project intentionally has no empty pretend kernel implementation. Add native components with their build and execution evidence when each milestone is reached.

## Current limits

The initial layout model explores a bounded family of layouts, not the globally optimal arrangement of arbitrary application content. Real content negotiation, native input, display modesetting, multi-monitor recovery, GPU work, and assistive technology integration are specified future work. Passing model tests demonstrates only the modeled behavior.

The first native milestone is a reproducible x86-64 UEFI/QEMU boot with serial diagnostics and a bounded memory-map handoff. See the roadmap for its gates and the original-language bootstrap dependency.

## Licensing

A distribution license has not been selected. Public repository visibility alone does not grant an open-source license. The owner must choose project licensing and document third-party obligations before accepting external code or distributing an OS image.
