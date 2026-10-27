"""Check the foundation's required documents and local Markdown link targets."""

from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "README.md", "AGENTS.md", "CONTRIBUTING.md", "SECURITY.md",
    "docs/requirements.md", "docs/fit-mode.md", "docs/desktop-modes.md",
    "docs/architecture.md", "docs/hardware.md", "docs/graphics.md",
    "docs/performance.md", "docs/security.md", "docs/observability.md",
    "docs/toolchain.md", "docs/roadmap.md", "docs/decisions.md",
    "prototype/fit.py", "prototype/session.py", "prototype/controls.py",
    "prototype/demo.py", "tests/test_fit.py", "tests/test_session.py",
    "tests/test_controls.py", ".github/workflows/checks.yml",
)


def main() -> int:
    errors: list[str] = []
    for name in REQUIRED:
        path = ROOT / name
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"Required file missing/empty: {name}")

    documents = sorted(ROOT.glob("*.md")) + sorted((ROOT / "docs").rglob("*.md"))
    for document in documents:
        source = document.read_text(encoding="utf-8")
        # This repository uses simple inline links, not arbitrary Markdown HTML.
        for match in re.finditer(r"\[[^\]\n]+\]\(([^\s)]+)\)", source):
            raw = match.group(1).strip("<>")
            parsed = urlsplit(raw)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = (document.parent / unquote(parsed.path)).resolve()
            if not target.is_relative_to(ROOT):
                errors.append(f"Link escapes repository: {document.relative_to(ROOT)}: {raw}")
            elif not target.exists():
                errors.append(f"Broken local link: {document.relative_to(ROOT)}: {raw}")

    requirements = ROOT / "docs/requirements.md"
    if requirements.is_file():
        ids = re.findall(r"^\| (ONX-\d{3}) \|", requirements.read_text(encoding="utf-8"), re.M)
        expected = [f"ONX-{number:03}" for number in range(1, 18)]
        if sorted(ids) != expected:
            errors.append("Requirement table must contain ONX-001 through ONX-017 exactly once")

    if errors:
        print("\n".join(errors))
        return 1
    print(f"Repository checks passed: {len(REQUIRED)} required files, {len(documents)} Markdown documents, 17 requirement IDs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
