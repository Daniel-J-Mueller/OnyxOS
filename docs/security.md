# Security architecture

**Status: proposed design, not an implemented security boundary.** OnyxOS currently has planning documents and a host-side geometry prototype. It has no bootable kernel, custom compiler, isolation implementation, security certification, or supported production release. Hardware that can run Ubuntu and Windows is the initial compatibility goal; this does not imply Linux or Windows binary compatibility.

## Threat model and trust

Protect user data, credentials, input, display contents, application isolation, update integrity, and interactive availability against malicious applications, hostile network input, malformed files, compromised services, and faulty or malicious drivers. Include resource exhaustion, confused deputies, stale handles, malicious GPU submissions, and stolen powered-off devices in design reviews.

The proposed trusted computing base includes the minimal kernel, capability manager, selected boot and recovery code, compiler output, cryptographic implementations, and the hardware/firmware assumptions of each supported platform. Privileged services remain separately reviewable and should hold only the authority required for their jobs. Minimize this boundary; do not equate a small boundary with a proved one.

Firmware compromise, physical tampering, hardware defects, speculative-execution attacks, timing channels, and unavailable device documentation require explicit platform limitations and mitigations. No claim of absolute safety is permitted. Even mature verified kernels state assumptions about hardware, boot, assembly, DMA, and information channels; OnyxOS has no such verification today. See [seL4's published proof assumptions](https://sel4.systems/Verification/assumptions.html).

## Authority and isolation contracts

| Boundary | Proposed contract | Required evidence before release |
| --- | --- | --- |
| Process memory | Separate address spaces; writable pages are non-executable; no implicit cross-process access | Adversarial map, fault, permission, and executable-loading tests |
| Object access | Kernel-validated opaque capabilities; explicit rights, delegation, revocation, lifetime, and quotas | Model checking of stale-handle reuse, revocation races, and confused-deputy cases |
| IPC and shared buffers | Bounded messages, validated lengths, explicit sharing rights and synchronization | Parser fuzzing, malformed-handle tests, and concurrent sender tests |
| Files and network | Authority granted to explicit resources or brokered operations; no ambient universal access | Traversal, rename/race, endpoint-policy, and revocation tests |
| Devices | Drivers isolated where feasible; MMIO, interrupts, and DMA exposed only through explicit grants | Fault injection, reset, hot-unplug, and DMA isolation testing |
| Display and input | Only the compositor/input broker controls global focus and delivery | Spoofing, unauthorized capture/injection, lock-screen, and focus-race tests |
| Resource usage | Per-principal limits for memory, handles, CPU, I/O, GPU queues, and telemetry | Exhaustion tests that retain a usable recovery/control path |

Specify capability identity independently of application-provided names. A restarted process receives a new lifetime identity. Revocation must account for in-flight IPC, pinned buffers, and device work; deleting a handle cannot silently leave its former owner with access. Service identity and policy determine authorization, not a label supplied by the client.

The compositor must distinguish trusted system prompts from application surfaces. Screen capture, clipboard transfer, accessibility control, global input, and input injection require scoped permissions. Fit-mode enlargement must preserve the selected control's identity and cannot turn an untrusted application control into a system-looking authorization prompt.

## Memory, concurrency, and failure

The [language contract](toolchain.md) proposes ownership, borrowing, checked indexing and arithmetic, explicit synchronization, and narrow reviewed unsafe interfaces. Runtime checks remain active in optimized builds unless the compiler proves they are unnecessary. Optimization must not silently replace a checked operation with undefined behavior.

Use bounded allocation domains and quotas, checked size calculations, zeroing before memory crosses principals, stack guards, and explicit allocation failure. Track physical pages, virtual mappings, DMA pins, GPU allocations, and shared-memory charges separately. Shared resources need one auditable charging rule to avoid both double accounting and uncharged exhaustion.

Keep interrupt paths, allocator internals, and IPC fast paths allocation-bounded. Reclamation must wait for readers and devices to release access. A use-after-free through DMA remains a memory safety defect even if the CPU language would reject the same operation.

Contain service failures; bound restart retries; expose the failure and its cause. A crashed driver must not leave stale DMA mappings. A hung GPU must have a documented reset/recovery path, including what happens if the device cannot preempt or reset safely. Critical kernel invariant failure enters a controlled recovery path, not speculative continuation. Recovery availability is itself tested under resource exhaustion.

## DMA and GPU policy

CPU address-space isolation does not by itself constrain DMA. The Linux VFIO documentation explains that real isolation depends on IOMMU and interconnect topology, sometimes grouping multiple devices into one isolation unit. OnyxOS must discover and honor the hardware's actual isolation units. See [VFIO groups, devices, and IOMMUs](https://docs.kernel.org/driver-api/vfio.html#groups-devices-and-iommus).

When supported, map only approved buffers into device address spaces, limit pinning, validate command submissions, invalidate mappings before reuse, and test interrupt remapping and device reset behavior. GPU memory isolation, shader validation, and queue limits are separate requirements from IOMMU isolation.

Without trustworthy DMA isolation, do not offer untrusted direct device assignment. Either disable the device or use a reviewed trusted driver with a prominently recorded reduced-isolation platform status. Bounce buffers can limit intended transfers; they cannot contain an arbitrary bus-mastering device. A software-rendered display fallback is useful only when its underlying framebuffer/device access satisfies the platform threat model. A VM boundary is not an automatic remedy for unsafe passthrough.

## Boot, secrets, storage, and recovery

- Define a verified loading chain from supported firmware to kernel and critical services. Secure Boot validates authorized boot images; it is not a runtime correctness proof. Keep firmware key enrollment and platform-owner control explicit. See [UEFI Secure Boot and Driver Signing](https://uefi.org/specs/UEFI/2.10_A/32_Secure_Boot_and_Driver_Signing.html).
- Separate normal, developer, and recovery policies. Normal operation cannot silently accept unsigned privileged code. Developer mode must visibly identify its changed trust policy and require an explicit owner action to enable it.
- Establish entropy readiness before creating keys or identifiers that require unpredictability. Select established cryptographic constructions and reviewed implementations; developing a language does not justify inventing cryptography.
- Specify encrypted data-volume and swap policies, authenticated key metadata, key derivation, key rotation, recovery credentials, and cryptographic erasure limits. Encryption protects defined data at rest; an unlocked compromised session remains in scope for access control.
- TPM-backed key protection is a platform-dependent enhancement with recovery paths for firmware changes and board replacement. Document the weaker guarantees on devices without it. Never make an unrecoverable hardware dependency an undocumented default.
- Secure crash dumps, hibernation images, diagnostics, and recovery tools to the same data classification as the memory they can contain. Default diagnostics exclude secrets and raw application buffers.
- Recovery must support a known-good signed system image without silently erasing user data or undoing security version policy. Power-loss and interrupted-write tests are required for boot metadata and updates.

## Update and supply-chain design

Use authenticated manifests, separate signing roles, revocable/rotatable keys, pinned artifact hashes, and explicit version and expiry handling. Package installation authority is separate from application execution authority. Verify before executing and before replacing the trusted system state.

The update design must resist rollback, stale-metadata freeze, and mixed-version attacks. Offline operation and unreliable clocks need an explicit policy instead of silently ignoring expiration. These requirements are informed by [The Update Framework specification](https://theupdateframework.github.io/specification/v1.0.36/); use of this reference does not mean TUF is implemented.

Atomic system slots or snapshots are candidates for rollback after a failed update. Distinguish operational rollback to an allowed known-good release from a prohibited downgrade below the security version floor. An owner-authorized emergency downgrade must disclose the effect, retain an audit record, and use an independently reviewed recovery procedure.

Release evidence must include source revision, toolchain provenance, dependency and firmware inventory, reproducible-build instructions, artifact digests, security findings, and an explicit hardware support matrix. Signing establishes who authorized an artifact, not whether it is correct.

## Gates and open decisions

Before an untrusted-application milestone, demonstrate access-control and memory-isolation invariants with negative tests. Before network exposure, fuzz every reachable parser and exercise exhaustion and cancellation. Before a production claim, independently review privileged code, unsafe interfaces, boot/update/recovery paths, compiler assumptions, and the complete supported hardware configuration.

Open decisions include capability representation and revocation, key custody, package trust policy, storage encryption format, authenticated IPC conventions, first isolated GPU, timing-channel mitigations, and update behavior without trustworthy time. Each decision requires a threat model, failure behavior, performance measurements, and a recorded review. Track inspection policy in [observability.md](observability.md); report vulnerabilities through [SECURITY.md](../SECURITY.md).
