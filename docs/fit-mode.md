# Fit Mode

This is the target behavior specification. The Python model exercises only a bounded subset of layout and input state; it is not a compositor or global packing solver.

## One reversible action

The proposed default is **F8**, remappable to one key or a combination. A visible Fit control invokes the same action. Suppress key repeat so a held key does not toggle repeatedly. Respect explicit user-approved shortcut overrides and expose conflicts; remote sessions and games need a documented escape path.

Entering Fit Mode saves per-window stable identity/generation, outer bounds, output, workspace, stacking order, state, focus and layout policy. Apply the candidate layout atomically only after validation. Exiting restores the snapshot for surviving windows. Windows created while fitting receive their recorded standard placement; closed windows are not resurrected. Output removal clamps affected windows into the surviving work area and reports why exact restoration was impossible. The initial host model does not implement all of these lifecycle cases.

## What gets fitted

1. Compute usable output area after explicit reserved surfaces, cutouts and accessibility needs. Use integer physical pixels for final bounds.
2. Obtain client minima, preferred size/aspect, resize increments, semantic content bounds, text scale and allowed layout policies. Treat these as untrusted bounded data. A legacy framebuffer is opaque: the compositor cannot safely infer its blank margins or reflow its controls.
3. Search a bounded candidate family with a deterministic ordering. Keep focused content legible, keep windows disjoint, honor minimum sizes, and keep image content intact. Use reusable storage and a configurable work budget.
4. Score feasible candidates lexicographically: hard constraints first; then weighted useful content area; then stability and predictable navigation; then the cost of rerendering. Avoid moving every window when one changes.
5. Negotiate a complete resize generation and commit when ready. A missed client deadline leaves the previous valid scene visible and marks the client pending; it does not freeze input or publish half a layout. Cancel stale generations and bound outstanding work.

Layout search may stop with the best feasible candidate. Report **no feasible candidate found in this family** separately from proven global infeasibility. If minima do not fit, offer another workspace, a focused view, or user-selected scaling. Never silently truncate content or make essential text unreadable.

Measure `output area = reserved area + outer-window area + unassigned area` and `outer-window area = border area + content area + letterbox area`. Do not count letterboxing, chrome, padding, or a background fill as useful content. Pixel rounding must be deterministic and area accounting exact. A real application may contain internal whitespace that the compositor cannot measure.

## Borders, images and resolution

Default outer framing is 2 physical pixels; 3 is an alternative. Focus outlines may use the same footprint with stronger contrast. Touch hit regions and resize affordances can be larger than painted borders. Transparent resize targets must not steal unrelated content input. Image aspect ratio is preserved; letterboxing is visible and measured. Cropping requires an explicit application/user operation.

Keep three independent quantities explicit:

| Quantity | Fit policy |
| --- | --- |
| Display scanout resolution and refresh rate | Preserve the native/current mode by default. An opt-in display policy may select only advertised, validated modes; use recovery/revert if confirmation fails. Link retraining and black frames are physical limits. |
| Logical content size and UI scale | Negotiate client reflow and readable density within declared limits. Remember user accessibility settings. |
| Render buffer resolution | Ask a cooperative client to rerender at the appropriate pixel density; use bounded temporary scaling only while waiting. Avoid repeated lossy resampling. |

This satisfies adaptive sizing without assuming a lower physical resolution creates more usable area. Multi-monitor scaling is per output, including mixed DPI, rotation and fractional scale. Physical borders round after transformation. The model is single-output and does not implement buffer negotiation or modesetting.

Wayland's surface/buffer scale distinction is a useful existing design reference, not a declaration that Onyx implements that protocol. See [Wayland surface scale semantics](https://wayland.freedesktop.org/docs/html/apa.html#protocol-spec-wl_surface).

## Approach-to-expand controls

Each action has a stable anchor, compact painted glyph, larger acquisition region, expanded hit rectangle and accessible label. Estimate approach from successive pointer samples using direction toward the anchor and decreasing distance. Expansion is a discrete state change on the next update, with no tween, delay, or dwell requirement. Proximity entry, keyboard focus and touch activation provide paths that do not depend on predicting movement.

Use spatial hysteresis: retain an expanded target while the pointer remains in its expanded retention region. Expansion overlays reserved UI space rather than pushing application content away from the pointer. Latch the selected target on pointer-down and retain it until release/cancel; never transfer a held click to a neighbor. Resolve overlapping acquisition regions deterministically and reveal only one active target per group. Destructive actions require deliberate activation, never mere approach.

Compact appearance does not require tiny interaction areas. A provisional desktop floor is 24 logical units with a larger touch profile and user-adjustable scale. This is a design benchmark inspired by [WCAG 2.2 target size](https://www.w3.org/TR/WCAG22/#target-size-minimum), which is expressed in CSS pixels for web content; it is not an OS compliance claim or a physical-pixel equivalence.

## Acceptance scenarios

- Odd output dimensions, one and many windows, 2/3-pixel borders, stable ordering and exact area sums.
- Minimum-size conflicts, extreme aspect ratios, a portrait display and content that cannot reflow.
- Rapid repeated toggles, key repeat, resize during fitting, client timeout, close/create, and output hot unplug.
- Pointer reversal, slow approach, tremor, high velocity, adjacent controls, click/drag capture, keyboard-only and touch-only use.
- Mixed DPI, screen readers, magnification, right-to-left layouts, non-Latin text, focus indicators and high contrast.
- No decorative animation, no crop, no overlap or out-of-output bounds, and no stale geometry generation.

Host tests cover some of the first, second and pointer-state cases. Native integration and user studies are required for the rest.
