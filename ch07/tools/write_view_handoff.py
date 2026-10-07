#!/usr/bin/env python3
"""읽기전용 뷰(클론)의 실제 경로를 스냅샷 루트에 적어 넘긴다."""
from __future__ import annotations

from pathlib import Path


def write_view_handoff(snapshot_root: Path, view_path: Path) -> None:
    view_path = view_path.resolve()
    if not view_path.is_dir():
        raise RuntimeError(f"뷰 경로가 존재하지 않음: {view_path}")
    (snapshot_root / "repo-view-path.txt").write_text(str(view_path) + "\n", encoding="utf-8")


def verify_view_handoff(snapshot_root: Path) -> Path:
    handoff = snapshot_root / "repo-view-path.txt"
    if not handoff.exists():
        raise RuntimeError("repo-view-path.txt 없음 — 뷰 경로를 워커에게 건네지 않았다")
    value = handoff.read_text(encoding="utf-8").strip()
    if not value or not Path(value).is_absolute():
        raise RuntimeError("뷰 경로는 비어 있지 않은 절대경로여야 한다")
    view_path = Path(value)
    if not view_path.is_dir():
        raise RuntimeError(f"기록된 뷰 경로가 실존하지 않음: {view_path}")
    return view_path
