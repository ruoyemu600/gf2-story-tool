#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""找出哪张表的哪个字段引用了 AvgContentData 的 id(台词序列的挂载点)。"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gf2_table import read_table, parse_fields
from gf2_extract import load_table, lang_ref, as_text

TABLE = "/sdcard/Download/gf2-dump/Table"

# AvgContent id 集合 + 它们的前缀(可能的"剧情单元"编号)
contents = set()
body = read_table(TABLE, "AvgContentData.bytes")
for f, w, v in parse_fields(body):
    if f == 1 and w == 2:
        for f2, w2, v2 in parse_fields(v):
            if f2 == 1 and v2 > 10**6:
                contents.add(v2)
print("AvgContent ids: %d, 样例 %s" % (len(contents), sorted(contents)[:5]))

# 候选引用:任何表的任何 varint 字段值落在 AvgContent id 里,
# 或等于 id//100 / id//1000(上级单元号)
prefix100 = {c // 100 for c in contents if c // 100 > 10**6}
prefix1000 = {c // 1000 for c in contents if c // 1000 > 10**6}

for name in sorted(os.listdir(TABLE)):
    if not name.endswith(".bytes") or name.startswith("LangPackage"):
        continue
    try:
        rows = load_table(TABLE, name)
    except Exception:
        continue
    stat = defaultdict(int)
    for r in rows[:400]:
        for fno, v in r.items():
            if isinstance(v, int) and v > 1000:
                if v in contents:
                    stat["f%d→content" % fno] += 1
                elif v in prefix100:
                    stat["f%d→/100" % fno] += 1
                elif v in prefix1000:
                    stat["f%d→/1000" % fno] += 1
    if stat:
        print("%-34s %s" % (name, dict(stat)))
