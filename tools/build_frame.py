# tools/build_frame.py
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[1]


def git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        return "UNKNOWN"


def load_manifest_module():
    manifest_path = ROOT / "frame" / "manifest.py"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing manifest: {manifest_path}")

    spec = importlib.util.spec_from_file_location("node_manifest", manifest_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore
    return mod


def relpath(p: Path) -> str:
    return p.resolve().relative_to(ROOT.resolve()).as_posix()


def section_for(rel: str) -> str:
    if rel.startswith("integrated/"):
        return "INTEGRATED REFERENCES"
    if rel.startswith("derivative/"):
        return "DERIVATIVE REFERENCES"
    return "FRAME"


def dirkey(rel: str) -> str:
    p = Path(rel)
    parent = p.parent.as_posix()
    return parent if parent != "." else "ROOT"


def demote_headings(md: str, levels: int) -> str:
    out_lines: List[str] = []
    for line in md.splitlines():
        if line.startswith("#"):
            n = 0
            while n < len(line) and line[n] == "#":
                n += 1
            if 1 <= n <= 6 and n < len(line) and line[n] == " ":
                new_n = min(6, n + levels)
                line = ("#" * new_n) + line[n:]
        out_lines.append(line)
    return "\n".join(out_lines)


def render_file(src: Path) -> str:
    raw = src.read_text(encoding="utf-8").rstrip()
    suf = src.suffix.lower()

    if suf == ".md":
        # IMPORTANT: demote by 3 so file content nests properly
        return demote_headings(raw, levels=3) + "\n"

    if suf == ".json":
        try:
            obj = json.loads(raw)
            pretty = json.dumps(obj, indent=2, ensure_ascii=False).rstrip()
        except Exception:
            pretty = raw

        if src.name == "seed_node.json":
            return f"<!-- seed_node.json -->\n```json\n{pretty}\n```\n"
        return f"```json\n{pretty}\n```\n"

    return f"```text\n{raw}\n```\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="Build a compiled node markdown artifact.")
    ap.add_argument("--bundle", choices=["none", "derivative", "all"], default="none")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    mod = load_manifest_module()

    files: List[Path] = mod.build_bundle(args.bundle)

    default_out = f"{mod.artifact_dir()}/{mod.artifact_basename(args.bundle)}.md"
    out_rel = args.out or default_out

    out_path = ROOT / out_rel
    out_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure dist exists

    head = git_head()
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"

    parts: List[str] = []
    parts.append("# Node\n\n")
    parts.append(f"> Node: {mod.node_name()}\n")
    parts.append(f"> Repository: {mod.repository_url()}\n") 
    parts.append(f"> Source commit: `{head}`\n")
    parts.append(f"> License: {mod.license_name()}\n")
    parts.append(f"> Frame schema: {mod.frame_schema()}\n")
    parts.append(f"> Generated: {now}\n")
    parts.append(f"> Bundle mode: `{args.bundle}`\n\n")
    parts.append("---\n\n")

    current_section: str | None = None
    current_dir: str | None = None

    for src in files:
        if not src.is_absolute():
            src = (ROOT / src).resolve()

        rel = relpath(src)
        sec = section_for(rel)

        if sec != current_section:
            current_section = sec
            current_dir = None
            parts.append(f"\n\n# {current_section}\n\n")

        dk = dirkey(rel)
        if dk != current_dir:
            current_dir = dk
            parts.append(f"\n\n## Directory: `{dk}`\n\n")

        parts.append("\n---\n\n")
        parts.append(f"### `{rel}`\n\n")
        parts.append(render_file(src))

    out_path.write_text("".join(parts), encoding="utf-8")
    print(f"Wrote {out_rel}")


if __name__ == "__main__":
    main()