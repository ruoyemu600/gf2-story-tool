#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P1: 全表 f1 注册表匹配。

1) 建注册表:每张表的 f1 id 全集。
2) 对"悬空引用"做整数值精确匹配(禁止拆位/前缀):
   - KittyCafeContentByDialogueIdData.f2 packed
   - KittyCafeDialogueData.f9
   - LoveAvgByGunIdData.f2 packed / CharacterAvgByGunIdData.f2 packed
   - ChessStoryData.f3
   - LobbyGunStoryByGunIdData.f2 packed
3) 判据:命中率 >80% 的表 = 持有正文的行表。

用法:python3 tools/registry_match.py --table <Table目录>
"""
import argparse
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gf2_table import read_table, parse_fields  # noqa: E402
from gf2_extract import flat_records, unpack_packed  # noqa: E402

SKIP = ("LangPackage",)


def f1_ids(table_dir, name):
    return {r[1] for r in flat_records(table_dir, name) if isinstance(r.get(1), int)}


def build_registry(table_dir):
    reg = {}
    for name in sorted(os.listdir(table_dir)):
        if not name.endswith(".bytes") or name.startswith(SKIP):
            continue
        try:
            reg[name] = f1_ids(table_dir, name)
        except Exception as e:
            print("  skip %s: %s" % (name, e))
    return reg


def refs_of(table_dir, table, field, unpack=False):
    vals = []
    for r in flat_records(table_dir, table):
        v = r.get(field)
        if isinstance(v, int):
            vals.append(v)
        elif isinstance(v, (bytes, bytearray)) and unpack:
            arr = unpack_packed(v)
            if arr:
                vals.extend(arr)
    return vals


def match(reg, vals, exclude=()):
    """整值精确匹配:返回 [(表名, 命中数)] 按命中降序。"""
    res = []
    s = set(vals)
    for name, ids in reg.items():
        if name in exclude:
            continue
        hit = len(s & ids)
        if hit:
            res.append((name, hit))
    res.sort(key=lambda x: -x[1])
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", required=True)
    args = ap.parse_args()
    T = args.table

    print("建注册表 ...")
    reg = build_registry(T)
    print("表数 %d,样例 f1 量:%s" % (
        len(reg), {k: len(v) for k, v in list(reg.items())[:3]}))

    cases = [
        ("B1 KittyCafeContent.f2", "KittyCafeContentByDialogueIdData.bytes", 2, True),
        ("B1 KittyCafeDialogue.f9", "KittyCafeDialogueData.bytes", 9, False),
        ("B1 Kittycafe2Content.f2", "Kittycafe2ContentByDialogueIdData.bytes", 2, True),
        ("B2 LoveAvgByGunId.f2", "LoveAvgByGunIdData.bytes", 2, True),
        ("B2 CharacterAvgByGunId.f2", "CharacterAvgByGunIdData.bytes", 2, True),
        ("B3 ChessStory.f3", "ChessStoryData.bytes", 3, False),
        ("B4 LobbyGunStoryByGunId.f2", "LobbyGunStoryByGunIdData.bytes", 2, True),
    ]
    for label, table, field, unpack in cases:
        if not os.path.exists(os.path.join(T, table)):
            print("\n══ %s: 表不存在 %s" % (label, table))
            continue
        vals = refs_of(T, table, field, unpack)
        if not vals:
            print("\n══ %s: 无引用值" % label)
            continue
        uniq = len(set(vals))
        top = match(reg, vals, exclude={table})
        print("\n══ %s: %d 值(去重 %d)" % (label, len(vals), uniq))
        for name, hit in top[:5]:
            print("   %-42s 命中 %d/%d = %.1f%%" % (name, hit, uniq, 100 * hit / uniq))
        if not top:
            print("   无任何命中")


if __name__ == "__main__":
    main()
