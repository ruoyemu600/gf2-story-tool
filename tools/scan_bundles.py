#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量扫描 bundle 目录:解密 + UnityPy,统计对象类型,列出所有 TextAsset 名。
用途:在拷贝出的 bundle 批次里定位剧本配置(TextAsset 的 m_Name 形如 M01101)。

用法:python3 tools/scan_bundles.py --dir /sdcard/cccodroid/bundle_probe2 --out out/scan.json
"""
import argparse
import glob
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gf2_bundle import load_env  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--out", default="out/scan.json")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.dir, "*.bundle")))
    kinds = Counter()
    text_assets = []
    failed = []
    for i, p in enumerate(files, 1):
        try:
            env = load_env(p)
            for o in env.objects:
                kinds[o.type.name] += 1
                if o.type.name == "TextAsset":
                    try:
                        d = o.read()
                        text_assets.append({"bundle": os.path.basename(p),
                                            "name": d.m_Name,
                                            "size": len(d.m_Script) if isinstance(d.m_Script, str) else len(str(d.m_Script))})
                    except Exception:
                        pass
        except Exception as e:
            failed.append({"bundle": os.path.basename(p), "err": "%s: %s" % (type(e).__name__, e)})
        if i % 500 == 0:
            print("  已扫 %d/%d,TextAsset %d" % (i, len(files), len(text_assets)), flush=True)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    report = {"scanned": len(files), "failed": len(failed),
              "kinds": dict(kinds.most_common()), "text_assets": text_assets,
              "failures": failed[:50]}
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    print("扫描 %d,失败 %d,TextAsset %d,类型: %s" %
          (len(files), len(failed), len(text_assets), dict(kinds.most_common(8))))
    for t in text_assets[:20]:
        print("  %-40s %s (%d B)" % (t["name"], t["bundle"][:34], t["size"]))


if __name__ == "__main__":
    main()
