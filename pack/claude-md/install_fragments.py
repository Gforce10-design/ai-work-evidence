#!/usr/bin/env python3
"""CLAUDE.md / AGENTS.md 조각 설치기 — 결정적·마커 기반·코너 배타.

2장(CLAUDE.md를 유지보수 가능하게 설계하기)의 설치기 설계를 그대로 따른다.
조각은 `<!-- store:이름:start -->` ~ `<!-- store:이름:end -->` 마커로 경계를
표시하고, 같은 코너(corner)의 조각은 동시 설치를 거부하며, 배타 검사는 반드시
실제로 파일을 고치기 **전에** 끝낸다 — 절반만 쓰인 파일을 남기지 않기 위해서다.

이 팩의 조각 파일(`fragments/*.md`)은 이미 자기 마커를 포함한 완성된 블록이다
(그대로 CLAUDE.md에 복붙해도 되게 하기 위함). 설치기는 그 블록을 통째로 읽어
대상 파일에 넣거나 빼거나 치환한다.

사용법:
    python3 install_fragments.py --list
    python3 install_fragments.py --target . --pick agent-loop,verification --yes
    python3 install_fragments.py --target . --pick agent-loop --yes   # 재설치(치환)
    python3 install_fragments.py --target . --remove agent-loop --yes
    python3 install_fragments.py --target . --doctor
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
FRAGMENTS_DIR = SCRIPT_DIR / "fragments"
CATALOG_PATH = FRAGMENTS_DIR / "catalog.json"
# 도구마다 지침 파일 이름은 다르지만 조각·코너 카탈로그는 하나를 공유한다.
FLAVOR_FILES = {"claude": "CLAUDE.md", "codex": "AGENTS.md"}

MARKER_RE = re.compile(r"<!-- store:([a-z0-9-]+):(start|end) -->")


def marker(name: str) -> tuple[str, str]:
    return f"<!-- store:{name}:start -->", f"<!-- store:{name}:end -->"


def load_catalog() -> dict[str, dict]:
    if not CATALOG_PATH.is_file():
        sys.exit(f"[error] 카탈로그가 없습니다: {CATALOG_PATH}")
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    for name in catalog:
        frag_path = FRAGMENTS_DIR / f"{name}.md"
        if not frag_path.is_file():
            sys.exit(f"[error] 카탈로그에 있는 조각 파일이 없습니다: {frag_path}")
    return catalog


def load_fragment_block(name: str) -> str:
    """조각 파일 자체가 이미 자기 마커로 시작·끝나는 완성된 블록이어야 한다.

    형식이 어긋나면(마커 누락·오타) 조용히 잘못된 블록을 심는 대신 여기서
    바로 실패시킨다 — 조각 파일이 손상된 채로 설치되는 것을 막기 위해서다.
    """
    path = FRAGMENTS_DIR / f"{name}.md"
    text = path.read_text(encoding="utf-8").strip("\n")
    start, end = marker(name)
    if not text.startswith(start) or not text.endswith(end):
        sys.exit(
            f"[error] {path.name} 이(가) 자기 마커로 시작·끝나지 않습니다 "
            f"(요구: {start} ... {end}) — 조각 파일이 손상됐습니다."
        )
    return text


def installed_names(instr: Path) -> set[str]:
    if not instr.is_file():
        return set()
    text = instr.read_text(encoding="utf-8")
    return {n for n, k in MARKER_RE.findall(text) if k == "start"}


def installed_names_all(target: Path) -> set[str]:
    """폴더는 도구가 몇 개든 하나의 작업 공간이다 — CLAUDE.md와 AGENTS.md에
    설치된 조각을 합집합으로 봐야, 한쪽엔 서로 다른 코너의 조각을 심어 같은
    폴더가 도구마다 모순된 지시를 받는 사고를 막는다."""
    names: set[str] = set()
    for fname in FLAVOR_FILES.values():
        names |= installed_names(target / fname)
    return names


def check_exclusions(picks: list[str], installed: set[str], catalog: dict) -> list[str]:
    """같은 코너는 상호배타. pick끼리 + pick과 기설치 조각을 모두 본다."""
    problems: list[str] = []
    for i, a in enumerate(picks):
        for b in picks[i + 1:]:
            if catalog[a]["corner"] == catalog[b]["corner"]:
                problems.append(f"{a} <-> {b}: 같은 코너({catalog[a]['corner']}) — 동시 설치 불가")
    for p in picks:
        for existing in installed:
            if existing != p and existing in catalog and catalog[existing]["corner"] == catalog[p]["corner"]:
                problems.append(
                    f"{p}: 이미 설치된 {existing}와 같은 코너({catalog[p]['corner']}) — 설치 불가"
                )
    return problems


def install_fragment(instr: Path, name: str, dry: bool) -> str:
    block = load_fragment_block(name)
    start, end = marker(name)
    text = instr.read_text(encoding="utf-8") if instr.is_file() else ""
    if start in text and end in text:
        pattern = re.escape(start) + r".*?" + re.escape(end)
        # repl에 함수를 쓰면 백슬래시가 역참조로 재해석되지 않는다 — block을
        # 그대로 문자열 치환 패턴에 넘기면 그 안의 백슬래시가 깨질 수 있다.
        new = re.sub(pattern, lambda m: block, text, count=1, flags=re.S)
        action = "재설치(치환)"
    else:
        new = (text.rstrip("\n") + "\n\n" if text.strip() else "") + block + "\n"
        action = "설치"
    if not dry:
        instr.write_text(new, encoding="utf-8")
    return f"{name} {action} -> {instr.name}"


def remove_fragment(instr: Path, name: str, dry: bool) -> str:
    if not instr.is_file():
        return f"{name} 제거 건너뜀 — {instr.name} 없음"
    start, end = marker(name)
    text = instr.read_text(encoding="utf-8")
    if start not in text or end not in text:
        return f"{name} 제거 건너뜀 — {instr.name}에 설치돼 있지 않음"
    pattern = re.escape(start) + r".*?" + re.escape(end)
    new = re.sub(pattern, "", text, count=1, flags=re.S)
    # 블록이 남긴 빈 줄 뭉치를 정리한다 (내용 손실 없이 공백만 접는다).
    new = re.sub(r"\n{3,}", "\n\n", new)
    new = new.strip("\n")
    new = (new + "\n") if new else ""
    if not dry:
        instr.write_text(new, encoding="utf-8")
    return f"{name} 제거 -> {instr.name}"


def doctor(instr: Path, catalog: dict) -> int:
    """읽기 전용 진단. 아무것도 고치지 않는다. FAIL이 있으면 1을 반환."""
    fails = 0
    if not instr.is_file():
        print(f"  [INFO] {instr.name} 없음 — 설치된 조각 없음")
        return 0
    text = instr.read_text(encoding="utf-8")
    tokens = MARKER_RE.findall(text)
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
        m = re.search(re.escape(start) + r"(.*?)" + re.escape(end), text, flags=re.S)
        if n not in catalog:
            print(f"  [WARN] 카탈로그에 없는 조각 마커 '{n}'")
            continue
        expected_block = load_fragment_block(n)
        expected_inner = expected_block[len(start): len(expected_block) - len(end)]
        if m and m.group(1) != expected_inner:
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


def print_catalog(catalog: dict) -> None:
    for name, m in catalog.items():
        print(f"  {name} — 코너: {m['corner']} — {m['desc']}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="설치 가능한 조각 목록을 보여준다")
    ap.add_argument("--target", help="CLAUDE.md/AGENTS.md가 있는(또는 생길) 폴더")
    ap.add_argument("--pick", help="설치·재설치할 조각 이름들, 쉼표로 구분")
    ap.add_argument("--remove", help="제거할 조각 이름들, 쉼표로 구분")
    ap.add_argument("--flavor", choices=sorted(FLAVOR_FILES), default="claude",
                     help="claude=CLAUDE.md(기본) | codex=AGENTS.md")
    ap.add_argument("--doctor", action="store_true", help="설치 상태만 읽기 전용으로 진단한다")
    ap.add_argument("--yes", action="store_true", help="확인 프롬프트를 건너뛴다")
    ap.add_argument("--dry-run", action="store_true", help="아무것도 쓰지 않고 계획만 보여준다")
    args = ap.parse_args()

    catalog = load_catalog()

    if args.list:
        print_catalog(catalog)
        return

    if not args.target:
        if not (args.pick or args.remove or args.doctor):
            print_catalog(catalog)
            return
        sys.exit("[error] --target 이 필요합니다 (예: --target .)")

    target = Path(args.target).expanduser().resolve()
    instr = target / FLAVOR_FILES[args.flavor]

    if args.doctor:
        sys.exit(doctor(instr, catalog))

    if args.remove:
        names = [p.strip() for p in args.remove.split(",") if p.strip()]
        unknown = [p for p in names if p not in catalog]
        if unknown:
            sys.exit(f"[error] 없는 품목: {', '.join(unknown)}")
        if not args.yes and not args.dry_run:
            reply = input(f"{target} 에서 {', '.join(names)} 제거할까요? [y/N]: ")
            if reply.strip().lower() not in ("y", "yes"):
                sys.exit("취소됨")
        for n in names:
            print(("(dry) " if args.dry_run else "") + remove_fragment(instr, n, dry=args.dry_run))
        return

    if args.pick:
        picks = [p.strip() for p in args.pick.split(",") if p.strip()]
        unknown = [p for p in picks if p not in catalog]
        if unknown:
            sys.exit(f"[error] 없는 품목: {', '.join(unknown)}")

        installed = installed_names_all(target)
        problems = check_exclusions(picks, installed, catalog)
        if problems:
            print("[배타 위반] 설치를 거부합니다 — 대상 파일은 변경되지 않았습니다:")
            for msg in problems:
                print(f"  - {msg}")
            sys.exit(2)

        if not args.yes and not args.dry_run:
            reply = input(f"{target} 에 {', '.join(picks)} 설치할까요? [y/N]: ")
            if reply.strip().lower() not in ("y", "yes"):
                sys.exit("취소됨")

        target.mkdir(parents=True, exist_ok=True)
        for p in picks:
            print(("(dry) " if args.dry_run else "") + install_fragment(instr, p, dry=args.dry_run))
        return

    sys.exit("[error] --pick, --remove, --doctor 중 하나를 지정하세요 (또는 --list)")


if __name__ == "__main__":
    main()
