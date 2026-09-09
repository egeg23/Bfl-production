#!/usr/bin/env python3
"""Build the interview cheat sheet (PDF + Markdown) from structured content.

Inputs:  docs/cheatsheet/blocks.json  — speaking script per block
         docs/cheatsheet/qa.json      — anticipated questions and answers (optional)
Outputs: docs/CHEATSHEET.pdf, docs/CHEATSHEET.md

Usage: python3 scripts/build_cheatsheet.py
"""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "cheatsheet"
PDF = ROOT / "docs" / "CHEATSHEET.pdf"
MD = ROOT / "docs" / "CHEATSHEET.md"

CSS = """
@page {
  size: A4; margin: 12mm 12mm 14mm 12mm;
  @bottom-center { content: counter(page) " / " counter(pages);
    font-family: "DejaVu Sans"; font-size: 7.5pt; color: #8a8f98; }
}
* { box-sizing: border-box; }
body { font-family: "DejaVu Sans", sans-serif; font-size: 9pt; line-height: 1.36;
       color: #16181d; margin: 0; }
h1 { font-size: 18pt; margin: 0 0 2mm; letter-spacing: -0.3pt; }
h2.part { font-size: 13pt; margin: 0 0 3mm; padding-bottom: 1.5mm;
  border-bottom: 2pt solid #16181d; letter-spacing: -0.2pt; }
.lede { color: #4a5058; font-size: 8.6pt; margin: 0 0 4mm; }
.cover-box { border: 1pt solid #16181d; padding: 3mm; margin: 0 0 4mm; }
.cover-box h3 { margin: 0 0 1.5mm; font-size: 10pt; }
.map td { font-size: 8.4pt; }
.block { margin: 0 0 4mm; }
.block-head { display: flex; align-items: baseline; gap: 2.5mm;
  border-bottom: 1.2pt solid #16181d; padding-bottom: 1.2mm; margin-bottom: 2mm; }
.num { font-size: 12pt; font-weight: bold; min-width: 7mm; }
.btitle { font-size: 11pt; font-weight: bold; flex: 1; letter-spacing: -0.2pt; }
.time { font-size: 7.6pt; color: #4a5058; white-space: nowrap; }
.flag { background: #f2f2f0; border-left: 2pt solid #16181d; padding: 1.4mm 2mm;
  font-size: 8.2pt; margin: 0 0 2mm; }
.say { margin: 0 0 1.8mm; }
.say p { margin: 0 0 1.2mm; padding-left: 4mm; text-indent: -4mm; break-inside: avoid; }
.say p::before { content: "▸ "; color: #6b7280; }
.chips { margin: 0 0 2mm; font-size: 8pt; }
.chip { display: inline-block; border: 0.6pt solid #b9bec6; border-radius: 2pt;
  padding: 0.4mm 1.4mm; margin: 0 1.4mm 1mm 0; }
.qa-h { font-size: 7.6pt; text-transform: uppercase; letter-spacing: 0.5pt;
  color: #6b7280; margin: 0 0 1.5mm; }
.q { break-inside: avoid; margin: 0 0 2.2mm; }
.q .qq { font-weight: bold; font-size: 9pt; margin: 0 0 0.6mm; }
.q .qa-txt { margin: 0 0 0.6mm; font-size: 8.8pt; }
.q .meta { font-size: 7.8pt; color: #4a5058; }
.q .meta b { color: #16181d; }
.two-col { column-count: 2; column-gap: 6mm; }
ul.tight { margin: 0 0 3mm; padding-left: 4.5mm; }
ul.tight li { margin: 0 0 1mm; break-inside: avoid; }
.pagebreak { break-before: page; }
table { width: 100%; border-collapse: collapse; font-size: 8.4pt; margin: 0 0 3mm; }
th, td { border: 0.6pt solid #b9bec6; padding: 1.1mm 1.6mm; text-align: left; vertical-align: top; }
th { background: #f2f2f0; font-size: 8pt; }
"""


def esc(s):
    return html.escape(str(s))


def head(b):
    return ('<div class="block-head">'
            f'<span class="num">{esc(b["n"])}</span>'
            f'<span class="btitle">{esc(b["title"])}</span>'
            f'<span class="time">{esc(b.get("time", ""))}</span></div>')


def render_script(b):
    out = ['<section class="block">', head(b)]
    if b.get("flag"):
        out.append(f'<div class="flag">{esc(b["flag"])}</div>')
    out.append('<div class="say">')
    for line in b["script"]:
        out.append(f"<p>{esc(line)}</p>")
    out.append("</div>")
    if b.get("numbers"):
        out.append('<div class="chips">'
                   + "".join(f'<span class="chip">{esc(n)}</span>' for n in b["numbers"])
                   + "</div>")
    out.append("</section>")
    return "\n".join(out)


def render_qa(b, qa_items):
    if not qa_items:
        return ""
    out = ['<section class="block">', head(b),
           '<div class="qa-h">Спросят — отвечаю</div>']
    for q in qa_items:
        out.append('<div class="q">')
        out.append(f'<div class="qq">В: {esc(q["question"])}</div>')
        out.append(f'<div class="qa-txt">О: {esc(q["answer"])}</div>')
        bits = []
        if q.get("numbers"):
            bits.append("<b>Цифры:</b> " + esc("; ".join(q["numbers"])))
        if q.get("trap"):
            bits.append("<b>Не говорить:</b> " + esc(q["trap"]))
        if bits:
            out.append('<div class="meta">' + " &nbsp;·&nbsp; ".join(bits) + "</div>")
        out.append("</div>")
    out.append("</section>")
    return "\n".join(out)


def build():
    blocks = json.loads((SRC / "blocks.json").read_text(encoding="utf-8"))["blocks"]
    qa_path = SRC / "qa.json"
    qa = json.loads(qa_path.read_text(encoding="utf-8")) if qa_path.exists() else {}
    by_block = {}
    for item in qa.get("items", []):
        by_block.setdefault(str(item.get("block_n", "")), []).append(item)

    parts = [
        "<h1>Собеседование: контрактное юридическое производство БФЛ</h1>",
        '<p class="lede">Часть I — что говорю, по блокам. Каждая строка со стрелкой — одна '
        'произнесённая мысль. Часть II — вопросы, которые последуют, и готовые ответы; её не '
        'читают вслух, в неё заглядывают. Все цифры — оценки из плана версии 1.1, '
        "проверяются в первые 30 дней.</p>",
    ]
    if qa.get("opening"):
        parts.append('<div class="cover-box"><h3>Держать в голове весь разговор</h3>'
                     + "<ul class='tight'>"
                     + "".join(f"<li>{esc(x)}</li>" for x in qa["opening"])
                     + "</ul></div>")
    rows = "".join(
        f'<tr><td>{esc(b["n"])}</td><td>{esc(b["title"])}</td><td>{esc(b.get("time",""))}</td>'
        f'<td>{len(by_block.get(b["n"], []))}</td></tr>' for b in blocks)
    parts.append('<table class="map"><tr><th>№</th><th>Блок</th><th>Время</th>'
                 f'<th>Вопросов</th></tr>{rows}</table>')

    parts.append('<section class="pagebreak"><h2 class="part">Часть I. Что говорю</h2></section>')
    for b in blocks:
        parts.append(render_script(b))

    parts.append('<section class="pagebreak"><h2 class="part">Часть II. Спросят — отвечаю</h2></section>')
    for b in blocks:
        parts.append(render_qa(b, by_block.get(b["n"], [])))
    stress = by_block.get("stress", [])
    if stress:
        parts.append(render_qa({"n": "S", "title": "Стресс-вопросы", "time": ""}, stress))

    if qa.get("must_know_numbers"):
        parts.append('<section class="pagebreak"><h2 class="part">Цифры наизусть</h2>'
                     '<ul class="tight two-col">'
                     + "".join(f"<li>{esc(x)}</li>" for x in qa["must_know_numbers"])
                     + "</ul></section>")
    if qa.get("killer_questions"):
        parts.append('<section><h2 class="part">Опасные вопросы</h2>'
                     '<ul class="tight">'
                     + "".join(f"<li>{esc(x)}</li>" for x in qa["killer_questions"])
                     + "</ul></section>")
    if qa.get("never_say"):
        parts.append('<section><h2 class="part">Не говорить никогда</h2>'
                     '<ul class="tight">'
                     + "".join(f"<li>{esc(x)}</li>" for x in qa["never_say"])
                     + "</ul></section>")

    doc = ("<!doctype html><html lang='ru'><head><meta charset='utf-8'>"
           f"<title>Шпаргалка БФЛ</title><style>{CSS}</style></head><body>"
           + "\n".join(parts) + "</body></html>")
    (SRC / "cheatsheet.html").write_text(doc, encoding="utf-8")

    from weasyprint import HTML
    HTML(string=doc).write_pdf(PDF)

    md = ["# Шпаргалка для собеседования — контрактное юридическое производство БФЛ", ""]
    for b in blocks:
        md += [f"## {b['n']}. {b['title']} ({b.get('time','')})", ""]
        if b.get("flag"):
            md += [f"> {b['flag']}", ""]
        md += [f"- {line}" for line in b["script"]] + [""]
        if b.get("numbers"):
            md += ["Цифры: " + " · ".join(b["numbers"]), ""]
        for q in by_block.get(b["n"], []):
            md += [f"**В: {q['question']}**", "", f"О: {q['answer']}", ""]
            if q.get("trap"):
                md += [f"_Не говорить: {q['trap']}_", ""]
    for key, title in (("must_know_numbers", "Цифры наизусть"),
                       ("killer_questions", "Опасные вопросы"),
                       ("never_say", "Не говорить никогда")):
        if qa.get(key):
            md += [f"## {title}", ""] + [f"- {x}" for x in qa[key]] + [""]
    MD.write_text("\n".join(md), encoding="utf-8")

    print(f"{PDF.relative_to(ROOT)} ({PDF.stat().st_size // 1024} KB), "
          f"{MD.relative_to(ROOT)}; блоков {len(blocks)}, вопросов {sum(len(v) for v in by_block.values())}")


if __name__ == "__main__":
    build()
