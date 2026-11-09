#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T8:主线骨架 -> out/outline.json

ChapterData(章: f1=id, f3=章名, f4=序)
StoryData(关卡: f1=id, f2/f3=chapter, f5=pre, f6=next, f8=关卡名)
关卡按 pre/next 链拓扑排序(链断按 id 升序续),为 T9 归属 join 预置。

用法:python3 tools/build_outline.py --table <Table目录> --out out/outline.json
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gf2_table import read_table, parse_fields  # noqa: E402
from gf2_extract import lang_ref, load_lang, clean_text  # noqa: E402


def flat(body):
    for f, w, v in parse_fields(body):
        if f == 1 and w == 2:
            yield {a: c for a, b, c in parse_fields(v)}


def stage_order(stages):
    """pre 链拓扑排序;断链从剩余最小 id 续。"""
    if not stages:
        return []
    by_id = {s["id"]: s for s in stages}
    heads = [s for s in stages if s.get("pre") not in by_id] or [min(stages, key=lambda s: s["id"])]
    ordered, seen = [], set()

    def walk(s):
        while s and s["id"] not in seen:
            seen.add(s["id"])
            ordered.append(s)
            nxt = s.get("next")
            s = by_id.get(nxt) if isinstance(nxt, int) else None
        rest = [x for x in stages if x["id"] not in seen]
        if rest:
            walk(min(rest, key=lambda x: x["id"]))

    for h in sorted(heads, key=lambda s: s["id"]):
        walk(h)
    return ordered


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", required=True)
    ap.add_argument("--out", default="out/outline.json")
    args = ap.parse_args()
    lang = load_lang(args.table)

    chapters = {}
    for r in flat(read_table(args.table, "ChapterData.bytes")):
        cid = r.get(1)
        if isinstance(cid, int):
            nid = lang_ref(r.get(3))
            chapters[cid] = {
                "id": cid, "seq": r.get(4),
                "name": clean_text(lang.get(nid, ""))[1] if nid is not None else "",
            }
    by_ch = {}
    for r in flat(read_table(args.table, "StoryData.bytes")):
        sid, ch = r.get(1), (r.get(2) or r.get(3))
        if not isinstance(sid, int) or not isinstance(ch, int):
            continue
        nid = lang_ref(r.get(8)) or lang_ref(r.get(10))
        by_ch.setdefault(ch, []).append({
            "id": sid,
            "name": clean_text(lang.get(nid, ""))[1] if nid is not None else "",
            "pre": r.get(5) if isinstance(r.get(5), int) else None,
            "next": r.get(6) if isinstance(r.get(6), int) else None,
            "type": r.get(11),
        })

    outline = []
    for cid in sorted(chapters, key=lambda c: (chapters[c].get("seq") or 999, c)):
        sts = stage_order(by_ch.get(cid, []))
        outline.append({**chapters[cid], "stages": sts, "n_stages": len(sts)})

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(outline, fh, ensure_ascii=False, indent=1)
    named = sum(1 for c in outline if c["name"])
    total_st = sum(c["n_stages"] for c in outline)
    print("章 %d(有名字 %d),关卡 %d -> %s" % (len(outline), named, total_st, args.out))


if __name__ == "__main__":
    main()
