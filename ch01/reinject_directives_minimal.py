#!/usr/bin/env python3
"""UserPromptSubmit 훅 — 매 턴마다 짧은 지시 파일을 다시 주입한다."""
import os
import sys

PATH = os.path.expanduser("~/.claude/agent-directives.md")


def main():
    if not os.path.exists(PATH):
        sys.exit(0)
    with open(PATH, encoding="utf-8") as handle:
        text = handle.read().strip()
    if not text:
        sys.exit(0)
    print("<active-directives>")
    print(text)
    print("</active-directives>")
    sys.exit(0)


main()
