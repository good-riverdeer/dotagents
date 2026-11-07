"""Validate repo layout: skill frontmatter, symlinks, JSON files, leaked tokens.

Run: uv run --with pyyaml scripts/validate.py
"""
import json
import re
import sys
from pathlib import Path

import yaml

root = Path(__file__).resolve().parent.parent
errors: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


skills = sorted(p for p in (root / ".agents/skills").iterdir() if p.is_dir())
for d in skills:
    f = d / "SKILL.md"
    if not f.is_file():
        err(f"{d.name}: SKILL.md missing")
        continue
    m = re.match(r"---\n(.*?)\n---\n", f.read_text(), re.S)
    if not m:
        err(f"{d.name}: no frontmatter")
        continue
    fm = yaml.safe_load(m.group(1)) or {}
    if fm.get("name") != d.name:
        err(f"{d.name}: frontmatter name {fm.get('name')!r} != directory name")
    desc = fm.get("description")
    if not isinstance(desc, str) or not desc.strip():
        err(f"{d.name}: description missing")
    elif len(desc) > 1024:
        err(f"{d.name}: description {len(desc)} chars > 1024")

# every skill must be reachable from .claude/skills, and links must resolve
links = root / ".claude/skills"
for d in skills:
    link = links / d.name
    if not link.is_symlink() or link.resolve() != d.resolve():
        err(f".claude/skills/{d.name}: missing or wrong symlink")
for link in links.iterdir():
    if not link.exists():
        err(f".claude/skills/{link.name}: dangling symlink")

for name in (".claude/settings.json", "skills-lock.json"):
    try:
        json.loads((root / name).read_text())
    except Exception as e:  # noqa: BLE001
        err(f"{name}: invalid JSON ({e})")

lock = json.loads((root / "skills-lock.json").read_text())["skills"]
for name in lock:
    if not (root / ".agents/skills" / name).is_dir():
        err(f"skills-lock.json: {name} has no directory")

# SonarQube tokens (sqa_/sqp_/squ_) must never be committed
token = re.compile(r"\bsq[apu]_[0-9a-f]{40}\b")
for p in root.rglob("*"):
    if p.is_file() and ".git" not in p.parts and p.stat().st_size < 1_000_000:
        try:
            if token.search(p.read_text()):
                err(f"{p.relative_to(root)}: looks like a SonarQube token")
        except UnicodeDecodeError:
            pass

if errors:
    print("\n".join(f"FAIL {e}" for e in errors))
    sys.exit(1)
print(f"ok: {len(skills)} skills")
