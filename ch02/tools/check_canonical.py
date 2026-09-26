#!/usr/bin/env python3
"""정본 포인터 드리프트 검사기.

CLAUDE.md 안의 "CANONICAL_PATH=... CANONICAL_VERSION=... CANONICAL_SHA256=..."
세 줄을 읽어, 실제 정본 파일의 현재 해시와 대조한다. 다르면 종료코드 1.

사용: python3 tools/check_canonical.py CLAUDE.md
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path


def read_pins(bootstrap_text: str) -> dict[str, str]:
    pins = {}
    for key in ("CANONICAL_PATH", "CANONICAL_VERSION", "CANONICAL_SHA256"):
        m = re.search(rf"{key}=(\S+)", bootstrap_text)
        if not m:
            sys.exit(f"[error] {key} 핀을 찾지 못했습니다")
        pins[key] = m.group(1)
    return pins


def main() -> int:
    bootstrap = Path(sys.argv[1] if len(sys.argv) > 1 else "CLAUDE.md")
    pins = read_pins(bootstrap.read_text(encoding="utf-8"))
    canonical = Path(pins["CANONICAL_PATH"]).expanduser()
    if not canonical.is_file():
        print(f"[FAIL] 정본 파일이 없습니다: {canonical}")
        return 1
    actual = hashlib.sha256(canonical.read_bytes()).hexdigest()
    if actual != pins["CANONICAL_SHA256"]:
        print(f"[FAIL] 해시 불일치 — 정본이 v{pins['CANONICAL_VERSION']} 이후로 바뀌었습니다")
        print(f"  핀    : {pins['CANONICAL_SHA256']}")
        print(f"  실제  : {actual}")
        print("  → 정본을 읽고 CLAUDE.md의 CANONICAL_VERSION·CANONICAL_SHA256을 갱신하세요")
        return 1
    print(f"[OK] 정본 v{pins['CANONICAL_VERSION']} 일치 ({canonical})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
