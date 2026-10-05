#!/usr/bin/env python3
"""실패 분류 + Wilson 하한 + append-only 레지스트리. 표준 라이브러리만 쓴다."""
from __future__ import annotations
import json
import math
import sys
from pathlib import Path

NORMAL_EFFORT_LADDER = ("low", "medium", "high")


def wilson_lower_bound(successes: int, n: int, z: float = 1.96) -> float:
    """일반 성공/시도 개수의 Wilson 양측 95% 신뢰구간 하한."""
    if type(n) is not int or type(successes) is not int or not 0 <= successes <= n:
        raise ValueError("0 <= successes <= n인 정수 개수가 필요하다")
    if isinstance(z, bool) or not isinstance(z, (int, float)) or not math.isfinite(z) or z <= 0:
        raise ValueError("z는 유한한 양수여야 한다")
    if n == 0:
        return 0.0  # 증거 없음 표시; 계산된 신뢰구간이 아니다
    phat = successes / n
    denom = 1 + z**2 / n
    center = phat + z**2 / (2 * n)
    margin = z * math.sqrt((phat * (1 - phat) + z**2 / (4 * n)) / n)
    return (center - margin) / denom


def evidence_tier(n: int) -> str:
    if n <= 2:
        return "anecdotal"
    if n <= 9:
        return "provisional"
    return "override_eligible"


def next_effort(effort: str) -> str | None:
    if effort not in NORMAL_EFFORT_LADDER:
        return None
    i = NORMAL_EFFORT_LADDER.index(effort)
    return NORMAL_EFFORT_LADDER[i + 1] if i + 1 < len(NORMAL_EFFORT_LADDER) else None


def diagnose(failure_class: str, model: str | None = None, effort: str | None = None) -> dict:
    """리트라이마다 축을 딱 하나만 바꾼다."""
    if failure_class in {"REASONING_DEPTH_FAILURE", "OVERPROVISIONING"} and effort not in NORMAL_EFFORT_LADDER:
        return {"change_axis": "none", "rationale": "지원되는 effort 값을 먼저 확인한다."}
    if failure_class == "REASONING_DEPTH_FAILURE":
        if next_effort(effort) is None:
            return {"change_axis": "none", "rationale": "effort 상한이다. 명세·도구·역량 진단을 다시 한다."}
        return {"change_axis": "effort", "from": effort, "to": next_effort(effort),
                "rationale": "숙고가 부족했다. 같은 모델에서 effort를 한 단계만 올린다."}
    if failure_class == "MODEL_CAPABILITY_FAILURE":
        return {"change_axis": "model", "from": model,
                "rationale": "명세·도구 문제를 배제하고 역량 부족으로 진단했다면 모델 변경을 시험한다."}
    if failure_class == "SPEC_FAILURE":
        return {"change_axis": "spec",
                "rationale": "테스트를 문자 그대로만 통과시켰다. 연산량이 아니라 명세·완료조건을 고친다."}
    if failure_class == "IMPLEMENTATION_BUG":
        return {"change_axis": "none",
                "rationale": "경계가 뚜렷한 버그다. 같은 모델·같은 effort로 한 번만 수선한다."}
    if failure_class == "TOOL_OR_INFRA_FAILURE":
        return {"change_axis": "none",
                "rationale": "인증·쿼터·네트워크·권한 문제다. 아무것도 바꾸지 않는다 — 환경을 고친다. "
                             "절대 모델 품질 실패로 기록하지 않는다."}
    if failure_class == "OVERPROVISIONING":
        if effort == NORMAL_EFFORT_LADDER[0]:
            return {"change_axis": "none", "rationale": "이 예제의 effort 하한이다. 다른 비용 원인을 확인한다."}
        return {"change_axis": "effort",
                "from": effort,
                "to": NORMAL_EFFORT_LADDER[max(0, NORMAL_EFFORT_LADDER.index(effort) - 1)],
                "rationale": "품질은 충분한데 느리고 비싸다. 한 단계 낮추고 멈출 조건을 명시한다."}
    if failure_class == "ROLE_OR_VENDOR_MISMATCH":
        return {"change_axis": "worker",
                "rationale": "특화가 안 맞는다. 다른 워커를 제안한다 — 벤더는 자동으로 바꾸지 않는다."}
    return {"change_axis": "none", "rationale": f"미분류 실패 종류: {failure_class}"}


# ---------- append-only 레지스트리 ----------

def record_attempt(path: Path, **fields) -> None:
    fields.setdefault("event_type", "attempt_final")
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(fields, ensure_ascii=False) + "\n")


def invalidate_attempt(path: Path, target_attempt_id: str, reason_code: str,
                        evidence: str, event_id: str) -> None:
    event = {
        "event_type": "attempt_invalidation",
        "event_id": event_id,
        "target_attempt_id": target_attempt_id,
        "reason_code": reason_code,
        "verification_evidence": evidence,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def load_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def usable_attempts(records: list[dict], cohort: dict | None = None) -> list[dict]:
    """V2/V3 + 독립 검증자 + 무효화되지 않은 것만, attempt_id로 중복 제거."""
    if any(not isinstance(r, dict) for r in records):
        raise ValueError("레지스트리의 각 줄은 JSON 객체여야 한다")
    invalidated = set()
    for r in records:
        if r.get("event_type") == "attempt_invalidation":
            target = r.get("target_attempt_id")
            if not isinstance(target, str) or not target.strip():
                raise ValueError("무효화 이벤트의 대상 식별자가 비었다")
            invalidated.add(target)
    by_id: dict[str, list[dict]] = {}
    for r in records:
        aid = r.get("attempt_id")
        if r.get("event_type", "attempt_final") == "attempt_final" and isinstance(aid, str) and aid.strip():
            by_id.setdefault(aid, []).append(r)
    conflicts = {aid for aid, rows in by_id.items() if any(row != rows[0] for row in rows)}
    seen: set[str] = set()
    out: list[dict] = []
    for r in records:
        if r.get("event_type", "attempt_final") != "attempt_final":
            continue
        if r.get("verification_grade") not in ("V2", "V3"):
            continue
        verifier = str(r.get("verifier_role") or "").strip().lower()
        worker = str(r.get("worker") or "").strip().lower()
        if not verifier or verifier in {"self", "producer", "worker"} or verifier == worker:
            continue
        aid = r.get("attempt_id")
        if any(not isinstance(r.get(k), str) or not r[k].strip() for k in ("attempt_id", "task", "worker", "verifier_role")):
            continue
        if r.get("outcome") not in ("success", "fail", "partial", "aborted") or aid in conflicts:
            continue
        if aid in invalidated or aid in seen:
            continue
        if cohort and any(r.get(k) != v for k, v in cohort.items()):
            continue
        seen.add(aid)
        out.append(r)
    return out


def override_allowed(usable: list[dict], failcost: str = "low") -> dict:
    if failcost not in {"low", "mid", "high"}:
        raise ValueError("알 수 없는 failcost")
    usable = usable_attempts(usable)
    n = len(usable)
    unique_tasks = len({r.get("task") for r in usable})
    success = sum(1 for r in usable if r.get("outcome") == "success")
    fail = sum(1 for r in usable if r.get("outcome") == "fail")
    partial = sum(1 for r in usable if r.get("outcome") == "partial")
    all_success = n > 0 and success == n and fail == 0 and partial == 0
    need = 20 if failcost == "high" else 10
    allowed = n >= need and unique_tasks >= 3 and all_success
    return {
        "allowed": allowed, "n": n, "tier": evidence_tier(n),
        "unique_task_instances": unique_tasks, "success": success, "fail": fail, "partial": partial,
        "wilson_lower_bound": round(wilson_lower_bound(success, n), 3) if n else 0.0,
    }


if __name__ == "__main__":
    reg = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("registry_demo.jsonl")
    print("Wilson 95% 하한 —")
    for x, n in ((1, 1), (3, 3), (10, 10), (20, 20)):
        print(f"  {x}/{n} 전부 성공 -> {wilson_lower_bound(x, n) * 100:.1f}%  ({evidence_tier(n)})")

    record_attempt(reg, attempt_id="a1", task="배치 업로드 파서 수정", worker="worker-b",
                    verification_grade="V3", verifier_role="pytest",
                    outcome="success", task_family="implementation")
    record_attempt(reg, attempt_id="a2", task="배치 업로드 파서 수정", worker="worker-b",
                    verification_grade="V0", verifier_role="self",
                    outcome="success", task_family="implementation")
    print("\nusable (V0 자기보고는 빠져야 한다):", len(usable_attempts(load_records(reg))))
