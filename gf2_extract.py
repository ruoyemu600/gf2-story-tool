#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GF2(少女前线2:追放)剧情语料提取器 v2 —— 只提取「可证」内容。

v2 范围(全部有数据证据,无猜测归属):
  avg3d     Avg3dContentData 2.2万行:演出正文(对白+括号旁白)。
            组 = id//1000,组内 id 升序 = 阅读序。1473 组。
  dialogue  DialoguePageData 2366页:宿舍/档案对话,f3=说话人,f4=头像资源名。
            组 = f2,页序 = id%1000。
  guildwar  GuildwarStoryData -> f6 packed 段落序列 -> GuildwarStoryParagraphData。
            标题/时间戳/前章链完整。
  章节/关卡结构(ChapterData/StoryData)输出为骨架 JSON,供 v2 归属时 join。

明确排除(证据不支持):
  AvgContentData 17.5万条 = 系统文本池(公告/邮件/成就),非剧情,不入书。
  组<->章节 的归属编码 —— 未破译,不猜。v2 若拿到演出配置再接。

清洗规则:
  - f2/f3 双文本:取 f3,空则 f2(实测两者同文)
  - 富文本标签 <color=..> </color> <b> </b> <size=..> </size> 剥离,
    但 <color>名:</color> 开头的提取为 speaker
  - {} 占位符保留原样(动态填充名,v2 决定替换策略)

用法:
  python3 gf2_extract.py --table /sdcard/Download/gf2-dump/Table --out out
"""
import argparse
import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gf2_table import read_table, parse_fields, read_varint  # noqa: E402


TAG_RE = re.compile(r"</?(?:color|b|i|u|size|sprite[^>]*)[^>]*>")
SPEAKER_TAG_RE = re.compile(r"^\s*<color=[^>]*>([^<]{1,20}?)[:：]\s*</color>\s*")
SPEAKER_PLAIN_RE = re.compile(r"^([^\s，。！？""]{1,12}?)[:：]\s*")


def clean_text(raw):
    """返回 (speaker, text)。speaker 可能为 None。
    两种说话人格式:<color=..>名:</color>文 / 裸「名:文」(名≤12字,无标点)。"""
    if not raw:
        return None, ""
    speaker = None
    m = SPEAKER_TAG_RE.match(raw)
    if m:
        speaker = m.group(1).strip()
        raw = raw[m.end():]
    else:
        m = SPEAKER_PLAIN_RE.match(raw)
        if m:
            speaker = m.group(1).strip()
            raw = raw[m.end():]
    txt = TAG_RE.sub("", raw).strip()
    return (speaker or None), txt


def unpack_packed(buf):
    out, i = [], 0
    try:
        while i < len(buf):
            v, i = read_varint(buf, i)
            out.append(v)
        return out
    except Exception:
        return None


def lang_ref(v):
    if isinstance(v, (bytes, bytearray)):
        for f, w, x in parse_fields(v):
            if f == 1 and w == 0:
                return x
    return None


def load_lang(table_dir):
    ids = {}
    for name in ("LangPackageTableCnBuiltinData.bytes", "LangPackageTableCnData.bytes"):
        for f, w, v in parse_fields(read_table(table_dir, name)):
            if f == 1 and w == 2:
                rid, txt = None, ""
                for f2, w2, v2 in parse_fields(v):
                    if f2 == 1:
                        rid = v2
                    elif f2 == 2:
                        txt = v2.decode("utf-8", "replace")
                if rid is not None:
                    ids[rid] = txt
    return ids


def flat_records(table_dir, name):
    for f, w, v in parse_fields(read_table(table_dir, name)):
        if f == 1 and w == 2:
            rec = {}
            for f2, w2, v2 in parse_fields(v):
                rec[f2] = v2
            yield rec


def extract_avg3d(table_dir, lang):
    """组 -> 按序台词行"""
    groups = defaultdict(list)
    for r in flat_records(table_dir, "Avg3dContentData.bytes"):
        lid = r.get(1)
        if not isinstance(lid, int):
            continue
        t3, t2 = lang_ref(r.get(3)), lang_ref(r.get(2))
        raw = (lang.get(t3) if t3 is not None else "") or (lang.get(t2) if t2 is not None else "")
        speaker, txt = clean_text(raw)
        if not txt:
            continue
        groups[lid // 1000].append({
            "id": lid, "seq": lid % 1000, "speaker": speaker, "text": txt,
        })
    for g in groups:
        groups[g].sort(key=lambda x: x["id"])
    return groups


def extract_dialogue_pages(table_dir, lang):
    groups = defaultdict(list)
    for r in flat_records(table_dir, "DialoguePageData.bytes"):
        lid, grp = r.get(1), r.get(2)
        if not isinstance(lid, int) or not isinstance(grp, int):
            continue
        t9, t8 = lang_ref(r.get(9)), lang_ref(r.get(8))
        raw = (lang.get(t9) if t9 is not None else "") or (lang.get(t8) if t8 is not None else "")
        _, txt = clean_text(raw)
        if not txt:
            continue
        avatar = r.get(4)
        avatar = avatar.decode("utf-8", "replace") if isinstance(avatar, (bytes, bytearray)) else ""
        groups[grp].append({
            "id": lid, "seq": lid % 1000,
            "speaker": lang.get(lang_ref(r.get(3)), "") if lang_ref(r.get(3)) else "",
            "avatar": avatar, "text": txt,
        })
    for g in groups:
        groups[g].sort(key=lambda x: x["id"])
    return groups


def extract_guildwar(table_dir, lang):
    """Story(标题/段序列) -> Paragraph(文本)"""
    paras = {}
    for r in flat_records(table_dir, "GuildwarStoryParagraphData.bytes"):
        pid = r.get(1)
        if not isinstance(pid, int):
            continue
        t3 = lang_ref(r.get(3)) or lang_ref(r.get(2))
        paras[pid] = (lang.get(t3) or "") if t3 is not None else ""
    stories = []
    for r in flat_records(table_dir, "GuildwarStoryData.bytes"):
        sid = r.get(1)
        if not isinstance(sid, int):
            continue
        seq_raw = r.get(6)
        seq = unpack_packed(seq_raw) if isinstance(seq_raw, (bytes, bytearray)) else []
        title_id = lang_ref(r.get(3))
        lines = []
        for pid in seq:
            txt = paras.get(pid, "")
            if txt:
                speaker, t = clean_text(txt)
                lines.append({"id": pid, "speaker": speaker, "text": t})
        if lines:
            pre = r.get(5)
            stories.append({
                "id": sid,
                "title": lang.get(title_id, "") if title_id is not None else "",
                "chapter_seq": r.get(2),
                "pre": pre if isinstance(pre, int) else None,
                "lines": lines,
            })
    stories.sort(key=lambda s: (s["chapter_seq"] or 0, s["id"]))
    return stories


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", required=True)
    ap.add_argument("--out", default="out")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    lang = load_lang(args.table)
    corpus = {}

    g3d = extract_avg3d(args.table, lang)
    corpus["avg3d"] = {"groups": [
        {"group": g, "lines": rows} for g, rows in sorted(g3d.items())
    ]}
    dpages = extract_dialogue_pages(args.table, lang)
    corpus["dialogue"] = {"groups": [
        {"group": g, "lines": rows} for g, rows in sorted(dpages.items())
    ]}
    gw = extract_guildwar(args.table, lang)
    corpus["guildwar"] = {"stories": gw}

    with open(os.path.join(args.out, "corpus.json"), "w", encoding="utf-8") as fh:
        json.dump(corpus, fh, ensure_ascii=False, indent=1)

    report = {
        "lang_entries": len(lang),
        "avg3d_groups": len(g3d),
        "avg3d_lines": sum(len(v) for v in g3d.values()),
        "dialogue_groups": len(dpages),
        "dialogue_lines": sum(len(v) for v in dpages.values()),
        "guildwar_stories": len(gw),
        "guildwar_lines": sum(len(s["lines"]) for s in gw),
    }
    with open(os.path.join(args.out, "report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
