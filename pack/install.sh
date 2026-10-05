#!/usr/bin/env bash
# install.sh — 템플릿 팩 설치기.
#
# 훅을 ~/.claude/hooks/에 복사하고, claude-md 조각을 대상 CLAUDE.md에 설치한다.
# 실패하면 지금까지 한 변경을 되돌리고 부분 설치 상태로 남기지 않는다.
#
# 사용:
#   ./install.sh [--target DIR] [--fragments a,b,c] [--dry-run]
#
#   --target      CLAUDE.md를 설치할 프로젝트 루트 (기본: 현재 디렉터리)
#   --fragments   설치할 조각 이름, 쉼표 구분 (기본: 다섯 개 전부)
#   --dry-run     아무것도 바꾸지 않고 계획만 보여준다
#
# 재실행해도 안전하다 — 이미 동일한 내용으로 설치된 훅은 건너뛰고, 조각은
# 마커를 찾아 치환(재설치)하므로 중복되지 않는다.

set -Eeuo pipefail
shopt -s nullglob

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="$(pwd)"
FRAGMENTS="agent-loop,session-handoff,verification,routing,approval-gate"
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      TARGET="$2"; shift 2 ;;
    --fragments)
      FRAGMENTS="$2"; shift 2 ;;
    --dry-run)
      DRY_RUN=1; shift ;;
    -h|--help)
      grep -E '^# ' "$0" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *)
      echo "[install.sh] 알 수 없는 인자: $1" >&2
      exit 2 ;;
  esac
done

HOOKS_SRC="$SCRIPT_DIR/hooks"
HOOKS_DST="$HOME/.claude/hooks"
INSTALLER="$SCRIPT_DIR/claude-md/install_fragments.py"

if [[ ! -d "$HOOKS_SRC" ]]; then
  echo "[install.sh] 훅 소스 디렉터리가 없습니다: $HOOKS_SRC" >&2
  exit 1
fi
if [[ ! -f "$INSTALLER" ]]; then
  echo "[install.sh] 조각 설치기를 찾을 수 없습니다: $INSTALLER" >&2
  exit 1
fi
command -v python3 >/dev/null 2>&1 || { echo "[install.sh] python3가 필요합니다." >&2; exit 1; }

say() { echo "[install.sh] $*"; }

# ---------- 롤백 장부 ----------
# 이번 실행에서 새로 만든 파일과, 덮어쓰기 전에 남긴 백업 경로 쌍을 기록해둔다.
# 도중에 어떤 단계든 실패하면 아래 on_error가 이 장부를 거꾸로 읽어 원상복구
# 한다 — 부분 설치 상태로 남기지 않기 위해서다.
CREATED_FILES=()
BACKUP_PAIRS=()   # "원본경로|백업경로" 쌍

on_error() {
  local status=$?
  echo "" >&2
  echo "[install.sh] 오류(종료코드 $status)가 발생했습니다 — 지금까지의 변경을 되돌립니다..." >&2

  if [[ ${#CREATED_FILES[@]} -gt 0 ]]; then
    for ((i = ${#CREATED_FILES[@]} - 1; i >= 0; i--)); do
      f="${CREATED_FILES[$i]}"
      if [[ -e "$f" ]]; then
        rm -f "$f"
        echo "  되돌림: 새로 만든 파일 삭제 — $f" >&2
      fi
    done
  fi

  if [[ ${#BACKUP_PAIRS[@]} -gt 0 ]]; then
    for ((i = ${#BACKUP_PAIRS[@]} - 1; i >= 0; i--)); do
      pair="${BACKUP_PAIRS[$i]}"
      orig="${pair%%|*}"
      bak="${pair##*|}"
      if [[ -f "$bak" ]]; then
        cp "$bak" "$orig"
        rm -f "$bak"
        echo "  되돌림: 백업에서 복원 — $orig" >&2
      fi
    done
  fi

  echo "[install.sh] 되돌리기 완료 — 부분 설치 상태로 남지 않았습니다." >&2
  exit 1
}
trap on_error ERR

# ---------- 1. 훅 설치 ----------
if [[ $DRY_RUN -eq 1 ]]; then
  say "(dry-run) 훅 대상 디렉터리: $HOOKS_DST"
else
  mkdir -p "$HOOKS_DST"
fi

for src in "$HOOKS_SRC"/*.py; do
  name="$(basename "$src")"
  dst="$HOOKS_DST/$name"

  if [[ -f "$dst" ]] && cmp -s "$src" "$dst"; then
    say "훅 $name — 이미 동일한 내용으로 설치돼 있음, 건너뜀"
    continue
  fi

  if [[ $DRY_RUN -eq 1 ]]; then
    if [[ -f "$dst" ]]; then
      say "(dry-run) 훅 $name — 기존 파일과 다름, 백업 후 덮어쓸 예정 -> $dst"
    else
      say "(dry-run) 훅 $name — 새로 설치할 예정 -> $dst"
    fi
    continue
  fi

  was_new=1
  if [[ -f "$dst" ]]; then
    was_new=0
    bak="${dst}.bak.$(date +%Y%m%d%H%M%S)"
    cp "$dst" "$bak"
    BACKUP_PAIRS+=("$dst|$bak")
    say "훅 $name — 기존 파일을 $(basename "$bak") 로 백업"
  fi

  cp "$src" "$dst"
  chmod +x "$dst"
  if [[ $was_new -eq 1 ]]; then
    CREATED_FILES+=("$dst")
  fi
  say "훅 $name 설치 완료 -> $dst"
done

# ---------- 2. CLAUDE.md 백업 ----------
CLAUDE_MD="$TARGET/CLAUDE.md"
if [[ $DRY_RUN -eq 0 ]]; then
  if [[ -f "$CLAUDE_MD" ]]; then
    bak="${CLAUDE_MD}.bak.$(date +%Y%m%d%H%M%S)"
    cp "$CLAUDE_MD" "$bak"
    BACKUP_PAIRS+=("$CLAUDE_MD|$bak")
    say "CLAUDE.md 기존 파일을 $(basename "$bak") 로 백업"
  else
    CREATED_FILES+=("$CLAUDE_MD")
  fi
fi

# ---------- 3. 조각 설치 ----------
INSTALL_ARGS=(--target "$TARGET" --pick "$FRAGMENTS" --yes)
[[ $DRY_RUN -eq 1 ]] && INSTALL_ARGS+=(--dry-run)

say "조각 설치: $FRAGMENTS -> $CLAUDE_MD"
python3 "$INSTALLER" "${INSTALL_ARGS[@]}"

trap - ERR

if [[ $DRY_RUN -eq 1 ]]; then
  say "dry-run 완료 — 실제로는 아무것도 바뀌지 않았습니다."
else
  say "설치 완료."
  say "확인: python3 \"$INSTALLER\" --target \"$TARGET\" --doctor"
fi
