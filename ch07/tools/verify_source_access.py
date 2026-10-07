#!/usr/bin/env python3
"""워커 응답이 스냅샷을 실제로 열었다는 증거(1회성 nonce)를 담고 있는지 검사한다."""
from __future__ import annotations

import sys
import re
from pathlib import Path


def expected_nonce(snapshot_root: Path) -> str:
    proof_file = snapshot_root / "sources" / "source-access-proof.txt"
    return proof_file.read_text(encoding="utf-8").strip()


def verify(response_text: str, snapshot_root: Path, required_line_index: int = 0) -> bool:
    if type(required_line_index) is not int or required_line_index < 0:
        return False
    try:
        nonce = expected_nonce(snapshot_root)
    except OSError:
        return False
    if not re.fullmatch(r"[0-9a-f]{32}", nonce):
        return False
    lines = [ln for ln in response_text.splitlines() if ln.strip() != ""]
    if len(lines) <= required_line_index:
        return False
    expected_line = f"SOURCE_ACCESS_PROOF:{nonce}"
    actual_line = lines[required_line_index].strip()
    # "포함"이 아니라 그 줄 전체가 정확히 일치해야 한다.
    return actual_line == expected_line


if __name__ == "__main__":
    root = Path(sys.argv[1])
    response = Path(sys.argv[2]).read_text(encoding="utf-8")
    ok = verify(response, root)
    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)
