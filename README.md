# 『AI가 일했다는 증거』 — 책에 실린 코드 전문

Claude Code에 일을 시키고 "다 됐다"는 말을 어떻게 확인하는지 다룬 전자책의 코드다.
원래 팔던 책인데 전부 무료로 풀었다. 본문은 Threads [@subal_i](https://www.threads.com/@subal_i) 에 하루 한 편씩 올라간다.
여기엔 Threads 한 편(500자)에 안 들어가는 코드를 원문 그대로 둔다.

## 1장 — 지시가 몇 턴 만에 흐려지는 문제

| 파일 | 내용 |
|---|---|
| `ch01/reinject_directives_minimal.py` | 최소 버전. 매 턴 지시 파일을 다시 주입하는 `UserPromptSubmit` 훅 |
| `ch01/reinject_directives.py` | 최종형. 원본 4KB 상한과 경고, main 안에서 잡힌 실행 중 예외는 exit 0 |
| `ch01/agent-directives.example.md` | 지시 파일 예시 (`~/.claude/agent-directives.md`) |
| `ch01/settings.example.json` | `settings.json` 훅 배선 |

훅은 `~/.claude/hooks/reinject_directives.py` 에 두고, `settings.json` 에 배선한다.
Threads 에는 복사해도 깨지지 않게 들여쓰기 없는 짧은 형태로 올렸다. 동작은 같다(출력 바이트·종료코드 대조).

## 2장 — CLAUDE.md를 유지보수 가능하게 설계하기

| 파일 | 내용 |
|---|---|
| `ch02/CLAUDE.md.example` | 규칙 대신 정본 위치·버전·해시만 적는 부트스트랩 |
| `ch02/tools/check_canonical.py` | 정본 포인터 드리프트 검사기. 해시가 다르면 종료코드 1 |
| `ch02/tools/claude_md_installer.py` | 조각 설치기. 마커 기반, 같은 코너 조각은 동시 설치 거부, 배타 검사는 쓰기 전에 |
| `ch02/tools/fragments/*/` | 조각 예시 (`meta.json` 라벨·코너·설명 + `fragment.md` 본문) |

> 2026-09-28 기술 검증판과 코드를 맞췄다. `multi-agent`·`session-handoff`의 본문 예시도 포함한다. 핀 검사는 정본을 자동으로 로딩하거나 버전 문자열을 비교하지 않는다. 설치기는 전체 입력을 먼저 검사하고 임시 파일 교체로 저장한다. 동시 설치기 실행은 지원하지 않는다.

### 직접 확인하는 법

`ch02/` 에서 돌린다. 배타 위반과 중복 마커에는 빨간불이 떠야 한다. 정상 재설치는 성공해야 하며 블록은 하나로 남아야 한다.

```
python3 tools/claude_md_installer.py --target proj --pick solo-mode --yes
python3 tools/claude_md_installer.py --target proj --pick multi-agent --yes      # 거부돼야 한다 (같은 코너)
python3 tools/claude_md_installer.py --target proj --pick session-handoff --yes  # 조각을 고쳐 다시 설치해도
grep -c "store:session-handoff:start" proj/CLAUDE.md                            # 1 이어야 한다
python3 tools/claude_md_installer.py --target proj --flavor codex --pick multi-agent --yes  # AGENTS.md 쪽도 거부
python3 tools/claude_md_installer.py --target proj --doctor                      # 블록을 손으로 복사해 넣으면 FAIL
```

이 저장소에 올리기 전에 위 네 가지를 실제로 돌려 책에 적힌 출력과 같은지 확인했다.

## 3장 — 세션이 끊겨도 이어지게

| 파일 | 내용 |
|---|---|
| `ch03/SESSION.minimal.example.md` | 최소 버전. 칸 다섯 개(목표·현재 상태·다음 단계·결정 기록·파일 흔적)만 둔 인계 파일 |
| `ch03/SESSION.md.example` | 최종형 템플릿. 섹션마다 갱신 규칙(고정·덮어쓰기·누적)을 주석으로 박아 둔다 |
| `ch03/SESSION.filled.example.md` | 채운 예시 한 벌(결제 모듈 재시도 로직) |
| `ch03/tools/session_open.py` | 세션 시작 때 돌린다. 파일이 없으면 템플릿으로 만들고, 있으면 목표·현재 상태·다음 단계 첫 항목을 띄운다 |
| `ch03/tools/session_stale_check.py` | 방치 감지기. `SESSION.md` 갱신 뒤 커밋이 임계(기본 5개) 이상 쌓이면 `[WARN]`, 종료코드 1 |

`SESSION.md` 는 이 책에서 정한 인계 방식이며 Claude Code 가 자동 관리하는 예약 파일명이 아니다. 출력은 모델이 읽었다는 증거가 아니다.

### 직접 확인하는 법

임시 git 저장소에서 `ch03/` 의 파일을 복사해 돌린다.

```
cp SESSION.filled.example.md SESSION.md && python3 tools/session_open.py   # 목표·현재 상태·다음 단계 첫 항목이 떠야 한다
git add SESSION.md && git commit -q -m "session update"
for i in 1 2 3 4 5; do echo "x" >> notes.txt; git add notes.txt; git commit -q -m "unrelated $i"; done
python3 tools/session_stale_check.py   # [WARN] … 커밋 5개, 종료코드 1
```

이 저장소에 올리기 전에 위 순서를 실제로 돌려 책에 적힌 출력과 같은지 확인했다.

## 4장 — 직접 할까 위임할까

| 파일 | 내용 |
|---|---|
| `ch04/naive_gate.py` | 최소 해법. 물량 하나만 보고 정한다 — 명세가 모호하거나 실패 비용이 높아도 `DELEGATE` 가 나오는 구멍이 있다 |
| `ch04/route_advisor.py` | 최종형 판정기(표준 라이브러리만). 결과는 `DIRECT` · `PLAN_FIRST` · `DELEGATE` · `NEEDS_PREFERENCE` 네 가지 |

판정 함수는 입력을 검토하는 예제다. 모델을 바꾸거나 워커를 실행하지 않는다. 위임 워커의 모델·effort 가 고정된 저자의 운영 구성을 예로 들며, Claude Code 전체의 제약이 아니다.

### 직접 확인하는 법

`ch04/` 에서 돌린다.

```
python3 naive_gate.py   # DELEGATE 두 번 — 둘 다 틀린 답
python3 route_advisor.py --axes "verifiable=yes,failcost=low,volume=high,depth=shallow" --axes-ext "spec_readiness=executable,decomposability=independent,context_dependency=low,verifier_available=yes"   # NEEDS_PREFERENCE
python3 route_advisor.py --axes "verifiable=yes,failcost=high,volume=high,depth=shallow" --axes-ext "spec_readiness=executable,decomposability=independent,context_dependency=low,verifier_available=yes"   # DELEGATE
```

`is_mechanical_batch` 의 조건을 `depth`·`verifiable` 둘만 남기면 두 번째 명령도 `NEEDS_PREFERENCE` 로 바뀐다 — 실패 비용이 높다는 신호가 사라진다.
이 저장소에 올리기 전에 책의 실행 예시 네 개와 깨뜨린 예시를 실제로 돌려 출력이 같은 것을 확인했다(깨뜨린 예시는 `ask:` 줄까지 세 줄).

## 앞으로

3장부터도 Threads 에 올라가는 순서대로 여기에 코드를 더한다.

## 라이선스

MIT. 가져다 쓰고 고쳐도 된다. 출처만 남겨 달라.
