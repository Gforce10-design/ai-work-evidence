# 『AI가 일했다는 증거』 — 책에 실린 코드 전문

Claude Code에 일을 시키고 "다 됐다"는 말을 어떻게 확인하는지 다룬 전자책의 코드다.
원래 팔던 책인데 전부 무료로 풀었다. 본문은 Threads [@subal_i](https://www.threads.com/@subal_i) 에 하루 한 편씩 올라간다.
여기엔 Threads 한 편(500자)에 안 들어가는 코드를 원문 그대로 둔다.

## 1장 — 지시가 몇 턴 만에 흐려지는 문제

| 파일 | 내용 |
|---|---|
| `ch01/reinject_directives_minimal.py` | 최소 버전. 매 턴 지시 파일을 다시 주입하는 `UserPromptSubmit` 훅 |
| `ch01/reinject_directives.py` | 최종형. 4KB 상한과 경고, 어떤 예외에도 exit 0 |
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

> `multi-agent`·`session-handoff` 의 `fragment.md` 는 책에 본문이 없다. 아래 확인 절차를 돌릴 수 있게 `meta.json` 의 설명을 그대로 옮긴 최소 본문을 넣어 뒀다. 자기 규칙으로 바꿔 쓰면 된다.

### 직접 확인하는 법

`ch02/` 에서 돌린다. 네 가지가 전부 빨간불을 내야 설치기가 제대로 동작하는 거다.

```
python3 tools/claude_md_installer.py --target proj --pick solo-mode --yes
python3 tools/claude_md_installer.py --target proj --pick multi-agent --yes      # 거부돼야 한다 (같은 코너)
python3 tools/claude_md_installer.py --target proj --pick session-handoff --yes  # 조각을 고쳐 다시 설치해도
grep -c "store:session-handoff:start" proj/CLAUDE.md                            # 1 이어야 한다
python3 tools/claude_md_installer.py --target proj --flavor codex --pick multi-agent --yes  # AGENTS.md 쪽도 거부
python3 tools/claude_md_installer.py --target proj --doctor                      # 블록을 손으로 복사해 넣으면 FAIL
```

이 저장소에 올리기 전에 위 네 가지를 실제로 돌려 책에 적힌 출력과 같은지 확인했다.

## 앞으로

3장부터도 Threads 에 올라가는 순서대로 여기에 코드를 더한다.

## 라이선스

MIT. 가져다 쓰고 고쳐도 된다. 출처만 남겨 달라.
