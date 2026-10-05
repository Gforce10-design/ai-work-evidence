#!/usr/bin/env python3
"""PreToolUse 훅 — Bash 호출 중 좁은 하드셋만 정규식으로 차단한다.
유효한 1회성 승인 마커가 있으면 정확히 그 명령 하나만 통과시킨다.

기준: (1) 되돌릴 수 없는가 (2) 내 작업 범위를 벗어나 남에게 영향을 주는가.
둘 다 아니면 이 훅에 넣지 않는다.

FAIL-OPEN: 파싱/로직 에러는 전부 허용(exit 0)으로 떨어진다. 이 훅의 버그가
작업 전체를 마비시켜서는 안 된다.
"""
import hashlib
import json
import os
import re
import stat
import sys
import time
import tempfile

MARKER = os.path.expanduser("~/.claude/.consequential_allow.json")
TTL_SECONDS = 300


def _consume_marker(command: str) -> bool:
    """마커를 읽자마자 지운다 — 검증에 실패해도 다시 못 쓰게 만들기 위해서다."""
    raw = b""
    claimed = None
    fd = None
    try:
        # 같은 파일을 두 프로세스가 읽지 않도록 먼저 원자적으로 가져온다.
        fd, claimed = tempfile.mkstemp(prefix=".consumed-", dir=os.path.dirname(MARKER))
        os.close(fd)
        fd = None
        os.replace(MARKER, claimed)
        fd = os.open(claimed, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        info = os.fstat(fd)
        if (stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                and stat.S_IMODE(info.st_mode) == 0o600 and info.st_nlink == 1):
            with os.fdopen(fd, "rb") as handle:
                fd = None
                raw = handle.read(8193)
        if len(raw) > 8192:
            raw = b""
    except OSError:
        raw = b""
    finally:
        if fd is not None:
            os.close(fd)
        if claimed is not None:
            try:
                os.unlink(claimed)
            except OSError:
                raw = b""  # 삭제 실패를 승인 성공으로 바꾸지 않는다

    try:
        if not raw:
            return False
        marker = json.loads(raw)
        required = {"schema_version", "command_sha256", "issued_at_epoch", "expires_at_epoch"}
        if set(marker) != required or marker["schema_version"] != "1":
            return False
        if marker["command_sha256"] != hashlib.sha256(command.encode("utf-8")).hexdigest():
            return False
        issued = marker["issued_at_epoch"]
        expires = marker["expires_at_epoch"]
        now = int(time.time())
        if type(issued) is not int or type(expires) is not int:
            return False
        if not (0 <= issued <= now < expires and 0 < expires - issued <= TTL_SECONDS):
            return False
        return True
    except Exception:
        return False


def _allow():
    sys.exit(0)


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        _allow()

    try:
        if data.get("tool_name") != "Bash":
            _allow()
        cmd = (data.get("tool_input") or {}).get("command", "")
        if not isinstance(cmd, str) or not cmd.strip():
            _allow()

        if _consume_marker(cmd):
            _allow()

        blocks = []

        if re.search(r"\bgit\s+push\b", cmd):
            if re.search(r"\b(master|main)\b", cmd):
                blocks.append("master/main으로의 git push")
            if re.search(r"--force(-with-lease)?\b|\s-f\b", cmd):
                blocks.append("git force-push")

        if re.search(r"\bgit\s+reset\s+--hard\b", cmd) and re.search(r"\b(origin|upstream)/", cmd):
            blocks.append("원격 ref로의 git reset --hard")

        if re.search(r"\brm\s+-\S*r\S*f|\brm\s+-\S*f\S*r|\brm\s+-rf|\brm\s+-fr", cmd):
            if re.search(r"(^|\s)(/|~|\$HOME)(\s|$|\"|')", cmd):
                blocks.append("홈/루트 대상 rm -rf")

        if blocks:
            sys.stderr.write(
                "BLOCKED by block_consequential.py: " + "; ".join(blocks) + ". "
                "정말 필요하면 오너가 검토한 뒤 신뢰된 발급 경로로 1회성 승인 "
                "마커를 발급하고 다시 실행해라.\n"
            )
            sys.exit(2)
    except Exception:
        _allow()
    _allow()


main()
