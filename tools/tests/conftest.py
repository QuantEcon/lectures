"""Scratch repositories for the tools/ tests.

Each test builds a small repository in a temp dir — ``mirror/<series>/
lectures/``, ``sync/manifest.yml``, ``sync/state.yml``, an empty pool — and
copies the real ``tools/promote`` and ``tools/drift-check`` into it. The tools
resolve every path from their own location, so a copy runs against the
scratch repository and never touches the real mirror, pool or ledger. They are
run as subprocesses, exactly as CI runs them.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

TOOLS_DIR = Path(__file__).resolve().parent.parent


def fake_sha(series: str, n: int = 1) -> str:
    """A deterministic 40-hex pin per series (``n`` moves it)."""
    return hashlib.sha1(f"{series}:{n}".encode()).hexdigest()


def lecture_text(title: str, body: str = "", refs=()) -> str:
    """A minimal MyST lecture; ``refs`` become markdown image references."""
    lines = ["---", "jupytext:", "  text_representation:", "    extension: .md", "---", "", f"# {title}", ""]
    if body:
        lines += [body, ""]
    for ref in refs:
        lines += [f"![figure]({ref})", ""]
    return "\n".join(lines)


class ScratchRepo:
    def __init__(self, root: Path, series, consumers=()):
        self.root = root
        self.order = list(series)
        (root / "tools").mkdir(parents=True)
        for name in ("promote", "drift-check"):
            shutil.copy(TOOLS_DIR / name, root / "tools" / name)
        (root / "sync").mkdir()
        (root / "lectures").mkdir()
        for key in self.order:
            (root / "mirror" / key / "lectures").mkdir(parents=True)
        self.write_manifest(consumers)
        self.write_state({key: fake_sha(key) for key in self.order})

    # -- inputs ------------------------------------------------------------ #
    def write_manifest(self, consumers=()):
        lines = ["defaults:", "  branch: main", "series:"]
        for key in self.order:
            lines += [f"  {key}:", f"    repo: test/{key}"]
            if key in consumers:
                lines.append("    class: consumer")
        (self.root / "sync" / "manifest.yml").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def write_state(self, pins):
        state = {key: {"sha": sha, "synced_at": "2026-10-06T00:00:00Z"} for key, sha in pins.items()}
        (self.root / "sync" / "state.yml").write_text(yaml.safe_dump(state, sort_keys=False), encoding="utf-8")

    def pin(self, series):
        state = yaml.safe_load((self.root / "sync" / "state.yml").read_text(encoding="utf-8"))
        return state[series]["sha"]

    def move_pin(self, series, n=2):
        state = yaml.safe_load((self.root / "sync" / "state.yml").read_text(encoding="utf-8"))
        state[series]["sha"] = fake_sha(series, n)
        (self.root / "sync" / "state.yml").write_text(yaml.safe_dump(state, sort_keys=False), encoding="utf-8")

    def write_canonical_map(self, mapping):
        text = "# test canonical map\n" + "".join(f"{slug}: {series}\n" for slug, series in mapping.items())
        (self.root / "sync" / "canonical.yml").write_text(text, encoding="utf-8")

    def mirror_file(self, series, rel, data):
        path = self.root / "mirror" / series / "lectures" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, str):
            data = data.encode("utf-8")
        path.write_bytes(data)
        return path

    def lecture(self, series, slug, text):
        return self.mirror_file(series, f"{slug}.md", text)

    def toc(self, series, slugs):
        chapters = "".join(f"  - file: {slug}\n" for slug in slugs)
        self.mirror_file(series, "_toc.yml", f"format: jb-book\nroot: intro\nchapters:\n{chapters}")

    # -- running ----------------------------------------------------------- #
    def run(self, tool, *args):
        return subprocess.run(
            [sys.executable, str(self.root / "tools" / tool), *args],
            capture_output=True,
            text=True,
            cwd=str(self.root),
        )

    def promote(self, *args):
        return self.run("promote", *args)

    def drift_check(self, *args):
        return self.run("drift-check", *args)

    # -- outputs ----------------------------------------------------------- #
    @property
    def ledger_path(self):
        return self.root / "sync" / "ledger.yml"

    def ledger(self):
        return yaml.safe_load(self.ledger_path.read_text(encoding="utf-8"))

    def entry(self, slug):
        return self.ledger()[f"lectures/{slug}.md"]

    def pool(self, rel):
        return self.root / "lectures" / rel


@pytest.fixture
def make_repo(tmp_path):
    """``make_repo(series, consumers=())`` -> a ScratchRepo; ``series`` is the
    manifest order (= dedup priority)."""
    count = {"n": 0}

    def factory(series, consumers=()):
        count["n"] += 1
        return ScratchRepo(tmp_path / f"repo{count['n']}", series, consumers)

    return factory
