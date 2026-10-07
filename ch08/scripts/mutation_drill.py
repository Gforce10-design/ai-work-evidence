#!/usr/bin/env python3
"""뮤테이션 드릴 — 가드를 일부러 깨뜨려 빨간불이 되는지 확인한다.

자기 완결형 예시다. 가짜 리뷰어 정의를 임시 폴더에 만들고, check_invariants.py가
지키는 불변식을 하나씩 망가뜨려 본다. 자기 프로젝트에 쓸 때는 MUTATIONS와 검사
대상만 바꾸면 된다. check_invariants.py는 이 파일과 같은 디렉터리에 있어야 한다.

규율:
1. 변이는 주장한 위험을 실제로 복원해야 한다.
2. 앵커(원본 조각)는 대상 파일에 정확히 한 번만 나타나야 한다.
3. 원본 상태에서는 위반이 0건이어야 한다(베이스라인이 이미 빨간불이면 무효).
4. 마지막 변경 뒤에 전수 스윕을 돌린다.
5. 심었을 때 빨간불, 치웠을 때 다시 초록불이어야 한다(양방향 확인).
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

CHECKER = Path(__file__).resolve().parent / "check_invariants.py"

CLEAN_REVIEWER_MD = """---
name: code-reviewer
description: 코드를 읽고 검토한다
tools: Read, Grep, Glob
---
코드를 읽고 문제만 지적한다. 고치지 않는다.
"""

# (라벨, 원본 조각, 망가뜨린 조각) — 자기 프로젝트의 위험으로 교체할 자리
MUTATIONS = [
    ("리뷰어에 Write 권한을 몰래 추가", "tools: Read, Grep, Glob", "tools: Read, Grep, Glob, Write"),
    ("리뷰어에 Bash 권한을 몰래 추가", "tools: Read, Grep, Glob", "tools: Read, Grep, Glob, Bash"),
]


def run_checker(agents_dir: Path) -> int:
    result = subprocess.run(
        [sys.executable, str(CHECKER), str(agents_dir)],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode not in (0, 1) or (result.returncode == 1 and "VIOLATION " not in result.stdout):
        return 2  # 인터프리터 오류를 위험 검출로 세지 않는다
    return result.returncode


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="mutation-drill-") as tmp:
        agents_dir = Path(tmp) / "agents"
        agents_dir.mkdir()
        target = agents_dir / "code-reviewer.md"
        target.write_text(CLEAN_REVIEWER_MD, encoding="utf-8")

        print("베이스라인 확인 (원본은 위반 0건이어야 함) ...")
        if run_checker(agents_dir) != 0:
            print("BASELINE RED — 원본부터 위반이 있다. 드릴을 멈춘다.")
            return 1

        if not MUTATIONS:
            print("INVALID — 변이 목록이 비었다")
            return 1
        caught = missed = 0
        for label, old, new in MUTATIONS:
            if run_checker(agents_dir) != 0:
                print("BASELINE RED — 매 변이 전 원본 확인 실패")
                return 1
            original = target.read_text(encoding="utf-8")
            if original.count(old) != 1:
                print(f"SKIP    {label} (앵커가 정확히 1번 나오지 않음 — 드릴이 낡았다)")
                return 1

            target.write_text(original.replace(old, new, 1), encoding="utf-8")
            try:
                mutation_result = run_checker(agents_dir)
                turned_red = mutation_result == 1
            finally:
                target.write_text(original, encoding="utf-8")  # 항상 원상복구

            recovered = run_checker(agents_dir) == 0

            if turned_red and recovered:
                print(f"caught  {label}  (심었을 때 빨간불, 치웠을 때 다시 초록불)")
                caught += 1
            elif mutation_result != 0:
                print(f"ERROR   {label}  (검사기 오류 — 위험 검출로 세지 않음)")
                missed += 1
            elif not turned_red:
                print(f"MISSED  {label}  (망가뜨렸는데도 초록불 — 이 가드는 이 위험을 안 본다)")
                missed += 1
            else:
                print(f"BROKEN  {label}  (복구 후에도 빨간불 — 드릴 자체가 고장)")
                missed += 1

        total = caught + missed
        print(f"\n{caught}/{total} 캐치")
        return 0 if missed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
