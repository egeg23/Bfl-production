#!/usr/bin/env python3
"""Merge persona Q&A + fact-check fixes into docs/cheatsheet/qa.json.

Reads the raw workflow output (items + verify chunks), applies corrected answers,
deduplicates near-identical questions, caps the number per block and maps
persona block labels onto the numbered blocks of the cheat sheet.

Usage: python3 scripts/merge_qa.py <raw_json> [--cap N]
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "cheatsheet" / "qa.json"

# persona label -> cheat sheet block number ("stress" goes to its own section)
BLOCK_MAP = {
    "О себе и почему я": "1",
    "Что за продукт": "2",
    "Аффилированность и право": "3",
    "Партнёры и продажи": "4",
    "Производство и SLA": "5",
    "Экономика и цифры": "6",
    "План 30/60/90": "8",
    "IT и данные": "9",
    "Команда и организация": "11",
    "Условия и мотивация": "13",
    "Каверзные/стресс": "stress",
}
RISK_ORDER = {"high": 0, "medium": 1, "low": 2}

# keyword router: some questions belong to a block the persona label does not name
KEYWORDS = (
    ("7", r"конфигурац|гибрид|регионал|сет[ьи] исполнител|аутсорс модел|централизов|вариант [абв]\b"),
    ("10", r"риск|жалоб|отзыв|утечк|фас\b|роспотреб|репутац|скандал|штраф за реклам|проверк"),
    ("12", r"что вам нужно от нас|какие вопросы|полномочи|бюджет|спонсор|кто принимает решени"),
    ("2", r"что мы продаём|зачем партнёру|почему отдаст|ценност|конкурент|франшиз"),
)
STOP = set("и в во не что он на я с со как а то все она так его но да ты к у же вы за бы по "
           "её мне было вот от меня ещё нет о из ему теперь когда даже ну вдруг ли если или "
           "быть был вам чтобы это этот эта эти для при над под про мы вас наш ваш то есть".split())


def norm(q):
    words = re.findall(r"[а-яёa-z0-9]+", q.lower())
    return {w for w in words if w not in STOP and len(w) > 2}


def similar(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def main():
    raw = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    cap = 6
    if "--cap" in sys.argv:
        cap = int(sys.argv[sys.argv.index("--cap") + 1])

    fixes, must, killers = {}, [], []
    for v in raw.get("verify", []):
        for f in v.get("fixes", []):
            fixes[f["question"].strip()] = f["corrected_answer"]
        must += v.get("must_know_numbers", [])
        killers += v.get("killer_questions", [])

    items = []
    for it in raw["items"]:
        it = dict(it)
        fix = fixes.get(it["question"].strip())
        if fix:
            it["answer"] = fix
            it["fixed"] = True
        it["block_n"] = BLOCK_MAP.get(it.get("block", ""), "stress")
        it["_alt"] = [b for b, pat in KEYWORDS if re.search(pat, it["question"].lower())]
        it["_k"] = norm(it["question"])
        items.append(it)

    items.sort(key=lambda x: (RISK_ORDER.get(x.get("risk"), 3), -len(x["answer"])))
    kept = []
    for it in items:
        if any(similar(it["_k"], k["_k"]) >= 0.5 for k in kept):
            continue
        kept.append(it)
    dropped_dup = len(items) - len(kept)

    per_block, final, overflow = {}, [], []
    for it in kept:
        b = it["block_n"]
        limit = 10 if b == "stress" else cap
        if per_block.get(b, 0) >= limit:
            overflow.append(it)
            continue
        per_block[b] = per_block.get(b, 0) + 1
        it.pop("_k", None)
        final.append(it)

    # fill thin blocks from the overflow using the keyword router
    moved = 0
    for it in overflow:
        for b in it.get("_alt", []):
            if per_block.get(b, 0) < cap:
                it["block_n"] = b
                per_block[b] = per_block.get(b, 0) + 1
                it.pop("_k", None)
                it.pop("_alt", None)
                final.append(it)
                moved += 1
                break
    for it in final:
        it.pop("_alt", None)

    # keep the numbered blocks in reading order, stress section last
    order = {str(n): n for n in range(1, 14)}
    final.sort(key=lambda x: (order.get(x["block_n"], 99), RISK_ORDER.get(x.get("risk"), 3)))

    data = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    data["items"] = final
    seen = set()
    data["must_know_numbers"] = [x for x in must if not (x in seen or seen.add(x))]
    seen = set()
    data["killer_questions"] = [x for x in killers if not (x in seen or seen.add(x))]
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"вошло {len(final)} из {len(raw['items'])} (дублей снято {dropped_dup}); "
          f"по блокам {dict(sorted(per_block.items(), key=lambda kv: order.get(kv[0], 99)))}; "
          f"перенесено по ключевым словам {moved}")


if __name__ == "__main__":
    main()
