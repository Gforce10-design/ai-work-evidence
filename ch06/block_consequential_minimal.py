#!/usr/bin/env python3
"""PreToolUse 훅 — Bash 호출 중 좁은 하드셋만 정규식으로 차단한다.

기준: (1) 되돌릴 수 없는가 (2) 내 작업 범위를 벗어나 남에게 영향을 주는가.
둘 다 아니면 이 훅에 넣지 않는다 — 넓게 막으면 결국 훅 자체가 꺼진다.

안전장치: 파싱/로직 에러는 전부 허용(exit 0)으로 떨어진다. 이 훅의 버그가
작업 전체를 마비시켜서는 안 된다.
"""
import json
import re
import sys


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
            sys.stderr.write("BLOCKED: " + "; ".join(blocks) + ".\n")
            sys.exit(2)
    except Exception:
        _allow()
    _allow()


main()
