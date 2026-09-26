#!/usr/bin/env python3
"""UserPromptSubmit 훅 — ~/.claude/agent-directives.md를 매 턴 다시 주입한다.

목적: CLAUDE.md의 규칙은 컨텍스트 앞쪽에 고정되고, 대화가 길어지거나 컴팩션이
한 번 지나가면 상대적 비중이 줄어든다. 이 훅은 그 문제를 "규칙을 더 세게 쓰기"가
아니라 "매 턴 다시 가까이 놓기"로 해결한다.

예산: 최대 CAP 바이트만 내보낸다. 넘으면 잘라내고 그 사실을 표시한다 — 규칙
파일이 계속 길어지면 이 훅 자체가 새로운 희석 문제를 만들기 때문이다.

안전장치: 어떤 예외가 나든 아무것도 출력하지 않고 exit 0 — 프롬프트를 막는 일은
절대 없다.
"""
import os
import sys

CAP = 4096
PATH = os.path.expanduser("~/.claude/agent-directives.md")


def main():
    try:
        if not os.path.exists(PATH):
            sys.exit(0)
        text = open(PATH, encoding="utf-8", errors="ignore").read().strip()
        if not text:
            sys.exit(0)
        if len(text.encode("utf-8")) > CAP:
            text = text.encode("utf-8")[:CAP].decode("utf-8", "ignore").rstrip()
            text += (
                "\n[...truncated at "
                + str(CAP)
                + " bytes — agent-directives.md가 너무 커졌다. "
                "해소된 항목을 지우고 다시 줄여라.]"
            )
        sys.stdout.write(
            "<active-directives note=\"매 턴 재주입됨. 지금 다시 확인하고 행동하라.\">\n"
            + text
            + "\n</active-directives>\n"
        )
    except Exception:
        pass
    sys.exit(0)


main()
