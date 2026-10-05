#!/usr/bin/env python3
"""리뷰어 역할 서브에이전트가 쓰기 도구를 갖지 않는지 확인한다.

결정: 리뷰어가 코드를 쓸 수 있으면 자기가 만든 결함을 자기가 통과시킬 수 있다.
      그래서 리뷰 역할은 읽기전용이어야 한다.
불변식: agents 디렉터리의 서브에이전트 정의 중 이름에 "review"가 들어간 것은
        frontmatter tools를 Read/Grep/Glob의 부분집합으로 명시한다.
        이 예제는 한 줄 쉼표 목록만 지원하고 다른 표기는 거부한다.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# 이 예제는 쉼표 구분 한 줄 tools만 받는다. 미지원 YAML을 추측하지 않는다.
READ_TOOLS = {"Read", "Grep", "Glob"}


def find_violations(agents_dir: Path) -> list[str]:
    violations = []
    reviewed = 0
    for path in sorted(agents_dir.glob("*.md")):
        if "review" not in path.stem.lower():
            continue
        reviewed += 1
        text = path.read_text(encoding="utf-8")
        front = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.S)
        rows = re.findall(r"^tools:[ \t]*(.*)$", front[1], re.M) if front else []
        if len(rows) != 1 or not rows[0].strip():
            violations.append(f"{path}: tools 허용 목록 누락·중복")
            continue
        declared = [tok.strip() for tok in rows[0].split(",")]
        if any(tok not in READ_TOOLS for tok in declared):
            violations.append(f"{path}: 허용하지 않거나 해석하지 못한 tools {declared}")
    if reviewed == 0:
        violations.append(f"{agents_dir}: 이름에 review가 든 검사 대상 없음")
    return violations


def main(argv: list[str]) -> int:
    agents_dir = Path(argv[1] if len(argv) > 1 else ".claude/agents")
    if not agents_dir.is_dir():
        print(f"{agents_dir} 없음 — 판정 불가")
        return 2
    violations = find_violations(agents_dir)
    for line in violations:
        print(f"VIOLATION {line}")
    print(f"\n{len(violations)}건 위반")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
