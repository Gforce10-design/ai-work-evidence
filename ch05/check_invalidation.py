from pathlib import Path
from failure_diagnosis import record_attempt, invalidate_attempt, usable_attempts, load_records

reg = Path("registry_audit.jsonl")
record_attempt(reg, attempt_id="b1", task="배치 이름변경", worker="worker-b",
               verification_grade="V3", verifier_role="pytest", outcome="success")
print("무효화 전:", len(usable_attempts(load_records(reg))))   # -> 1

invalidate_attempt(reg, target_attempt_id="b1", reason_code="verifier_was_producer",
                    evidence="검증자가 실행자 본인이었음이 뒤늦게 밝혀짐", event_id="inv-1")
print("무효화 후:", len(usable_attempts(load_records(reg))))   # -> 0
print("파일 줄 수(둘 다 남아 감사 가능):", sum(1 for _ in open(reg)))  # -> 2
