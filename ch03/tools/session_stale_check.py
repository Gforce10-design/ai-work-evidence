#!/usr/bin/env python3
"""SESSION.md 방치 감지기.

마감 신호 없이 세션이 끊기면 '현재 상태'가 낡은 채로 방치될 수 있다. 이 스크립트는
정답을 판정하지 않는다 — SESSION.md를 건드리지 않은 채 커밋이 N개 이상 쌓였다는
사실만 알린다. 최종 판단(낡았는지 아닌지)은 사람이 한다.

사용: python3 tools/session_stale_check.py [--threshold N] [SESSION.md 경로]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run(*args: str) -> str:
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout.strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default="SESSION.md")
    ap.add_argument("--threshold", type=int, default=5)
    args = ap.parse_args()

    path = Path(args.path)
    if not path.is_file():
        print(f"[INFO] {path} 없음 — 아직 세션 인계 파일을 안 쓰는 폴더입니다.")
        return 0

    last = run("git", "log", "-1", "--format=%H", "--", str(path))
    if not last:
        print(f"[INFO] {path} 이 아직 커밋되지 않았습니다.")
        return 0

    since = run("git", "rev-list", "--count", f"{last}..HEAD")
    n = int(since)
    if n >= args.threshold:
        print(f"[WARN] {path} 갱신 이후 커밋 {n}개 — 마감 신호 없이 세션이 끊겼을 가능성. "
              f"'현재 상태'를 실물과 대조하세요.")
        return 1
    print(f"[OK] {path} 갱신 이후 커밋 {n}개 (임계 {args.threshold})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
