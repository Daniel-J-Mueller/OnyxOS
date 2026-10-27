# Hardware strategy

Status: planned support only. No hardware compatibility is claimed by this repository's initial design documents.

The PC objective is hardware capable of running Ubuntu and Windows. That identifies a broad hardware market, not a driver ABI or an automatic support guarantee. Onyx needs its own working drivers and platform integration. The Raspberry Pi and server objectives extend the roadmap beyond that initial PC target.

## Portability contract

Maintain common kernel/service source and stable application-facing interfaces, with separate machine-code builds for each supported instruction set. Runtime discovery selects drivers and CPU features within a supported architecture. Architecture backends and board firmware remain necessary. A single executable cannot natively run both x86-64 and AArch64 instructions, and a generic ARM VM image does not establish physical-board compatibility. QEMU explicitly documents the variation between ARM boards and the separate `virt` platform. [QEMU ARM system documentation](https://www.qemu.org/docs/master/system/target-arm.html)

| Stage | Target | Initial device contract | Promotion evidence |
| --- | --- | --- | --- |
| First boot | x86-64 QEMU, versioned PC machine, UEFI firmware | Serial, memory map, timer, exceptions, firmware framebuffer | Repeated clean boots, fault output and memory-map validation |
| Virtual workstation | Same VM, explicit virtio devices | Block, input, network, entropy and display | Driver lifecycle, malformed descriptors, restart and I/O stress |
| First physical PC | One published UEFI x86-64 reference machine | Exact storage, USB, display and network devices listed | Reproducible installation, device inventory and recovery |
| Architecture port | AArch64 QEMU `virt` with explicit CPU and device configuration | GIC, architectural timer, UART, virtio, device tree | Shared service tests and architecture isolation tests |
| Small board | One named 64-bit Raspberry Pi model and revision | Board boot chain, storage, USB, clock, display and power | Cold boot, reboot, thermal and sustained I/O on real board |
| Wider desktop | Selected PC chipsets and GPUs | Tested hardware matrix, hotplug, audio, Wi-Fi and suspend | Per-model release qualification and regression ownership |
| Compute server | SMP then NUMA reference systems | Topology, IOMMU, storage/network scaling, accelerators | Locality, throughput, tail latency and isolation measurements |
| Cluster | Multiple qualified compute nodes | Authenticated network and optional distributed services | Node-loss and scaling tests; no implicit shared-memory promise |

QEMU's ARM `virt` board offers explicit virtual devices and a versioned machine contract. Pin the machine, CPU model, firmware and acceleration mode for reproducible testing rather than relying on host defaults. [QEMU `virt` documentation](https://www.qemu.org/docs/master/system/arm/virt)

Raspberry Pi support means a selected application-processor board with an MMU, not every product carrying the name. Pico microcontrollers are a separate hardware category and are outside this roadmap. [Raspberry Pi hardware documentation](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html)

## Boot and discovery

The x86-64 loader consumes the UEFI memory map, loads verified images, configures a diagnostic framebuffer and exits boot services with the current map key. Onyx then owns runtime hardware operation; firmware boot-service drivers are not a permanent driver layer. [UEFI boot-services handoff](https://uefi.org/specs/UEFI/2.10/07_Services_Boot_Services.html)

Discover CPU and interrupt topology, usable/reserved memory, timers and devices through validated platform descriptors. Keep parsing isolated and bounded where practical. Separate ACPI support on PCs from device-tree and board-specific paths on ARM. Unsupported devices receive visible IDs and reasons rather than pretending to work. A missing device must not stall boot indefinitely.

Boot the minimum dependency graph first: memory and interrupts, authority, storage needed for the image, input, display and shell. Start optional networking, indexing and peripheral services afterward. A headless VM profile omits the graphical stack. Cache discovery only when it is safe to invalidate after hardware or firmware changes. Keep rescue/serial output available independently of accelerated graphics.

## Driver risk register

| Risk | Why it matters | Mitigation / release gate |
| --- | --- | --- |
| Real GPU initialization | Display, shader execution, memory management and firmware are large independent tasks | Start with a deterministic software path; select one documented GPU family; do not claim acceleration before measurement |
| Firmware redistribution | Devices may require blobs with separate redistribution terms | Inventory exact licenses, provenance and checksums before including firmware |
| DMA isolation | A device can access memory beyond a user-space driver's CPU mappings | Require supported IOMMU enforcement for untrusted DMA domains; label configurations without it as a weaker isolation profile |
| GPU command safety | User-space driver placement alone does not validate GPU commands | Validate submission, mappings, synchronization and reset behavior before untrusted rendering |
| USB and hotplug | Complex parsers and unplug races affect input and storage | Fuzz descriptors, revoke handles and test removal during active I/O |
| Storage durability | A fast acknowledgment may precede durable data | Define flush semantics; test abrupt interruption and recovery |
| Wi-Fi and Bluetooth | Firmware, radio control and protocol breadth increase effort | Ethernet/virtual network first; staged device-specific enablement |
| Laptop power | Suspend, resume, thermal and battery control vary by platform | Publish exact supported models; qualify each transition |
| Secure boot | Signing and firmware trust enrollment differ from simply booting | Document key ownership and recovery; test rejection and rollback |
| Pi variation | Boot firmware, controllers and connectors differ by model | Board-specific support package and real-device CI |
| NUMA and accelerators | Allocation/interrupt locality and device APIs can dominate compute | Publish topology-aware benchmarks and device-specific support |
| Unsupported hardware | “Runs Windows” does not imply documentation or compatible drivers | Maintain a tested matrix with exact IDs and supported functions |

Use the published virtio specification as the early virtual-device contract, including negotiated features and reset semantics. A virtio transport or 2D display driver alone is not proof of hardware-accelerated 3D graphics. [OASIS VIRTIO specification](https://docs.oasis-open.org/virtio/virtio/v1.3/virtio-v1.3.html)

The eventual support matrix must record architecture, firmware version, CPU, RAM, storage controller, GPU and connector, network device, input devices, power functions, supported feature level, known limitations and last successful test revision. Profiles select optional services and budgets without forking the core operating system.
