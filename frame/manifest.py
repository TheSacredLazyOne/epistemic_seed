from __future__ import annotations
from pathlib import Path
from typing import List
import json
import re

ROOT = Path(__file__).resolve().parents[1]


def _files_in(dir_rel: str) -> List[Path]:
    d = ROOT / dir_rel
    if not d.exists():
        return []
    return sorted(
        [p for p in d.iterdir() if p.is_file() and p.suffix == ".md"],
        key=lambda p: p.name,
    )


def _rfiles_in(dir_rel: str) -> List[Path]:
    d = ROOT / dir_rel
    if not d.exists():
        return []
    return sorted(
        [p for p in d.rglob("*.md") if p.is_file()],
        key=lambda p: str(p.relative_to(ROOT)),
    )


# ---------------------------------------------------------------------------
# Manifest-owned metadata
# ---------------------------------------------------------------------------

def frame_schema() -> str:
    return "v0"


def node_name() -> str:
    p = ROOT / "seed_node.json"
    if not p.exists():
        return "node"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        name = data.get("name")
        return str(name).strip() if isinstance(name, str) and name.strip() else "node"
    except Exception:
        return "node"


def _safe_slug(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_\-]+", "", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "node"


def artifact_dir() -> str:
    return "dist"


def artifact_basename(mode: str) -> str:
    # Single underscore separator (no double __)
    return f"{_safe_slug(node_name())}_frame_{mode}"


def repository_url() -> str | None:
    p = ROOT / "seed_node.json"
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        repo = data.get("repository")
        return str(repo).strip() if isinstance(repo, str) and repo.strip() else None
    except Exception:
        pass

    # Fallback — structural default
    return 'https://github.com/TheSacredLazyOne/epistemic_seed'


def license_name() -> str:
    """
    Returns declared license from seed_node.json.
    Falls back to CC-BY-SA-4.0 if absent.
    """
    p = ROOT / "seed_node.json"
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            lic = data.get("license")
            if isinstance(lic, str) and lic.strip():
                return lic.strip()
        except Exception:
            pass

    # Fallback — structural default
    return "CC-BY-SA-4.0"


# ---------------------------------------------------------------------------
# Frame definition
# ---------------------------------------------------------------------------

def build_node_frame() -> List[Path]:
    items: List[Path] = []

    # Identity first
    items += [ROOT / "seed_node.json"]

    # Root docs
    items += [ROOT / "README.md", ROOT / "LINEAGE.md", ROOT / "version.md"]

    # Governance + vocabulary
    items += _files_in("governance")
    items += _files_in("propositions")

    return [p for p in items if p.exists()]


def build_bundle(mode: str) -> List[Path]:
    items = build_node_frame()

    if mode == "derivative":
        items += _rfiles_in("derivative")
    elif mode == "all":
        items += _rfiles_in("integrated")
        items += _rfiles_in("derivative")
    elif mode != "none":
        raise ValueError(f"Unknown bundle mode: {mode}")

    seen = set()
    out: List[Path] = []
    for p in items:
        rp = p.resolve()
        if rp in seen:
            continue
        seen.add(rp)
        out.append(p)
    return out