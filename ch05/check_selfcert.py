def usable_attempts_broken(records, cohort=None):
    invalidated = {r.get("target_attempt_id") for r in records if r.get("event_type") == "attempt_invalidation"}
    seen, out = set(), []
    for r in records:
        if r.get("event_type", "attempt_final") != "attempt_final":
            continue
        if r.get("verification_grade") not in ("V2", "V3"):
            continue
        aid = r.get("attempt_id")           # 검증자 == 산출자 체크가 사라졌다
        if aid in invalidated or aid in seen:
            continue
        seen.add(aid)
        out.append(r)
    return out

from pathlib import Path
from failure_diagnosis import record_attempt, usable_attempts, load_records

reg2 = Path("registry_selfcert.jsonl")
record_attempt(reg2, attempt_id="c1", task="배치 이름변경", worker="worker-b",
               verification_grade="V3", verifier_role="worker-b", outcome="success")

print("정상판(검증자==실행자면 제외):", len(usable_attempts(load_records(reg2))))          # -> 0
print("깨진판(검증자 체크 제거 -> 자기증명이 세어짐):", len(usable_attempts_broken(load_records(reg2))))  # -> 1
