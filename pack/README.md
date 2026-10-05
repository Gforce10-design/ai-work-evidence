# 템플릿 팩 — 『AI가 일했다는 증거: Claude Code 멀티에이전트 실전 운영』

이 팩은 책에서 설명한 장치들을 복사해서 바로 쓸 수 있는 파일로 묶은 것이다.

- 훅 세 개, 8장 도구 두 개, 인쇄용 체크리스트 두 개는 책 본문에서 그대로 뽑는다.
  공개하기 전에 본문과 글자 그대로 같은지 검사한다.
- 조각 설치기, CLAUDE.md 조각, 템플릿은 책 내용을 팩에 맞게 따로 쓴 파일이다.
  책과 어긋나는 곳이 보이면 책 본문이 맞다.

책 전문은 <https://gforce10-design.github.io/ai-work-evidence/> 에서 읽을 수 있다.

## 빠른 설치

```bash
cd pack   # 이 README가 있는 디렉터리
./install.sh --target /path/to/your/project
```

이 한 줄이 하는 일:

1. `hooks/*.py`를 `~/.claude/hooks/`에 복사한다.
2. `claude-md/fragments/`의 조각 다섯 개(전부)를 대상 프로젝트의
   `CLAUDE.md`에 설치한다.

기존 파일을 덮어쓰기 전에는 항상 타임스탬프가 붙은 `.bak.<시각>` 백업을
남긴다. 설치 도중 어떤 단계든 실패하면 그때까지의 변경을 자동으로 되돌린다
— 절반만 설치된 상태로 남지 않는다.

먼저 무엇이 바뀔지만 보고 싶다면:

```bash
./install.sh --target /path/to/your/project --dry-run
```

재실행해도 안전하다. 이미 동일한 내용으로 설치된 훅은 건너뛰고, 조각은
마커(`<!-- store:이름:start -->` ~ `<!-- store:이름:end -->`)를 찾아
치환하므로 중복되지 않는다.

특정 조각만 고르려면:

```bash
./install.sh --target . --fragments agent-loop,verification
```

### settings.json 배선

`install.sh`는 훅 **파일**을 `~/.claude/hooks/`에 두기만 한다. Claude Code가
그 훅을 실제로 호출하게 하려면 `~/.claude/settings.json`(또는 프로젝트의
`.claude/settings.json`)에 훅을 등록해야 한다 — 배선 예시는 1장과 6장 본문에
있다. 이건 프로젝트마다 훅 조합이 달라질 수 있어 자동화하지 않았다.

팩의 훅은 책 본문과 파일 이름이 다르다. 배선 예시를 옮길 때 이름을 바꿔 적는다.

| 책 본문의 이름 | 팩의 이름 |
|---|---|
| `reinject_directives.py` (1장) | `inject_directives.py` |
| `block_consequential.py` (6장) | `preflight_deny.py` |

내용은 같으므로 `preflight_deny.py`가 막을 때 내는 문구에는 `block_consequential.py`라는
이름이 그대로 나온다.

### CLAUDE.md 조각을 직접 다루고 싶다면

`install.sh`를 거치지 않고 조각 설치기만 따로 써도 된다.

```bash
python3 claude-md/install_fragments.py --list
python3 claude-md/install_fragments.py --target . --pick agent-loop,verification --yes
python3 claude-md/install_fragments.py --target . --remove agent-loop --yes
python3 claude-md/install_fragments.py --target . --doctor
```

`--doctor`는 아무것도 고치지 않는다 — 마커 짝이 깨졌는지, 블록이 중복됐는지,
같은 코너의 조각이 동시에 설치됐는지만 읽기 전용으로 진단한다.

각 조각 `.md` 파일은 그 자체로 완성된 블록이다 — 설치기를 안 쓰고 그냥
`CLAUDE.md`에 복사해 붙여넣어도 그대로 동작한다. 다만 그렇게 손으로 붙인
블록은 이후 설치기가 자동으로 추적·치환하지 못한다는 점은 감안해야 한다.

## 파일이 어느 장에 대응하는가

| 팩 파일 | 대응 장 | 무엇을 하는가 |
|---|---|---|
| `hooks/inject_directives.py` | 1장 — 지시가 몇 턴 만에 흐려지는 문제 | `UserPromptSubmit` 훅. 짧은 지시 파일을 매 턴 다시 컨텍스트 앞쪽에 주입한다. 크기 상한(4096바이트)을 넘으면 잘라내고 경고를 붙인다. |
| `hooks/preflight_deny.py` | 6장 — 위험한 명령을 안전하게 위임하기 | `PreToolUse` 훅. `git push --force`, `main`으로의 푸시, 원격 ref로의 `reset --hard`, 홈/루트 대상 `rm -rf`만 좁게 차단한다. 유효한 1회성 승인 마커가 있으면 그 명령 하나만 통과시킨다. 정규식은 단순한 명령 표기만 잡는 보조 검사이고, 파싱·로직 오류는 전부 허용(fail-open)으로 떨어진다 — 위험한 작업의 유일한 승인 게이트로 쓰지 않는다. |
| `hooks/approve_once.py` | 6장 | 위 훅이 요구하는 1회성 승인 마커 발행 스크립트. 명령 문자열의 SHA256 + TTL 300초 + 0600 권한으로 마커를 만든다. 사람이나 분리된 신뢰 주체가 실행한다 — 에이전트에게 실행시키지 않는다. 이 예제는 누가 승인했는지 인증하지 않는다. |
| `tools/check_invariants.py` | 8장 — 가드가 진짜 작동하는지 증명하기 | 리뷰어 역할 서브에이전트 정의에 `Write`/`Edit`/`Bash`/`NotebookEdit`이 없는지 확인하는 불변식 자가점검의 최소 예시. |
| `tools/mutation_drill.py` | 8장 | 위 자가점검을 일부러 깨뜨려 빨간불이 되는지 확인하는 뮤테이션 드릴. 베이스라인 확인 → 변이 심기 → 판정 → 원상복구 → 재확인까지 자동화한 자기완결형 예시. |
| `claude-md/fragments/agent-loop.md` | 머리말·1장 | 목표·완료조건·이터레이션 캡·합격처리 규율. |
| `claude-md/fragments/session-handoff.md` | 3장 — 세션이 끊겨도 이어지게 | SESSION.md 프로토콜 요약(섹션별 갱신 규칙, 마감 시 자체 점검). |
| `claude-md/fragments/verification.md` | 0장·5장 | 증거의 사다리 7단계 + "산출자가 자기 결과를 채점하지 않는다" 원칙. |
| `claude-md/fragments/routing.md` | 4장·5장 | 직접/위임 판정 축과 실패 7분류 진단의 요약. |
| `claude-md/fragments/approval-gate.md` | 6장 | 위험 명령 하드셋 기준과 1회성 승인 규율의 요약. |
| `claude-md/install_fragments.py` | 2장 — CLAUDE.md를 오래 고쳐 쓸 수 있게 짜기 | 2장 설치기를 팩의 조각에 맞춰 따로 쓴 판. 조각 설치·재설치(치환)·제거·doctor. 같은 코너(corner)의 조각은 동시 설치를 거부하고, 배타 검사는 파일을 고치기 전에 끝낸다. |
| `templates/SESSION.md` | 3장 | 세션 인계 파일의 최종형 템플릿. 5개 섹션과 섹션별 갱신 규칙이 주석으로 박혀 있다. |
| `templates/mission-approval.md` | 6장(팩 전용 양식 — 책 본문에는 없다) | 미션 디스패치 전 오너 전속 결정 4축(범위/쓰기경계/외부효과/재검증강도)을 확정하는 인터뷰 양식. |
| `templates/worker-brief.md` | 7장 — 위임 증거 만들기 | 워커 브리프 골격. `source-access-proof` nonce를 응답 첫 줄에 요구해, 워커가 실제로 소스를 열어봤는지 증명하게 한다. |
| `checklists/routing-decision.md` | 4장 | 직접/위임 판정 체크리스트 — 인쇄용. 책 본문 그대로. |
| `checklists/failure-diagnosis.md` | 5장 | 실패 7분류 진단표 — 인쇄용. 책 본문 그대로. |

## 라이선스

MIT. 가져다 쓰고 고쳐도 되고 다시 나눠도 된다. 출처만 남겨 달라.
저장소 루트의 `LICENSE`를 따른다.

## 직접 확인하는 법

이 팩을 신뢰하기 전에, 책의 원칙("일부러 깨뜨려서 빨간불이 되는지 확인하라")을
팩 자체에도 적용해보라.

1. `python3 claude-md/install_fragments.py --target /tmp/some-empty-dir --pick agent-loop --yes`로
   설치한 뒤 같은 명령을 한 번 더 돌린다. `grep -c "store:agent-loop:start"
   CLAUDE.md`가 여전히 1을 반환하는지 확인한다(중복 설치되지 않아야 한다).
2. 설치된 `CLAUDE.md`에서 마커 하나를 손으로 지워 짝을 깨뜨린다. `--doctor`가
   `FAIL`을 내는지 확인한다.
3. 훅은 임시 홈 폴더에서 시험한다. 실제 `~/.claude`에는 마커를 만들지 않는다.
   위험 명령은 JSON 안의 글자로만 넘긴다 — 훅은 그 문자열을 분류할 뿐 실행하지 않는다.

   ```bash
   T=$(mktemp -d); mkdir -p "$T/.claude"
   J='{"tool_name":"Bash","tool_input":{"command":"git push --force origin demo"}}'
   echo "$J" | HOME="$T" python3 hooks/preflight_deny.py; echo $?       # 2 — 차단
   HOME="$T" python3 hooks/approve_once.py "git push --force origin demo"
   echo "$J" | HOME="$T" python3 hooks/preflight_deny.py; echo $?       # 0 — 마커로 한 번 통과
   echo "$J" | HOME="$T" python3 hooks/preflight_deny.py; echo $?       # 2 — 같은 마커는 다시 못 쓴다
   echo "not json" | HOME="$T" python3 hooks/preflight_deny.py; echo $? # 0 — fail-open 이 열리는 경우
   ```

세 가지가 적힌 대로 나와야 이 팩이 책에서 설명한 대로 작동하는 것이다. 마지막 줄의 0은
통과가 아니라 이 훅이 막지 못하는 경우를 본 것이다.
