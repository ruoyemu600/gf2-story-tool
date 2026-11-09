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
SPEAKER_PLAIN_RE = re.compile(r"^([^\s，。！？“”'\"：:]{1,12}?)[:：]\s*")


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
            name = m.group(1).strip()
            # {} 占位符不是说话人(动态填充的主角名另走保留策略)
            if "{" in name or "}" in name:
                m = None
            else:
                speaker = name
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
    """msg{f1: lang_id} -> id;非 msg 的 bytes(头像名/图路径等)安全返回 None。"""
    if isinstance(v, (bytes, bytearray)):
        try:
            for f, w, x in parse_fields(v):
                if f == 1 and w == 0:
                    return x
        except Exception:
            return None
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


def _asset_path(v):
    """f4 的 packed varint 数组是 UTF-8 资源路径的字节序列("Assets/...")。"""
    if not isinstance(v, (bytes, bytearray)):
        return ""
    arr = unpack_packed(v)
    if not arr or not all(0 < x < 256 for x in arr):
        return ""
    try:
        s = bytes(arr).decode("utf-8")
        return s if s.startswith(("Assets/", "assets/")) else ""
    except UnicodeDecodeError:
        return ""


def extract_guildwar(table_dir, lang):
    """Story(标题/段序列) -> Paragraph(文本或演出占位)。
    段落表实测:344 引用段中 109 段无文本、f4 为 Assets 视频路径 —— 是纯演出段,
    按诚实原则输出占位行,让读者知道此处有视频而非静默缺失。"""
    paras = {}
    for r in flat_records(table_dir, "GuildwarStoryParagraphData.bytes"):
        pid = r.get(1)
        if not isinstance(pid, int):
            continue
        t3 = lang_ref(r.get(3)) or lang_ref(r.get(13))
        txt = (lang.get(t3) or "") if t3 is not None else ""
        paras[pid] = (txt, _asset_path(r.get(4)))
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
            txt, asset = paras.get(pid, ("", ""))
            if txt:
                speaker, t = clean_text(txt)
                lines.append({"id": pid, "speaker": speaker, "text": t})
            else:
                label = "〔演出片段%s〕" % ("：" + os.path.basename(asset) if asset else "")
                lines.append({"id": pid, "speaker": None, "text": label})
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


# ---------- 支线家族(T1):结构已验证的「说话人+台词」直出族 ----------

SIMPLE_FAMILIES = {
    # family: (表, 说话人字段, 台词字段, 选项字段)
    "lobby": ("LobbyDialogueData.bytes", None, 3, 6),   # f3 台词;f6 选项(植物的长势)
    "adjutant": ("AdjutantConversationData.bytes", None, 3, None),  # f3 台词;角色从动画名解
    "lounge": ("LoungeDialogData.bytes", 3, 4, None),   # f3 名 f4 台词
    "behavior": ("BehaviorDialogData.bytes", 3, 4, None),  # f3 名 f4 台词
    "darkzone": ("DarkzoneDialogueData.bytes", 5, 6, None),  # f5 名 f6 台词
}


def _char_from_anim(anim):
    """c_Charolic_idle_to_apathy -> Charolic"""
    if not anim:
        return ""
    m = re.match(r"^c_([A-Za-z0-9]+)_", anim)
    return m.group(1) if m else ""


def _text_field(r, f, lang):
    """字段 -> 文本:先按 lang 引用解,再尝试内嵌 utf-8。"""
    if f is None:
        return ""
    lr = lang_ref(r.get(f))
    if lr is not None and lang.get(lr):
        return lang[lr]
    v = r.get(f)
    if isinstance(v, (bytes, bytearray)):
        try:
            s = v.decode("utf-8")
            if s and all(31 < ord(c) or c in "\n\t" for c in s):
                return s
        except UnicodeDecodeError:
            pass
    return ""


def extract_simple_families(table_dir, lang):
    """返回 {family: [{"group": 组名, "lines": [...]}]}。
    分组:lounge/behavior/adjutant 按说话人;lobby/darkzone 整族一组的对话串。"""
    out = {}
    for fam, (tname, spk_f, txt_f, opt_f) in SIMPLE_FAMILIES.items():
        per_group = defaultdict(list)
        for r in flat_records(table_dir, tname):
            rid = r.get(1)
            if not isinstance(rid, int):
                continue
            text = _text_field(r, txt_f, lang)
            speaker = _text_field(r, spk_f, lang)
            if fam == "adjutant" and not speaker:
                for k in (4, 5, 6):
                    v = r.get(k)
                    if isinstance(v, (bytes, bytearray)):
                        try:
                            speaker = _char_from_anim(v.decode("utf-8"))
                        except UnicodeDecodeError:
                            pass
                        if speaker:
                            break
            if not text:
                continue
            _, text = clean_text(text)
            entry = {"id": rid, "speaker": speaker or None, "text": text}
            if opt_f:
                opt = _text_field(r, opt_f, lang)
                if opt:
                    _, entry["option"] = clean_text(opt)
            # 分角色族按说话人分;无名行归「旁白」组(不猜归属)
            if fam in ("lounge", "behavior", "adjutant"):
                gname = speaker or "旁白"
            else:
                gname = fam
            per_group[gname].append(entry)
        out[fam] = [
            {"group": g, "lines": sorted(rows, key=lambda x: x["id"])}
            for g, rows in sorted(per_group.items())
        ]
    return out


# ---------- T6:叙事长文(邮件/日志/论坛贴),从系统文本池人工确认后入书 ----------

EMAIL_MIN = 120


def _narrative(txt):
    """叙事特征 >=2:对指挥官/引号/换行/第一人称——过滤纯公告。"""
    return sum([("指挥官" in txt), ('"' in txt or "「" in txt or "“" in txt),
                ("\n" in txt), ("我" in txt)]) >= 2


def extract_emails(table_dir, lang):
    """AvgContentData 中 >=120 字且带叙事特征的长文;每封一篇,段内换行拆行。"""
    out = []
    for r in flat_records(table_dir, "AvgContentData.bytes"):
        lid = r.get(1)
        if not isinstance(lid, int):
            continue
        t3, t2 = lang_ref(r.get(3)), lang_ref(r.get(2))
        txt = (lang.get(t3) if t3 is not None else "") or (lang.get(t2) if t2 is not None else "")
        if len(txt) < EMAIL_MIN or not _narrative(txt):
            continue
        _, clean = clean_text(txt)
        paras = [p.strip() for p in clean.split("\n") if p.strip()]
        if not paras:
            continue
        out.append({"id": lid, "paras": paras})
    out.sort(key=lambda x: x["id"])
    return out


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
    corpus["simple"] = extract_simple_families(args.table, lang)
    corpus["email"] = extract_emails(args.table, lang)

    with open(os.path.join(args.out, "corpus.json"), "w", encoding="utf-8") as fh:
        json.dump(corpus, fh, ensure_ascii=False, indent=1)

    simple_stats = {
        fam: {"groups": len(gs), "lines": sum(len(g["lines"]) for g in gs)}
        for fam, gs in corpus["simple"].items()
    }
    report = {
        "lang_entries": len(lang),
        "avg3d_groups": len(g3d),
        "avg3d_lines": sum(len(v) for v in g3d.values()),
        "dialogue_groups": len(dpages),
        "dialogue_lines": sum(len(v) for v in dpages.values()),
        "guildwar_stories": len(gw),
        "guildwar_lines": sum(len(s["lines"]) for s in gw),
        "simple": simple_stats,
        "simple_lines_total": sum(v["lines"] for v in simple_stats.values()),
        "email_pieces": len(corpus["email"]),
        "email_paras": sum(len(e["paras"]) for e in corpus["email"]),
    }
    with open(os.path.join(args.out, "report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
