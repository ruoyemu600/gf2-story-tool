#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
在 bundle 批次里搜 Utage 剧本特征(快速版:解密+字符串搜索,不做对象解析)。
命中分类:
  PATH  含 Assets/Utage/BuildResources/... (剧本路径引用)
  SCEN  含 ScenarioData/AdvScenario/AdvCommandText(剧本数据结构)
  CHN   含 5+ 连续中文字符(文本内容)
  CJK_CHAPTER 含 CN_Chapter/MainStory/ChapterXX 等章节名
输出 JSON + 每类前若干样例。

用法:python3 tools/scan_utage.py --dir <目录> --out out/utage_scan.json
"""
import argparse
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gf2_bundle import decrypt  # noqa: E402

PATHS = [b"Assets/Utage/BuildResources", b"BuildResources/NewAVG", b"BuildResources/MainStory"]
SCEN = [b"AdvScenario", b"ScenarioData", b"AdvCommandText", b"AdvEngine", b"ScenarioPage"]
CHN = re.compile(rb'[\xe4-\xe9][\x80-\xbf]{2}(?:[\xe4-\xe9][\x80-\xbf]{2}){9,}')
CHAP = re.compile(rb'CN_Chapter\d+|MainStory/Chapter\d+|Activity/Chapter[A-Z]?\d+')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--out", default="out/utage_scan.json")
    args = ap.parse_args()
    files = sorted(glob.glob(os.path.join(args.dir, "*.bundle")))
    hits = []
    for i, p in enumerate(files, 1):
        try:
            plain = decrypt(open(p, "rb").read())
        except Exception:
            continue
        rec = {"bundle": os.path.basename(p),
               "path": any(k in plain for k in PATHS),
               "scen": any(k in plain for k in SCEN),
               "chn": len(CHN.findall(plain)),
               "chap": len(set(CHAP.findall(plain)))}
        if rec["path"] or rec["scen"] or rec["chn"] >= 5 or rec["chap"]:
            # 记录章节名样例
            if rec["chap"]:
                rec["chap_samples"] = [c.decode() for c in sorted(set(CHAP.findall(plain)))[:5]]
            hits.append(rec)
        if i % 500 == 0:
            print("  已扫 %d/%d,命中 %d" % (i, len(files), len(hits)), flush=True)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(hits, fh, ensure_ascii=False, indent=1)
    path_n = sum(1 for h in hits if h["path"])
    scen_n = sum(1 for h in hits if h["scen"])
    print("扫描 %d,命中 %d (path %d, scen %d)" % (len(files), len(hits), path_n, scen_n))
    for h in hits[:25]:
        print("  %-40s path=%s scen=%s chn=%d chap=%s" % (
            h["bundle"][:34], h["path"], h["scen"], h["chn"], h.get("chap_samples", [])))


if __name__ == "__main__":
    main()
