# Initial decisions and open questions

These are design decisions, not claims of an existing implementation. Revise them with evidence and requirement impact.

| Decision | Rationale | Revisit when |
| --- | --- | --- |
| Original OS with a small capability-oriented kernel proposal | Bound privileged code and make resource ownership explicit; isolate failure-prone services | Measured IPC/driver workloads show unacceptable latency or the security boundary cannot be enforced |
| Hardware compatibility only | Owner clarified Ubuntu/Windows refers to machines able to run them | Owner explicitly requests binary or guest compatibility |
| Fit is reversible, independent of presets | A single toggle must reliably return the desktop to its prior state | A lifecycle/topology change makes exact restoration impossible; document fallback |
| Adapt content/render size before physical mode changes | Preserve image quality and avoid unnecessary display disruption | User opts into a tested physical mode policy |
| Zero decorative shell animation | Responsiveness is an explicit founding requirement | Do not relax without owner direction |
| Original small systems language, measured bootstrap | Own semantics and safety boundaries without assuming handwritten code is faster | Prototype evidence identifies a better minimal backend or safety design |
| Python host model only | Test interaction/layout rules immediately without choosing the target ABI prematurely | Native language/toolchain passes its validation gate |
| Separate architecture binaries from shared source | CPU instruction sets and firmware differ | Add supported ISA/platform with published tests |
| License pending | Public visibility is authorized, licensing terms were not specified | Owner selects distribution and contribution policy |

## Decisions still requiring research

Compiler source language, bootstrap trust chain, exact ownership/borrow rules and failure semantics; syscall and message ABI; scheduler policy and priority inversion strategy; filesystem format and crash consistency; supported physical GPU family; driver provenance/firmware redistribution; application/package ABI; signing key custody and recovery ownership; initial reference PC and Raspberry Pi board; accessibility validation participants; reproducible build tool versions; stable public API versioning; measured threshold for replacing a prototype.

Do not let this list hide dependencies: hardware graphics support, compiler correctness, drivers, update recovery and application availability are major project workstreams. The [roadmap](roadmap.md) defines promotion gates. Each future decision record should include context, alternatives, safety implications, performance evidence, compatibility impact and a rollback strategy.
