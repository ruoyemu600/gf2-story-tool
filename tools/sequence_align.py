#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v2.2 ① B4/B2 序对位验证。

假设:Avg3DPlotData(1497 条,编排)与 Avg3dContentData 的组(1474 个,文本行)
按各自 f1/组号升序排列后,第 N 项一一对应(无显式外键的平行序列)。

判据(按序):
1. 角色交集:前 20 对,plot.f5 角色 id 数组 → 名字 ↔ 组内文本出现该名字,平均 >50%。
2. 章节隔离:M01xxx 5 对 / M08xxx 5 对,第 1 章的组不应出现第 8 章特有角色。
3. 首尾校准:若整体 <50% 但首尾命中,推段偏移后重验。

失败即按 plan-v2.2 规则收手(不再试第三种排序)。

用法:python3 tools/sequence_align.py --table <Table目录>
"""
import argparse
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gf2_table import read_table, parse_fields  # noqa: E402
from gf2_extract import load_lang, lang_ref, flat_records, clean_text  # noqa: E402


def build_gun_names(T, lang):
    names = {}
    for r in flat_records(T, "GunData.bytes"):
        gid = r.get(1)
        lr = lang_ref(r.get(2)) or lang_ref(r.get(3))
        if isinstance(gid, int) and lr is not None and lang.get(lr):
            names[gid] = lang[lr].strip()
    return names


def load_plots(T):
    """Avg3DPlotData 按 f1 升序: [{id, txtName, roles:[ids]}]"""
    out = []
    for f, w, v in parse_fields(read_table(T, "Avg3DPlotData.bytes")):
        if f != 1 or w != 2:
            continue
        r = {}
        roles = []
        for f2, w2, v2 in parse_fields(v):
            if f2 == 1 and w2 == 0:
                r["id"] = v2
            elif f2 == 3 and w2 == 2:
                try:
                    r["txtName"] = v2.decode("utf-8", "replace")
                except Exception:
                    pass
            elif f2 == 5 and w2 == 2:          # repeated {f1: role_id}
                for a, b, c in parse_fields(v2):
                    if a == 1 and b == 0:
                        roles.append(c)
        if "id" in r:
            r["roles"] = roles
            out.append(r)
    out.sort(key=lambda x: x["id"])
    return out


def load_groups(T):
    """演出组按组号升序: [{group, text, speakers}]"""
    per = defaultdict(lambda: {"chunks": [], "speakers": set()})
    for f, w, v in parse_fields(read_table(T, "Avg3dContentData.bytes")):
        if f != 1 or w != 2:
            continue
        lid = None
        t3 = t2 = None
        for f2, w2, v2 in parse_fields(v):
            if f2 == 1:
                lid = v2
            elif f2 == 3:
                for a, b, c in parse_fields(v2):
                    if a == 1 and b == 0:
                        t3 = c
            elif f2 == 2:
                for a, b, c in parse_fields(v2):
                    if a == 1 and b == 0:
                        t2 = c
        if lid is None:
            continue
        raw = (t3 is not None and lang_get(t3)) or (t2 is not None and lang_get(t2)) or ""
        if not raw:
            continue
        spk, txt = clean_text(raw)
        g = lid // 1000
        per[g]["chunks"].append(txt)
        if spk:
            per[g]["speakers"].add(spk)
    out = []
    for g in sorted(per):
        out.append({"group": g, "text": "\n".join(per[g]["chunks"]),
                    "speakers": per[g]["speakers"]})
    return out


LANG = None


def lang_get(i):
    return LANG.get(i, "") if i is not None else ""


def role_hit_rate(plot, group, gun_names):
    """plot 角色名在组内文本出现(名字子串或内嵌说话人)的比例。"""
    names = [gun_names.get(r) for r in plot.get("roles", [])]
    names = [n for n in names if n]
    if not names:
        return None
    hit = sum(1 for n in names if n in group["text"] or n in group["speakers"])
    return hit / len(names)


def chapter_of(plot):
    tn = plot.get("txtName", "")
    if tn.startswith("M") and len(tn) >= 3:
        return tn[1:3]
    return None


def main():
    global LANG
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", required=True)
    args = ap.parse_args()
    T = args.table
    LANG = load_lang(T)
    gun = build_gun_names(T, LANG)
    plots = load_plots(T)
    groups = load_groups(T)
    print("plot %d 条, 组 %d 个, GunData 名字 %d" % (len(plots), len(groups), len(gun)))

    n = min(len(plots), len(groups))
    pairs = list(zip(plots[:n], groups[:n]))

    # ---- 判据 1:前 20 对角色交集 ----
    print("\n== 判据1:前 20 对角色交集 ==")
    rates = []
    for i, (p, g) in enumerate(pairs[:20]):
        r = role_hit_rate(p, g, gun)
        rates.append(r)
        rn = [gun.get(x, "?") for x in p.get("roles", [])][:4]
        print("  #%2d plot %-7d(%s) roles=%s -> %s" % (
            i + 1, p["id"], p.get("txtName", "?"), rn,
            ("%.0f%%" % (r * 100)) if r is not None else "无角色"))
    valid = [r for r in rates if r is not None]
    avg = sum(valid) / len(valid) if valid else 0
    print("  平均交集率: %.1f%% (%d 对有效)" % (avg * 100, len(valid)))

    # ---- 判据 2:章节隔离 ----
    print("\n== 判据2:章节隔离(M01xxx vs M08xxx)==")
    def chapter_pairs(ch):
        return [(p, g) for p, g in pairs if chapter_of(p) == ch][:5]
    c1, c8 = chapter_pairs("01"), chapter_pairs("08")
    roles1 = {r for p, _ in c1 for r in p.get("roles", [])}
    roles8 = {r for p, _ in c8 for r in p.get("roles", [])}
    only8 = {gun[r] for r in roles8 - roles1 if r in gun}
    only1 = {gun[r] for r in roles1 - roles8 if r in gun}
    print("  第1章 plot 对数 %d,角色 %d;第8章 %d,角色 %d" % (
        len(c1), len(roles1), len(c8), len(roles8)))
    leak = 0
    for p, g in c1:
        for nm in only8:
            if nm in g["text"] or nm in g["speakers"]:
                leak += 1
                break
    print("  第1章组出现第8章特有角色: %d/%d" % (leak, len(c1)))

    # ---- 判据 3:首尾校准提示 ----
    print("\n== 判据3:首尾逐对明细(校准用)==")
    for idx in (0, 1, 2, n - 3, n - 2, n - 1):
        p, g = pairs[idx]
        r = role_hit_rate(p, g, gun)
        print("  idx %4d: plot %-7d(%s) group %-7d %s" % (
            idx, p["id"], p.get("txtName", "?"), g["group"],
            ("%.0f%%" % (r * 100)) if r is not None else "无角色"))

    # ---- 结论 ----
    ok1 = avg > 0.5
    ok2 = (leak == 0) and (len(c1) > 0 and len(c8) > 0)
    print("\n结论: 判据1(>50%%) = %s;判据2(无交叉) = %s" % (ok1, ok2))
    print("VERDICT:", "PASS" if (ok1 and ok2) else "FAIL")


if __name__ == "__main__":
    main()
