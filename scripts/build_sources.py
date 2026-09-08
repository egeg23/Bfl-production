#!/usr/bin/env python3
"""Rebuild docs/SOURCES.md from the "Источники" sections of docs/research/*.md.

Usage: python3 scripts/build_sources.py
Report titles are taken from the first H1 line of each report.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESEARCH = ROOT / "docs" / "research"
OUT = ROOT / "docs" / "SOURCES.md"

HEADER = [
    "# Источники",
    "",
    "Сводный список источников по всем исследовательским отчётам (`docs/research/`). "
    "Каждый факт и цифра в `docs/PLAN.md` опирается на один из этих отчётов; там же — "
    "даты публикаций и пометки «оценка»/«не найдено».",
    "",
    "Файл генерируется скриптом `scripts/build_sources.py` — не редактировать вручную.",
    "",
    "## Отчёты исследования",
    "",
]


def title_of(text: str, fallback: str) -> str:
    m = re.search(r"^#\s+(.+)$", text, flags=re.M)
    return m.group(1).strip() if m else fallback


def sources_section(text: str) -> str | None:
    m = re.search(r"\n(#+\s*(?:\d+\.\s*)?Источники[^\n]*)\n", text)
    return text[m.end():].strip() if m else None


def main() -> None:
    reports = sorted(p for p in RESEARCH.glob("*.md") if p.name != "README.md")
    out = list(HEADER)
    items = []
    for p in reports:
        text = p.read_text(encoding="utf-8")
        items.append((p, title_of(text, p.stem), sources_section(text)))
    for p, title, _ in items:
        out.append(f"- [`{p.name}`](research/{p.name}) — {title}")
    out.append("")
    for p, title, body in items:
        out += [f"## {title}", f"(из `research/{p.name}`)", ""]
        out += [body if body else "(раздел «Источники» не найден)", ""]
    OUT.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"{OUT.relative_to(ROOT)}: {len(items)} reports, {len(OUT.read_text(encoding='utf-8').split())} words")


if __name__ == "__main__":
    main()
