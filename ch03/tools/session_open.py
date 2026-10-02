#!/usr/bin/env python3
"""세션 시작 의식 — SESSION.md 핵심 섹션을 출력한다.
출력은 모델이 읽거나 따랐다는 증거가 아니다. 없으면 템플릿에서 만든다.

사용: python3 tools/session_open.py [SESSION.md 경로]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

TEMPLATE = """# SESSION — 세션 이어가기 기록

## 목표
(첫 세션 마감 때 채운다)

## 현재 상태
(아직 기록 없음)

## 다음 단계
1. (아직 기록 없음)

## 결정 기록

## 파일 흔적
"""


def extract_section(text: str, name: str) -> str:
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    m = re.search(rf"^## {re.escape(name)}\n(.*?)(?=\n## |\Z)", text, flags=re.S | re.M)
    return m.group(1).strip() if m else "(섹션 없음)"


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "SESSION.md")
    if not path.is_file():
        path.write_text(TEMPLATE, encoding="utf-8")
        print(f"[생성] {path} — 템플릿으로 새로 만들었습니다. 첫 세션 마감 때 채우세요.")
        return 0
    text = path.read_text(encoding="utf-8")
    print(f"=== {path} 재정박 요약 ===")
    print("\n[목표]\n" + extract_section(text, "목표"))
    print("\n[현재 상태]\n" + extract_section(text, "현재 상태"))
    next_steps = extract_section(text, "다음 단계")
    first_line = next((ln for ln in next_steps.splitlines() if ln.strip()), "(없음)")
    print("\n[다음 단계 — 첫 항목]\n" + first_line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
