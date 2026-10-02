#!/usr/bin/env python3
"""직접/위임 판정기 — 표준 라이브러리만 쓴다. 아무 폴더에나 둬도 된다."""
from __future__ import annotations
import argparse

OPT_GOALS = ("cost", "latency", "context_preservation")


def parse_kv(s: str) -> dict:
    out = {}
    for pair in s.split(","):
        pair = pair.strip()
        if not pair:
            continue
        k, _, v = pair.partition("=")
        out[k.strip()] = v.strip()
    return out


def is_mechanical_batch(axes: dict, ext: dict) -> bool:
    """shallow + verifiable 단둘로는 부족하다 — 전 조건을 다 걸어야 한다."""
    return (
        axes.get("depth") == "shallow"
        and axes.get("verifiable") == "yes"
        and axes.get("volume") == "high"
        and axes.get("failcost") != "high"
        and ext.get("spec_readiness") == "executable"
        and ext.get("decomposability") == "independent"
        and ext.get("context_dependency") == "low"
    )


def gate(axes: dict, ext: dict) -> dict:
    choices = {"verifiable": {"yes", "partial", "no"}, "failcost": {"low", "mid", "high"},
               "volume": {"low", "high"}, "depth": {"shallow", "mid", "deep"}}
    extra = {"handoff_cost": {"low", "high"}, "spec_readiness": {"executable", "vague"},
             "decomposability": {"independent", "single"}, "context_dependency": {"low", "high"},
             "verifier_available": {"yes", "no"}, "optimization_goal": set(OPT_GOALS)}
    if (set(axes) != set(choices) or set(ext) - set(extra)
            or any(not isinstance(v, str) or v not in choices[k] for k, v in axes.items())
            or any(not isinstance(v, str) or v not in extra[k] for k, v in ext.items())):
        return {"route": "PLAN_FIRST", "reason": "필수 축 누락·알 수 없는 값이 있다. 입력부터 확인한다."}
    if ext.get("spec_readiness") != "executable":
        return {
            "route": "PLAN_FIRST",
            "reason": "명세가 실행 가능한 상태(범위·완료조건·검증자)가 아니다. 먼저 정한다.",
        }

    if axes.get("volume") == "low" and (
        ext.get("handoff_cost") == "high" or ext.get("context_dependency") == "high"
    ):
        return {
            "route": "DIRECT",
            "reason": "위임 고정비(새 컨텍스트 구축 + 명세 작성)가 산출물 규모보다 크다.",
        }

    if ext.get("verifier_available") != "yes":
        return {"route": "PLAN_FIRST", "reason": "독립 검증자를 정한 뒤 위임을 판단한다."}

    if is_mechanical_batch(axes, ext):
        goal = ext.get("optimization_goal")
        if goal not in OPT_GOALS:
            return {
                "route": "NEEDS_PREFERENCE",
                "reason": (
                    "기계적 배치이지만 위임 워커에 경제형 로드아웃이 없다. "
                    "비용/시간/컨텍스트 보존 중 무엇이 우선인지 답해야 판정이 성립한다."
                ),
                "ask": "비용 / 완료시간 / 메인 컨텍스트 보존 중 무엇이 우선입니까?",
            }
        if goal == "cost":
            return {
                "route": "DIRECT",
                "reason": "비용 우선 — 직접 실행을 측정 후보로 삼는다. 모델 전환은 별도 판단이다.",
            }
        return {
            "route": "DELEGATE",
            "reason": f"{goal} 우선 — 위임은 병렬성·컨텍스트 보존을 산다(비용 절감이 아니다).",
        }

    if (
        ext.get("spec_readiness") == "executable"
        and (axes.get("volume") == "high" or ext.get("decomposability") == "independent")
        and ext.get("verifier_available") == "yes"
    ):
        return {
            "route": "DELEGATE",
            "reason": "명세 확정 + (물량 또는 분해 가능) + 독립 검증자 존재.",
        }

    return {
        "route": "DIRECT",
        "reason": "위 조건 중 어느 것도 확정적으로 위임을 지지하지 않는다.",
        "confidence": "low",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--axes", required=True,
        help="verifiable=yes|partial|no,failcost=low|mid|high,volume=high|low,depth=shallow|mid|deep",
    )
    ap.add_argument(
        "--axes-ext", default="",
        help=(
            "handoff_cost=low|high,spec_readiness=executable|vague,"
            "decomposability=independent|single,context_dependency=low|high,"
            "verifier_available=yes|no,optimization_goal=cost|latency|context_preservation"
        ),
    )
    args = ap.parse_args()
    axes = parse_kv(args.axes)
    ext = parse_kv(args.axes_ext)
    result = gate(axes, ext)
    print(f"route: {result['route']}")
    print(f"reason: {result['reason']}")
    if "ask" in result:
        print(f"ask: {result['ask']}")


if __name__ == "__main__":
    main()
