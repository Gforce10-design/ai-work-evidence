#!/usr/bin/env python3
"""최소 해법 — 실패하면 무조건 연산량을 늘린다. 구멍이 있다."""

LADDER = ("low", "medium", "high")


def naive_escalate(effort: str) -> str:
    i = LADDER.index(effort)
    return LADDER[i + 1] if i + 1 < len(LADDER) else "raise_model_tier"


if __name__ == "__main__":
    print(naive_escalate("low"))     # -> medium
    print(naive_escalate("medium"))  # -> high
    print(naive_escalate("high"))    # -> raise_model_tier
