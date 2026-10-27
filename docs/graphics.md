# Graphics and presentation design

Status: proposed interfaces and verification requirements. Hardware acceleration and latency targets have not been demonstrated.

The objective is to minimize work and latency while preserving correctness, readable text and predictable interaction. GPU acceleration is already present in comparable systems, including Windows' composition APIs; Onyx must establish any improvement with comparable measurements. [Microsoft DirectComposition overview](https://learn.microsoft.com/en-us/windows/win32/directcomp/why-use-directcomposition-)

## Display pipeline

Applications submit surfaces and optional semantic layout information to an isolated compositor. The compositor validates handles and dimensions, resolves visible damage, prepares composition work, and submits a display transaction. A separate device service owns display configuration, GPU queues and recovery. Input processing remains independent of rendering so a blocked client cannot freeze navigation.

The initial renderer uses a software framebuffer for correctness and recovery. Add a virtual display backend, then an accelerated backend with explicitly measured CPU time, GPU time and memory traffic. Software and hardware paths implement the same surface and presentation contract. A driver failure returns to a working fallback when the platform permits it, and reports a clear fault when it does not.

Design the native display transaction API around validated whole-state changes, planes, supported pixel formats, explicit synchronization, damage information and presentation timestamps. Linux KMS documents these concepts and the hardware limits of atomic changes; it is a reference, not an Onyx dependency. Full mode changes can require display blanking, which is why Fit mode must not routinely change physical timing. [Linux KMS documentation](https://docs.kernel.org/gpu/drm-kms.html)

## Minimize unnecessary work

| Mechanism | Proposed behavior | Correctness condition |
| --- | --- | --- |
| Damage tracking | Redraw changed visible regions; coalesce overlapping damage | Invalidate for movement, resize, occlusion, color and transform changes |
| Occlusion | Skip fully covered opaque content | Respect alpha, rounded edges, capture and accessibility overlays |
| Direct scanout | Present a compatible application's buffer without compositing | Layout, format, synchronization, protection and overlays all permit it |
| Hardware planes | Assign compatible surfaces to available planes | Validate bandwidth, scaling, color and plane constraints as a transaction |
| Shared buffers | Import explicitly authorized buffers without redundant copies | Producer/consumer ownership and mapping lifetime remain valid |
| Explicit fences | Wait only for dependencies needed for the selected frame | Never present an incomplete or reused buffer |
| Bounded buffering | Begin with at most two reusable buffers per simple surface; permit a bounded third when justified | No reuse before completion; quota covers extra buffering |
| Cached glyphs and assets | Reuse rasterized glyphs and unchanged image data | Evict within quota; invalidate when scale/font/color changes |
| Idle behavior | Submit nothing for a truly unchanged desktop | Device refresh continues independently; no shell timer produces empty frames |
| Adaptive batching | Merge work only within the active deadline | No fixed batching delay added to input or a ready frame |

Use the GPU where it reduces end-to-end cost; small operations can be cheaper on the CPU. Avoid forced GPU readbacks, synchronous round trips and excessive state changes on the interactive path. Measure the break-even point instead of assuming every task improves when moved to a GPU. Keep GPU queue admission bounded so compute jobs cannot indefinitely delay desktop presentation on shared hardware.

## Fit mode and resolution

Fit mode primarily changes logical layout, content viewport and application rendering scale. The panel stays at a stable native resolution and refresh timing by default. App surfaces can be reallocated at the required pixel size after scale negotiation. This is the proposed meaning of automatic resolution adjustment in the first native implementation; the current host model does not control a display.

1. Snapshot window placement, focus, per-output scale and application layout state.
2. Determine usable rectangles, semantic minimum sizes, aspect-ratio constraints and accessibility limits.
3. Compute a deterministic layout that minimizes unused space under those constraints.
4. Ask responsive applications to reflow and render at the new surface size; apply a bounded fallback to clients that cannot reflow.
5. Commit the layout atomically at the next feasible presentation boundary with zero transition animation.
6. Restore the standard-mode snapshot when the same toggle is invoked again, adapting safely if monitors changed.

Two to three physical pixels are the normal visual separator budget in Fit mode. This is not permission to crop image pixels, remove meaningful margins inside documents, shrink text below the user's minimum, or reduce hit targets to that width. Separate visible chrome from input regions. Artwork preserves aspect ratio unless the app/user requests another policy; unavoidable letterboxing remains preferable to distortion or hidden content.

Arbitrary existing application pixels do not expose the meaning of controls or internal whitespace. Perfect packing is therefore a constrained objective, not a universal guarantee. Native applications provide layout hints and semantic controls. Fixed-layout content is scaled only within readability limits; overflow uses explicit scrolling or an alternate arrangement. Record unused area, constraint violations and resizing cost so the heuristic can improve without concealing compromises.

Physical mode switching is an optional explicit policy for displays that support it. Enumerate validated modes, preserve a known-working fallback, handle hotplug and expose recovery if the mode fails. It must not be required for the core Fit toggle or desktop-preset switching.

## Interaction and accessibility

Control enlargement is an immediate geometry change driven by pointer position and motion direction, with no tween, easing or dwell timer. A compact visual control can have a larger stable hit region. Use spatial hysteresis and a locked active target to prevent flicker or buttons fleeing the pointer; neither requires a time delay. Expanded controls overlay reserved interaction space where possible so unrelated content does not repeatedly reflow.

Do not require movement prediction for correctness. Controls remain reachable through keyboard focus, touch, assistive technology and a persistent-controls setting. The user can set minimum text size, control size, contrast and magnification. Dangerous actions keep stable identity and activation semantics during enlargement. A desktop preset switch uses the same input and application session, and never implicitly changes app permissions.

Support output-specific scale, rotation and color state. Test mixed DPI, multiple monitors, screen capture, remote display, text shaping, bidirectional text, IME, touch and keyboard-only use before broad desktop support. Screen capture and remote viewing require explicit authority; direct scanout must transition correctly when capture begins.

## Required graphics evidence

Correctness tests cover buffer ownership, damage invalidation, clipping, fractional-scale rounding, geometry reversibility, hotplug, focus stability, hung applications and GPU reset. Pixel comparison against the software reference is useful where rendering semantics match. Performance traces separate input receipt, app work, layout, CPU submission, GPU completion, compositor selection and actual presentation. High-speed camera or photodiode measurement is required for input-to-photon claims; a completed GPU fence is not a visible pixel.
