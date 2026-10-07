#!/usr/bin/env python3
"""워커 스냅샷을 만든다: brief.md + sources/ 만 담고, 검증용 1회성 문자열을 심는다."""
from __future__ import annotations

import secrets
import shutil
import sys
from pathlib import Path


def build_snapshot(snapshot_root: Path, brief_text: str, source_files: dict[str, str]) -> str:
    """snapshot_root 아래에 brief.md와 sources/를 만들고, 심어 넣은 nonce 값을 돌려준다.

    source_files: {"파일명": "내용"} — 워커에게 보여줄 원본만 여기 담는다.
    다른 워커의 결과·로그·승인 상태는 이 함수의 인자로도 받지 않는다.
    """
    reserved = "source-access-proof.txt"
    for name in source_files:
        rel = Path(name)
        if rel.is_absolute() or ".." in rel.parts or name in {"", ".", reserved}:
            raise ValueError(f"허용되지 않는 소스 경로: {name}")
    snapshot_root.mkdir(mode=0o700, parents=True, exist_ok=False)
    sources_dir = snapshot_root / "sources"
    sources_dir.mkdir(parents=True)
    snapshot_root.chmod(0o700)

    nonce = secrets.token_hex(16)
    (snapshot_root / "brief.md").write_text(brief_text, encoding="utf-8")
    for name, content in source_files.items():
        target = sources_dir / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    (sources_dir / "source-access-proof.txt").write_text(nonce + "\n", encoding="utf-8")

    _assert_nonce_unique(snapshot_root, nonce)
    return nonce


def _assert_nonce_unique(snapshot_root: Path, nonce: str) -> None:
    hits = 0
    for path in snapshot_root.rglob("*"):
        if path.is_file():
            hits += path.read_text(encoding="utf-8", errors="replace").count(nonce)
    if hits != 1:
        raise RuntimeError(f"nonce가 스냅샷 전체에서 {hits}번 발견됨 — 정확히 1번이어야 한다")


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("./worker-snapshot")
    value = build_snapshot(
        root,
        brief_text=(
            "이 브리프에 실린 파일들만 근거로 리뷰하라. 응답 첫 줄에\n"
            "SOURCE_ACCESS_PROOF:<sources/source-access-proof.txt의 값>을 그대로 적어라."
        ),
        source_files={"target.py": "def add(a, b):\n    return a + b\n"},
    )
    print(f"snapshot 생성 완료: {root} (nonce는 출력하지 않음)")
