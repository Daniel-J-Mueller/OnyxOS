# OnyxOS contributor instructions

- This is an original OS research repository. Keep architecture proposals, host reference models, native implementations, and measured evidence explicitly distinct.
- Preserve the requirements in `docs/requirements.md`, especially reversible Fit Mode, no shell animations or artificial delays, safe allocation, activity attribution, and hardware portability.
- Hardware compatibility means hardware on which Ubuntu/Windows can run. Do not silently expand that into application/guest compatibility or imply it is implemented.
- Host Python is temporary research scaffolding. Do not make it a future boot/runtime dependency. Follow `docs/toolchain.md` before adding native language/compiler dependencies.
- Do not assert fastest, memory-safe, secure, formally verified, bootable, or supported-hardware status without scoped evidence.
- Test meaningful invariants, fault cases, resource bounds, and regressions. Record benchmark environment and distribution, not just a best sample.
- No credentials, private user files, machine images, dumps, or signing keys in Git. Keep license decisions explicit; do not add third-party code without provenance.
- Run `python -m unittest discover -s tests -v`, `python -m prototype.demo`, and `python tools/check_repository.py` before publishing changes to this foundation.
- Do not modify the enclosing workspace's personal website or job-search content. This directory is a separate Git repository.
