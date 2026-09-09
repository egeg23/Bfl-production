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
  size: A4; margin: 14mm 13mm 16mm 13mm;
  @bottom-center { content: counter(page) " / " counter(pages);
    font-family: "DejaVu Sans"; font-size: 8pt; color: #8a8f98; }
}
* { box-sizing: border-box; }
body { font-family: "DejaVu Sans", sans-serif; font-size: 9.6pt; line-height: 1.45;
       color: #16181d; margin: 0; }
h1 { font-size: 20pt; margin: 0 0 2mm; letter-spacing: -0.3pt; }
.lede { color: #4a5058; font-size: 9pt; margin: 0 0 5mm; }
.cover-box { border: 1.2pt solid #16181d; padding: 4mm; margin: 0 0 5mm; }
.cover-box h2 { margin: 0 0 2mm; font-size: 11pt; }
.block { break-inside: avoid-page; margin: 0 0 6mm; }
.block-head { display: flex; align-items: baseline; gap: 3mm;
  border-bottom: 1.6pt solid #16181d; padding-bottom: 1.6mm; margin-bottom: 2.6mm; }
.num { font-size: 15pt; font-weight: bold; min-width: 9mm; }
.btitle { font-size: 13pt; font-weight: bold; flex: 1; letter-spacing: -0.2pt; }
.time { font-size: 8pt; color: #4a5058; white-space: nowrap; }
.flag { background: #f2f2f0; border-left: 2.5pt solid #16181d; padding: 1.8mm 2.5mm;
  font-size: 8.6pt; margin: 0 0 2.5mm; }
.say { margin: 0 0 2.5mm; }
.say p { margin: 0 0 1.6mm; padding-left: 4.5mm; text-indent: -4.5mm; }
.say p::before { content: "▸ "; color: #6b7280; }
.chips { margin: 0 0 2.5mm; font-size: 8.4pt; color: #16181d; }
.chip { display: inline-block; border: 0.6pt solid #b9bec6; border-radius: 2pt;
  padding: 0.6mm 1.6mm; margin: 0 1.6mm 1.2mm 0; }
.qa { border-top: 0.6pt dotted #b9bec6; padding-top: 2mm; }
.qa-h { font-size: 8pt; text-transform: uppercase; letter-spacing: 0.6pt;
  color: #6b7280; margin: 0 0 1.8mm; }
.q { break-inside: avoid; margin: 0 0 2.6mm; }
.q .qq { font-weight: bold; font-size: 9.4pt; margin: 0 0 0.8mm; }
.q .qa-txt { margin: 0 0 0.8mm; }
.q .meta { font-size: 8.2pt; color: #4a5058; }
.q .meta b { color: #16181d; }
.two-col { column-count: 2; column-gap: 7mm; }
.two-col li { break-inside: avoid; }
ul.tight { margin: 0 0 3mm; padding-left: 5mm; }
ul.tight li { margin: 0 0 1.2mm; }
.pagebreak { break-before: page; }
table { width: 100%; border-collapse: collapse; font-size: 8.8pt; margin: 0 0 4mm; }
th, td { border: 0.6pt solid #b9bec6; padding: 1.4mm 2mm; text-align: left; vertical-align: top; }
th { background: #f2f2f0; font-size: 8.4pt; }
.footer-note { font-size: 8pt; color: #6b7280; margin-top: 4mm; }
"""


def esc(s):
    return html.escape(str(s))


def render_block(b, qa_items):
    out = ['<section class="block">']
    out.append('<div class="block-head">'
               f'<span class="num">{esc(b["n"])}</span>'
               f'<span class="btitle">{esc(b["title"])}</span>'
               f'<span class="time">{esc(b.get("time", ""))}</span></div>')
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
    if qa_items:
        out.append('<div class="qa"><div class="qa-h">Спросят — отвечаю</div>')
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
        '<p class="lede">Шпаргалка для устного разговора. Слева номер блока, справа — сколько он звучит. '
        'Каждая строка со стрелкой — одна произнесённая мысль. Под блоком — вопросы, которые последуют, '
        "и готовые ответы. Все цифры — оценки из плана версии 1.1, проверяются в первые 30 дней.</p>",
    ]
    if qa.get("opening"):
        parts.append('<div class="cover-box"><h2>Держать в голове весь разговор</h2>'
                     + "<ul class='tight'>"
                     + "".join(f"<li>{esc(x)}</li>" for x in qa["opening"])
                     + "</ul></div>")
    for b in blocks:
        parts.append(render_block(b, by_block.get(b["n"], [])))

    if qa.get("must_know_numbers"):
        parts.append('<section class="pagebreak"><h1>Цифры наизусть</h1>'
                     '<ul class="tight two-col">'
                     + "".join(f"<li>{esc(x)}</li>" for x in qa["must_know_numbers"])
                     + "</ul></section>")
    if qa.get("killer_questions"):
        parts.append('<section><div class="block-head"><span class="btitle">Опасные вопросы</span></div>'
                     '<ul class="tight">'
                     + "".join(f"<li>{esc(x)}</li>" for x in qa["killer_questions"])
                     + "</ul></section>")
    if qa.get("never_say"):
        parts.append('<section><div class="block-head"><span class="btitle">Не говорить никогда</span></div>'
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
