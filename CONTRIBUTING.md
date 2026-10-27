# Contributing

OnyxOS begins with a specification and host reference model. See [the roadmap](docs/roadmap.md) before adding a subsystem. Licensing is pending; propose designs or discuss licensing with the owner before contributing external implementation code.

## A useful change

Identify the requirement ID, observable behavior, implementation status, resource bounds, and failure policy. Include a small reproducible example. Explain when the proposed optimization loses and whether a fallback is required. Changes to unsafe code, memory ownership, privilege boundaries, or GPU synchronization need an explicit invariant and independent review.

Architectural proposals belong in a decision record with alternatives and evidence. Do not replace a whole subsystem merely because a language or kernel structure is expected to be faster.

## Host checks

From the repository root, with Python 3.11 or later:

```sh
python -m unittest discover -s tests -v
python -m prototype.demo
python tools/check_repository.py
```

The CI workflow runs these checks on Linux and Windows. It does not boot OnyxOS, validate GPU hardware, or establish OS performance. Native milestones must add real boot tests, fault injection, compiler tests, and representative hardware measurements as appropriate.

## Measurements

Use [the performance protocol](docs/performance.md). Preserve raw timing data, test source revision, hardware/firmware, clock policy, workload, warm/cold state, and the full latency distribution. Separate host reference timings from target OS measurements. Store large artifacts in release/CI artifact storage, never Git history.

## Security reports

Follow [SECURITY.md](SECURITY.md). Never publish signing keys, exploit credentials, personal data, or memory dumps containing secrets.
