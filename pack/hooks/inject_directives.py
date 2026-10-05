#!/usr/bin/env python3
"""UserPromptSubmit 훅 — ~/.claude/agent-directives.md를 매 턴 다시 주입한다.

목적: 사용자 프롬프트마다 짧은 지시를 다시 출력한다. CLAUDE.md의 재로딩과
별개인 보조 장치이며, 규칙 준수 효과는 실제 행동을 비교해 확인한다.

예산: 최대 CAP 바이트만 원문에서 내보낸다. 태그·경고 문구는 별도다. 넘으면 잘라내고 그 사실을 표시한다 — 규칙
파일이 계속 길어지면 이 훅 자체가 새로운 희석 문제를 만들기 때문이다.

안전장치: main 안에서 잡힌 실행 중 예외는 삼키고 exit 0으로 끝낸다.
문법 오류·인터프리터 실행 실패·강제 종료까지 이 코드가 처리하지는 않는다.
"""
import os
import sys

CAP = 4096
PATH = os.path.expanduser("~/.claude/agent-directives.md")


def main():
    try:
        if not os.path.exists(PATH):
            sys.exit(0)
        with open(PATH, encoding="utf-8", errors="ignore") as handle:
            text = handle.read().strip()
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
