#!/usr/bin/env python3
"""CLAUDE.md 조각 설치기 — 결정적·마커 기반·코너 배타.

사용법:
    python3 tools/claude_md_installer.py --list
    python3 tools/claude_md_installer.py --target . --pick solo-mode,session-handoff --yes
    python3 tools/claude_md_installer.py --target . --doctor
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
FRAGMENTS_DIR = SCRIPT_DIR / "fragments"
# 도구마다 지침 파일 이름은 다르지만 조각·코너 카탈로그는 하나를 공유한다.
FLAVOR_FILES = {"claude": "CLAUDE.md", "codex": "AGENTS.md"}


def marker(name: str) -> tuple[str, str]:
    return f"<!-- store:{name}:start -->", f"<!-- store:{name}:end -->"


def load_catalog() -> dict[str, dict]:
    catalog: dict[str, dict] = {}
    for meta_path in sorted(FRAGMENTS_DIR.glob("*/meta.json")):
        catalog[meta_path.parent.name] = json.loads(meta_path.read_text(encoding="utf-8"))
    return catalog


def validate_markers(text: str) -> None:
    """중첩·역순·중복·짝 누락을 쓰기 전에 거부한다."""
    opened = None
    seen = set()
    for name, kind in re.findall(r"<!-- store:([a-z0-9-]+):(start|end) -->", text):
        if kind == "start":
            if opened is not None or name in seen:
                raise ValueError(f"중첩 또는 중복 마커: {name}")
            opened = name
            seen.add(name)
        elif opened != name:
            raise ValueError(f"짝 또는 순서가 잘못된 마커: {name}")
        else:
            opened = None
    if opened is not None:
        raise ValueError(f"끝 마커 없음: {opened}")


def installed_names(instr: Path) -> set[str]:
    if not instr.is_file():
        return set()
    text = instr.read_text(encoding="utf-8")
    return set(re.findall(r"<!-- store:([a-z0-9-]+):start -->", text))


def installed_names_all(target: Path) -> set[str]:
    """폴더는 도구가 몇 개든 하나의 작업 공간이다 — CLAUDE.md와 AGENTS.md에 설치된
    조각을 합집합으로 봐야, 한쪽엔 '단독 실행'을 다른 쪽엔 '멀티에이전트'를 심어
    같은 폴더가 서로 다른 도구에서 모순된 지시를 받는 사고를 막는다."""
    names: set[str] = set()
    for fname in FLAVOR_FILES.values():
        names |= installed_names(target / fname)
    return names


def check_exclusions(picks: list[str], installed: set[str], catalog: dict) -> list[str]:
    """같은 코너(corner)는 상호배타. pick끼리 + pick과 기설치 조각을 모두 본다."""
    problems: list[str] = []
    for i, a in enumerate(picks):
        for b in picks[i + 1:]:
            if catalog[a]["corner"] == catalog[b]["corner"]:
                problems.append(
                    f"{a} ↔ {b}: 같은 코너({catalog[a]['corner']}) — 동시 설치 불가")
    for p in picks:
        for existing in installed:
            if existing != p and existing in catalog and catalog[existing]["corner"] == catalog[p]["corner"]:
                problems.append(
                    f"{p}: 이미 설치된 {existing}와 같은 코너({catalog[p]['corner']}) — 설치 불가")
    return problems


def install_fragment(instr: Path, name: str, dry: bool) -> str:
    frag_dir = FRAGMENTS_DIR / name
    body = (frag_dir / "fragment.md").read_text(encoding="utf-8").strip("\n")
    start, end = marker(name)
    block = f"{start}\n{body}\n{end}"
    text = instr.read_text(encoding="utf-8") if instr.is_file() else ""
    validate_markers(text)
    if start in text and end in text:
        pattern = re.escape(start) + r".*?" + re.escape(end)
        new = re.sub(pattern, lambda m: block, text, count=1, flags=re.S)
        action = "교체"
    else:
        new = (text.rstrip("\n") + "\n\n" if text else "") + block + "\n"
        action = "설치"
    if not dry:
        instr.write_text(new, encoding="utf-8")
    return f"{name} {action} → {instr.name}"


def doctor(instr: Path, catalog: dict) -> int:
    """읽기 전용 진단. 아무것도 고치지 않는다. FAIL이 있으면 1을 반환."""
    fails = 0
    if not instr.is_file():
        print(f"  [INFO] {instr.name} 없음 — 설치된 조각 없음")
        return 0
    text = instr.read_text(encoding="utf-8")
    try:
        validate_markers(text)
    except ValueError as exc:
        print(f"  [FAIL] {exc}")
        return 1
    tokens = re.findall(r"<!-- store:([a-z0-9-]+):(start|end) -->", text)
    starts = [n for n, k in tokens if k == "start"]
    ends = [n for n, k in tokens if k == "end"]
    clean: set[str] = set()
    for n in sorted(set(starts) | set(ends)):
        s, e = starts.count(n), ends.count(n)
        if s != e:
            print(f"  [FAIL] '{n}' 마커 짝 깨짐 (start {s} / end {e})")
            fails += 1
        elif s > 1:
            print(f"  [FAIL] '{n}' 블록 중복 {s}개")
            fails += 1
        else:
            clean.add(n)
    for n in sorted(clean):
        start, end = marker(n)
        m = re.search(re.escape(start) + r"\n(.*?)\n" + re.escape(end), text, flags=re.S)
        src = FRAGMENTS_DIR / n / "fragment.md"
        if n not in catalog:
            print(f"  [WARN] 카탈로그에 없는 조각 마커 '{n}'")
        elif not m or not src.is_file():
            print(f"  [FAIL] '{n}' 본문 또는 카탈로그 파일 없음")
            fails += 1
        elif m.group(1) != src.read_text(encoding="utf-8").strip("\n"):
            print(f"  [WARN] '{n}' 블록이 카탈로그 최신본과 다름 — 재설치 권장")
        else:
            print(f"  [OK] '{n}' 정상")
    by_corner: dict[str, list[str]] = {}
    for n in sorted(clean & catalog.keys()):
        by_corner.setdefault(catalog[n]["corner"], []).append(n)
    for corner, names in by_corner.items():
        if len(names) > 1:
            print(f"  [FAIL] 같은 코너({corner}) 조각 공존 — {', '.join(names)}")
            fails += 1
    print(f"\n  진단 결과: {'FAIL ' + str(fails) + '건' if fails else '이상 없음'}")
    return 1 if fails else 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--target")
    ap.add_argument("--pick")
    ap.add_argument("--flavor", choices=sorted(FLAVOR_FILES), default="claude",
                    help="claude=CLAUDE.md(기본) | codex=AGENTS.md")
    ap.add_argument("--doctor", action="store_true")
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    catalog = load_catalog()
    if not catalog:
        sys.exit(f"[error] fragments가 없습니다: {FRAGMENTS_DIR}")

    if args.list or not (args.target and args.pick) and not args.doctor:
        for name, m in catalog.items():
            print(f"  {name} — 코너: {m['corner']} — {m['desc']}")
        return

    if not args.target:
        ap.error("--doctor/설치에는 --target이 필요합니다")
    target = Path(args.target).expanduser().resolve()
    instr = target / FLAVOR_FILES[args.flavor]

    if args.doctor:
        sys.exit(doctor(instr, catalog))

    picks = list(dict.fromkeys(p.strip() for p in args.pick.split(",") if p.strip()))
    if not picks:
        ap.error("--pick이 비어 있습니다")
    unknown = [p for p in picks if p not in catalog]
    if unknown:
        sys.exit(f"[error] 없는 품목: {', '.join(unknown)}")

    installed = installed_names_all(target)  # CLAUDE.md + AGENTS.md 합집합
    problems = check_exclusions(picks, installed, catalog)
    if problems:
        print("[배타 위반] 설치를 거부합니다 — 대상 파일은 변경되지 않았습니다:")
        for msg in problems:
            print(f"  · {msg}")
        sys.exit(2)

    if not args.yes and not args.dry_run:
        if input(f"{target} 에 {', '.join(picks)} 설치할까요? [y/N]: ").strip().lower() not in ("y", "yes"):
            sys.exit("취소됨")

    # 입력·마커·조각 파일을 모두 확인한 뒤 메모리에서 한 번에 조립한다.
    original = instr.read_text(encoding="utf-8") if instr.exists() else ""
    try:
        for fname in FLAVOR_FILES.values():
            path = target / fname
            if path.exists():
                validate_markers(path.read_text(encoding="utf-8"))
        bodies = {p: (FRAGMENTS_DIR / p / "fragment.md").read_text(encoding="utf-8").strip("\n") for p in picks}
    except (ValueError, OSError) as exc:
        sys.exit(f"[error] 쓰기 전 검사 실패: {exc}")
    result = original
    messages = []
    for p in picks:
        start, end = marker(p)
        block = f"{start}\n{bodies[p]}\n{end}"
        if start in result:
            result = re.sub(re.escape(start) + r".*?" + re.escape(end), lambda m: block, result, count=1, flags=re.S)
            action = "교체"
        else:
            result = (result.rstrip("\n") + "\n\n" if result else "") + block + "\n"
            action = "설치"
        messages.append(f"{p} {action} → {instr.name}")
    if not args.dry_run:
        import os
        import tempfile
        target.mkdir(parents=True, exist_ok=True)
        fd, staged = tempfile.mkstemp(prefix=".instructions-", dir=target)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(result)
            if instr.exists():
                os.chmod(staged, instr.stat().st_mode & 0o777)
            os.replace(staged, instr)
        finally:
            Path(staged).unlink(missing_ok=True)
    for message in messages:
        print(("(dry) " if args.dry_run else "") + message)



if __name__ == "__main__":
    main()
