#!/usr/bin/env python3
"""읽기전용 뷰를 실제로 읽었는지 묻고 답하게 하는 challenge-response 검사기."""
from __future__ import annotations

import random
import re
from pathlib import Path

MIN_LINE_LENGTH = 20
QUESTION_COUNT = 3
PASS_THRESHOLD = 2  # 3문 중 2정답 — 3정답을 요구했다가 정직한 리뷰어를 거부한 적이 있다

QUESTION_LINE_RE = re.compile(r"^(?P<idx>\d+)\. QUOTE_LINE (?P<path>.+):(?P<lineno>\d+)$")


def _iter_view_lines(view_root: Path):
    for path in sorted(view_root.rglob("*")):
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(view_root.resolve()):
            continue
        rel = path.relative_to(view_root)
        try:
            text = path.read_text(encoding="utf-8", errors="strict")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if len(stripped) >= MIN_LINE_LENGTH:
                yield rel, lineno, stripped


def _build_exclusion_corpus(*handed_dirs: Path) -> set[str]:
    """워커가 이미 받은 모든 텍스트(brief + sources) — 정답 후보에서 제외한다."""
    corpus: set[str] = set()
    for handed in handed_dirs:
        if not handed.exists():
            continue
        for path in handed.rglob("*"):
            if path.is_file():
                try:
                    text = path.read_text(encoding="utf-8", errors="strict")
                except (UnicodeDecodeError, OSError):
                    continue
                corpus.update(ln.strip() for ln in text.splitlines() if ln.strip())
    return corpus


def _render_question(rel_path: Path, lineno: int) -> str:
    return f"QUOTE_LINE {rel_path}:{lineno}"


def select_challenge(
    view_root: Path, handed_dirs: list[Path], count: int = QUESTION_COUNT, seed: int | None = None
) -> list[tuple[Path, int, str]]:
    """뷰에서만 나오고, 뷰 전체에서 유일하고, 질문 자체가 답을 드러내지 않는 줄을 count개 고른다."""
    if type(count) is not int or count < 1:
        raise ValueError("count는 양의 정수여야 한다")
    by_text: dict[str, list[tuple[Path, int]]] = {}
    for rel, lineno, text in _iter_view_lines(view_root):
        by_text.setdefault(text, []).append((rel, lineno))

    exclusion = _build_exclusion_corpus(*handed_dirs)

    candidates: list[tuple[Path, int, str]] = []
    for text, locations in by_text.items():
        if len(locations) != 1:
            continue  # 파일 안에서만 유일한 게 아니라, 뷰 전체에서 유일해야 한다
        if any(text in line for line in exclusion):
            continue  # 워커가 이미 받은 내용에도 있으면 정답이 아니다
        rel, lineno = locations[0]
        question = _render_question(rel, lineno)
        if question in text or text in question:
            continue  # 질문 문장이 후보 줄 안에 이미 있으면 자기지시적이라 버린다
        candidates.append((rel, lineno, text))

    rng = random.Random(seed)
    rng.shuffle(candidates)
    if len(candidates) < count:
        raise RuntimeError(f"뷰에서 유일하고 안전한 줄을 {count}개 찾지 못함 (가용 {len(candidates)}개)")
    return candidates[:count]


def write_challenge(
    view_root: Path, handed_dirs: list[Path], out_path: Path, seed: int | None = None
) -> None:
    picked = select_challenge(view_root, handed_dirs, seed=seed)
    lines = [
        "다음 각 질문에, 지정된 파일의 지정된 줄 내용을 정확히 그대로 답하라.",
        "형식: ANSWER_<번호>: <줄 내용 그대로>",
        "",
    ]
    for i, (rel, lineno, _text) in enumerate(picked, start=1):
        lines.append(f"{i}. {_render_question(rel, lineno)}")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def verify_challenge(
    view_root: Path, out_path: Path, response_text: str, pass_threshold: int = PASS_THRESHOLD
) -> bool:
    """답은 저장된 값과 비교하지 않는다 — 매번 고정된 읽기 전용 뷰에서 다시 계산한다."""
    if type(pass_threshold) is not int or not 1 <= pass_threshold <= QUESTION_COUNT:
        return False
    try:
        questions = []
        for line in out_path.read_text(encoding="utf-8").splitlines():
            match = QUESTION_LINE_RE.fullmatch(line.strip())
            if match:
                questions.append(match)
        if len(questions) != QUESTION_COUNT or {m["idx"] for m in questions} != {"1", "2", "3"}:
            return False
        locations = set()
        expected_values = set()
        correct = 0
        root = view_root.resolve()
        for m in questions:
            rel = Path(m["path"])
            lineno = int(m["lineno"])
            path = (root / rel).resolve()
            if rel.is_absolute() or ".." in rel.parts or not path.is_relative_to(root) or lineno < 1:
                return False
            location = (path, lineno)
            if location in locations:
                return False
            locations.add(location)
            expected = path.read_text(encoding="utf-8").splitlines()[lineno - 1].strip()
            if len(expected) < MIN_LINE_LENGTH or expected in expected_values:
                return False
            expected_values.add(expected)
            answers = [ln.strip() for ln in response_text.splitlines() if ln.strip().startswith(f"ANSWER_{m['idx']}:")]
            if len(answers) > 1:
                return False
            if answers and answers[0].split(":", 1)[1].strip() == expected:
                correct += 1
        return correct >= pass_threshold
    except (OSError, ValueError, IndexError):
        return False
