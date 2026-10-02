#!/usr/bin/env python3
"""최소 해법 — 물량 하나만 보고 정한다. 구멍이 있다."""


def naive_gate(axes: dict) -> str:
    if axes.get("volume") == "high":
        return "DELEGATE"
    return "DIRECT"


if __name__ == "__main__":
    print(naive_gate({"volume": "high", "spec_readiness": "vague"}))
    print(naive_gate({"volume": "high", "failcost": "high"}))
