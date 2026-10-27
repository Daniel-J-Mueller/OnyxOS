# Native desktop modes

A mode is a declarative Onyx shell policy: panel placement, visible controls, launcher arrangement, layout rules, density, accessibility and output assignments. Switching a policy does not replace the kernel, restart applications, change their trust boundaries, or execute another operating system.

## Controls

| Action | Proposed keyboard default | Pointer/touch access |
| --- | --- | --- |
| Toggle Fit Mode | F8 | Labeled Fit button |
| Previous preset | F9 | Visible previous button |
| Next preset | F10 | Visible next button |
| Choose a preset directly | User-configurable | Labeled mode chooser |

All bindings are remappable; these are defaults awaiting usability testing. The previous and next buttons satisfy switching without a key binding. Controls remain discoverable in compact mode via labels/focus/approach expansion. Fit state is orthogonal to preset selection: cycling presets does not overwrite the saved standard geometry. Persist selected preset and fit policy independently.

## Initial design presets

| Preset | Intended behavior |
| --- | --- |
| Standard | Floating windows with compact stable controls |
| Focus | Prioritize the active application and nearby task navigation |
| Workbench | Dense tiled work areas and persistent task/context tools |
| Ubuntu-inspired | Familiar top bar/launcher placement implemented with native Onyx components |
| Accessible | Larger explicit targets, persistent labels and customizable density; no decorative animation |
| Headless | No compositor; retain administration and observable activity APIs |

Names and policies are proposals. An Ubuntu-inspired preset is not GNOME, an Ubuntu image, or Linux binary compatibility. Importing a third-party desktop later would require its runtime, APIs, licensing and a separate compatibility decision.

## Transaction and failure behavior

Validate the entire preset against resource quotas and accessibility requirements before switching. Stage geometry and focus changes as one scene transaction. Keep the current preset if validation or a critical component fails; report the reason immediately. Preserve process identities, open documents, input focus and window ownership. Rebuild a crashed shell from the last committed policy without killing unrelated applications.

Keep a small bounded amount of preset metadata ready; do not preload every desktop's applications or consume VRAM merely to make a switch look fast. Measure cold and warm switching separately. A real client resize may complete later; keep the existing buffer visible with a pending indicator and bounded fallback.

Provide a secure recovery action that restores a known accessible shell profile. If the compositor fails, recovery and administration must remain available through an independent console. Authenticate privileged actions; instant feedback does not remove authorization checks.

## Application contract

Versioned native UI messages describe semantic actions, text, focus order, min/preferred geometry, content bounds, scale constraints and accessibility information. Applications retain their own content/rendering choices. An application may animate or wait for its own UX, but shell APIs add no transition or mandatory delay. Timing/synchronization needed for correctness is not an animation.

The initial model tests preset index cycling separately from geometry. It does not render these presets or implement a native UI protocol.
