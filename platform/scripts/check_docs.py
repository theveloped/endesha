"""Documentation coverage and link checker (`pixi run docs-check`).

Enforces the two promises platform/docs/README.md makes:

1. No floating docs: every markdown file in the repo (tracked or untracked,
   not gitignored) is reachable from the doc map — platform/docs/README.md —
   or from platform/CLAUDE.md, by following relative markdown links.
   Directory links do not count as coverage: files must be linked
   explicitly, which is what keeps the map an honest inventory.
2. No dead links: every relative link in a reachable doc resolves to an
   existing file or directory.

Exit code 1 if either promise is broken.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
EXCLUDE_PARTS = ("vendor", "node_modules", ".pytest_cache", "__pycache__")
ROOTS = ("platform/docs/README.md", "platform/CLAUDE.md")


def repo_root() -> Path:
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=True,
    )
    return Path(out.stdout.strip())


def all_md_files(root: Path) -> set[Path]:
    out = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard", "--", "*.md"],
        capture_output=True, text=True, check=True, cwd=root,
    )
    files = set()
    for line in out.stdout.splitlines():
        p = (root / line).resolve()
        if any(part in EXCLUDE_PARTS for part in Path(line).parts):
            continue
        if p.is_file():
            files.add(p)
    return files


def links_in(md: Path) -> list[str]:
    text = md.read_text(encoding="utf-8", errors="replace")
    return LINK_RE.findall(text)


def main() -> int:
    root = repo_root()
    universe = all_md_files(root)
    roots = [(root / r).resolve() for r in ROOTS]
    missing_roots = [r for r in roots if not r.is_file()]
    if missing_roots:
        for r in missing_roots:
            print(f"MISSING ROOT: {r.relative_to(root)}")
        return 1

    reachable: set[Path] = set()
    broken: list[str] = []
    queue = list(roots)
    while queue:
        doc = queue.pop()
        if doc in reachable:
            continue
        reachable.add(doc)
        for target in links_in(doc):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            path_part = target.split("#", 1)[0]
            if not path_part:
                continue
            resolved = (doc.parent / path_part).resolve()
            if not resolved.exists():
                broken.append(
                    f"{doc.relative_to(root)} -> {target} (missing)"
                )
                continue
            if resolved.suffix.lower() == ".md" and resolved.is_file():
                queue.append(resolved)

    orphans = sorted(
        p.relative_to(root) for p in (universe - reachable)
    )

    ok = True
    if broken:
        ok = False
        print("Broken links:")
        for b in sorted(broken):
            print(f"  {b}")
    if orphans:
        ok = False
        print("Orphaned docs (not reachable from the doc map — link them")
        print("from platform/docs/README.md or delete them):")
        for o in orphans:
            print(f"  {o}")
    if ok:
        print(
            f"docs-check OK: {len(reachable)} docs reachable, "
            f"{len(universe)} in repo, no broken links."
        )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
