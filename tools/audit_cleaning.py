#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T2 清洗审计:产出 out/placeholders.tsv、docs/cleaning-diff.md,
并复测 is_roster 阈值。可重复运行,结果稳定。

用法:python3 tools/audit_cleaning.py --table <Table目录> --out out
"""
import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gf2_table import read_table, parse_fields  # noqa: E402
from gf2_extract import load_lang, lang_ref, clean_text  # noqa: E402
import gf2_books  # noqa: E402

PH_RE = re.compile(r"\{[^{}]{0,12}\}")
TABLES = ["Avg3dContentData", "DialoguePageData", "LobbyDialogueData",
          "AdjutantConversationData", "LoungeDialogData", "BehaviorDialogData",
          "DarkzoneDialogueData"]


def raw_texts(table_dir, tname, lang):
    for f, w, v in parse_fields(read_table(table_dir, tname + ".bytes")):
        if f != 1 or w != 2:
            continue
        for f2, w2, v2 in parse_fields(v):
            if w2 != 2:
                continue
            lr = lang_ref(v2)
            if lr is not None:
                yield lang.get(lr, "")
            else:
                try:
                    s = v2.decode("utf-8")
                    if s and all(31 < ord(c) or c in "\n\t" for c in s):
                        yield s
                except UnicodeDecodeError:
                    pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", required=True)
    ap.add_argument("--out", default="out")
    args = ap.parse_args()
    lang = load_lang(args.table)

    ph_by_table = defaultdict(Counter)
    samples = []
    roster_total = roster_hit = 0
    for t in TABLES:
        for raw in raw_texts(args.table, t, lang):
            if not raw:
                continue
            for m in PH_RE.finditer(raw):
                ph_by_table[t][m.group(0)] += 1
            if len(samples) < 20 and (PH_RE.search(raw) or "<" in raw or "：" in raw[:14] or ":" in raw[:14]):
                spk, txt = clean_text(raw)
                samples.append((t, raw, spk, txt))
    # roster 复测:用成书前的组数据
    corpus_path = os.path.join(args.out, "corpus.json")
    if os.path.exists(corpus_path):
        c = json.load(open(corpus_path, encoding="utf-8"))
        for g in c["avg3d"]["groups"]:
            roster_total += 1
            if gf2_books.is_roster(g["lines"]):
                roster_hit += 1

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "placeholders.tsv"), "w", encoding="utf-8") as fh:
        fh.write("table\tplaceholder\tcount\n")
        for t, cnt in ph_by_table.items():
            for p, n in cnt.most_common():
                fh.write("%s\t%s\t%d\n" % (t, p, n))

    os.makedirs("docs", exist_ok=True)
    with open(os.path.join("docs", "cleaning-diff.md"), "w", encoding="utf-8") as fh:
        fh.write("# 清洗前后对照(自动生成,样本 20 条)\n\n")
        fh.write("| 表 | 原文 | 说话人 | 清洗后 |\n|---|---|---|---|\n")
        for t, raw, spk, txt in samples:
            esc = lambda s: s.replace("|", "\\|").replace("\n", " ")
            fh.write("| %s | %s | %s | %s |\n" % (t, esc(raw[:60]), spk or "—", esc(txt[:60])))

    print("placeholders.tsv: %d 表" % len(ph_by_table))
    print("cleaning-diff.md: %d 样本" % len(samples))
    if roster_total:
        print("is_roster: %d/%d 组被判名单(%.1f%%)" % (
            roster_hit, roster_total, 100 * roster_hit / roster_total))


if __name__ == "__main__":
    main()
