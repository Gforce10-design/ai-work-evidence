#!/usr/bin/env python3
"""1회성 승인 마커 발행 스크립트.

사용: python3 approve_once.py "<실행할 정확한 명령 전체 문자열>"

이 문자열과 SHA256이 정확히 일치하는 명령 하나만, 발급 시각으로부터 TTL초
안에 통과시키는 마커를 만든다. 훅이 그 마커를 소비하는 순간 파일이 지워진다 —
재사용 불가.
"""
import hashlib
import json
import os
import sys
import time
import tempfile

MARKER = os.path.expanduser("~/.claude/.consequential_allow.json")
TTL_SECONDS = 300


def main():
    if len(sys.argv) != 2:
        sys.exit('사용법: approve_once.py "<정확한 명령 문자열>"')
    command = sys.argv[1]
    now = int(time.time())
    marker = {
        "schema_version": "1",
        "command_sha256": hashlib.sha256(command.encode("utf-8")).hexdigest(),
        "issued_at_epoch": now,
        "expires_at_epoch": now + TTL_SECONDS,
    }
    # 발급 경로는 에이전트와 분리된 신뢰 영역에서만 호출한다.
    directory = os.path.dirname(MARKER)
    os.makedirs(directory, mode=0o700, exist_ok=True)
    fd, staged = tempfile.mkstemp(prefix=".approval-", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(marker, handle)
        os.chmod(staged, 0o600)
        os.replace(staged, MARKER)
    finally:
        if os.path.lexists(staged):
            os.unlink(staged)
    print(f"승인 마커 발급: {MARKER} (TTL {TTL_SECONDS}초)")
    print("지금 정확히 이 문자열로 실행해야 한다 — 한 글자라도 다르면 거부된다.")


main()
