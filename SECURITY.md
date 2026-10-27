# Security policy

OnyxOS is an early research and design project. There is no supported production OS release, bootable kernel, implemented custom compiler, or verified security boundary. Design documents describe intended properties. Host-side prototypes and repository automation can still contain vulnerabilities and should be reviewed as executable software.

## Reporting a vulnerability

Private vulnerability reporting is enabled for this repository. Use [Security / Report a vulnerability](https://github.com/Daniel-J-Mueller/OnyxOS/security/advisories/new) to submit a private report. Enablement is a repository setting and must remain available as the project evolves. See [GitHub's private reporting instructions](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/report-privately).

If that option is unavailable, use a contact method the repository owner publishes on their GitHub profile. If no private method is available, open an issue asking only for a private security contact; omit exploit details, secrets, and sensitive data from that public issue. No security email address or response-time commitment has been established.

Include the affected revision, component, expected and actual behavior, impact, and a minimal reproducible example that contains no unrelated personal data. Include the host environment or proposed platform assumptions when relevant. Clearly distinguish an implemented-code defect from a concern about a proposed design.

Avoid testing against other people's systems or data. Use disposable local test data for reproduction and disclose only the access needed to explain the issue.

## Project handling

Maintainers should acknowledge and assess reports, agree on disclosure where possible, track the fix and regression evidence, and publish an advisory for confirmed vulnerabilities affecting released artifacts when appropriate. No bug bounty, fixed response deadline, maintenance window, or supported-version matrix is currently promised.

Before a production release, publish supported versions and security-update expectations, verify the private reporting channel, document release signing and recovery, and review the threat model in [docs/security.md](docs/security.md).
