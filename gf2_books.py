#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GF2 剧情成书:corpus.json -> 合订本 txt + EPUB3。

卷册划分:
  演出剧情  avg3d 1474 组,按组号前缀(6位中的前4位)聚类成卷,组名=首行摘要
  宿舍对话  dialogue,按头像资源名(Avatar_Head_XXX)聚角色卷,滤占位组
  公会战    guildwar 102 篇按 chapter_seq 分卷,分支段保留

排版规则(继承 limbus-story-tool 的排版教训):
  - 对话:「名:文」;无说话人则缩进两格(旁白)
  - 同组内连发不重复名字 —— 但 GF2 组内 speaker 多为空(交替对话),
    空时不猜说话人,全部按旁白排版(诚实原则)
  - EPUB3:cover-image 声明 + nav 跳转目录 + mimetype 首位不压缩

用法:
  python3 gf2_books.py --corpus out/corpus.json --out out/books [--no-epub]
"""
import argparse
import json
import os
import re
import zipfile
from collections import defaultdict
from html import escape

PLACEHOLDER = ("占位",)


def safe_name(s):
    s = re.sub(r"[/\\:*?\"<>|\s]+", "_", s.strip())
    return s[:60] or "未命名"


def is_roster(lines):
    """名单类组:80% 以上行是 ≤6 字的短词(角色名单/道具表),不是正文。"""
    if not lines:
        return True
    short = sum(1 for l in lines if len(l["text"]) <= 6)
    return short / len(lines) >= 0.8


def group_title(lines, limit=18):
    """组名:首个有信息量的行(跳过占位与 ≤6 字寒暄"嗯。""……"),
    全短时退回最长行,不留空。"""
    def brief(t):
        return t[:limit] + "…" if len(t) > limit else t

    for l in lines:
        t = l["text"].strip()
        if t and len(t) > 6 and not any(p in t for p in PLACEHOLDER):
            return brief(t)
    if lines:
        longest = max((l["text"].strip() for l in lines), key=len, default="")
        if longest:
            return brief(longest)
    return "空"


# ---------- txt / xhtml 排版 ----------

def section_txt(title, lines):
    out = ["", "◆ %s" % title, ""]
    for l in lines:
        spk, t = l.get("speaker"), l["text"]
        line = ("「%s」%s" % (spk, t)) if spk else ("　　%s" % t)
        if l.get("option"):
            line += "　〔选项：%s〕" % l["option"]
        out.append(line)
    return "\n".join(out)


def section_xhtml(title, lines):
    parts = ['<?xml version="1.0" encoding="utf-8"?>',
             '<html xmlns="http://www.w3.org/1999/xhtml">',
             "<head><title>%s</title>" % escape(title),
             '<link rel="stylesheet" type="text/css" href="style.css"/></head><body>',
             "<h2>%s</h2>" % escape(title)]
    for l in lines:
        spk, t = l.get("speaker"), l["text"]
        opt = ('　<span class="opt">〔选项：%s〕</span>' % escape(l["option"])) if l.get("option") else ""
        if spk:
            parts.append('<p class="dlg"><span class="spk">%s:</span>%s%s</p>' % (escape(spk), escape(t), opt))
        else:
            parts.append('<p class="narr">%s%s</p>' % (escape(t), opt))
    parts.append("</body></html>")
    return "\n".join(parts)


CSS = ("body{font-family:serif;line-height:1.7;margin:5%%}"
       "h1{font-size:1.4em} h2{font-size:1.1em;margin:1.2em 0 .4em}"
       ".narr{margin:.3em 0;text-indent:2em}"
       ".dlg{margin:.3em 0} .spk{font-weight:bold}")


def write_epub(path, vol_title, sections, cover_png=None):
    """sections: [(title, xhtml_body)];cover_png: 封面图路径,None 则无封面。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml",
                   '<?xml version="1.0"?><container version="1.0" '
                   'xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
                   '<rootfiles><rootfile full-path="OEBPS/content.opf" '
                   'media-type="application/oebps-package+xml"/></rootfiles></container>')
        z.writestr("OEBPS/style.css", CSS)
        manifest, spine, nav = [], [], ['<?xml version="1.0" encoding="utf-8"?>',
                                        '<html xmlns="http://www.w3.org/1999/xhtml" '
                                        'xmlns:epub="http://www.idpf.org/2007/ops">',
                                        "<head><title>%s</title></head><body>"
                                        '<nav epub:type="toc"><h1>%s</h1><ol>' % (escape(vol_title), escape(vol_title))]
        if cover_png and os.path.exists(cover_png):
            with open(cover_png, "rb") as fh:
                z.writestr("OEBPS/cover.jpg", fh.read())
            z.writestr("OEBPS/cover.xhtml",
                       '<?xml version="1.0" encoding="utf-8"?>'
                       '<html xmlns="http://www.w3.org/1999/xhtml"><head>'
                       '<title>封面</title><style>body{margin:0;padding:0}'
                       'img{width:100%;height:auto}</style></head>'
                       '<body><img src="cover.jpg" alt="封面"/></body></html>')
            manifest.append('<item id="cover-img" href="cover.jpg" media-type="image/jpeg" '
                            'properties="cover-image"/>')
            manifest.append('<item id="coverpage" href="cover.xhtml" media-type="application/xhtml+xml"/>')
            spine.append('<itemref idref="coverpage"/>')
        for i, (title, body) in enumerate(sections, 1):
            fid = "c%04d" % i
            z.writestr("OEBPS/%s.xhtml" % fid, section_xhtml(title, body))
            manifest.append('<item id="%s" href="%s.xhtml" media-type="application/xhtml+xml"/>' % (fid, fid))
            spine.append('<itemref idref="%s"/>' % fid)
            nav.append("<li>%s</li>" % escape(title))
        nav.append("</ol></nav></body></html>")
        z.writestr("OEBPS/nav.xhtml", "\n".join(nav))
        manifest.append('<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" '
                        'properties="nav"/>')
        manifest.append('<item id="css" href="style.css" media-type="text/css"/>')
        guide = ('<guide><reference type="cover" title="封面" href="cover.xhtml"/></guide>'
                 if cover_png and os.path.exists(cover_png) else "")
        opf = ['<?xml version="1.0" encoding="utf-8"?>',
               '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" '
               'unique-identifier="bid">',
               '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">',
               '<dc:identifier id="bid">urn:uuid:gf2-%s</dc:identifier>' % safe_name(vol_title),
               "<dc:title>%s</dc:title>" % escape(vol_title),
               "<dc:language>zh-CN</dc:language>",
               '<meta name="cover" content="cover-img"/>' if cover_png and os.path.exists(cover_png) else "",
               "</metadata><manifest>%s</manifest>"
               "<spine>%s</spine>%s</package>" % ("".join(manifest), "".join(spine), guide)]
        z.writestr("OEBPS/content.opf", "\n".join(opf))


def unique_titles(secs):
    """同卷内组名去重:重复时换该组次优行,仍重复则追加 ·2/·3。"""
    seen, out = set(), []
    for title, lines in secs:
        base = title
        if title in seen:
            alt = next((l["text"].strip()[:18] for l in lines
                        if len(l["text"].strip()) > 6
                        and l["text"].strip()[:18] not in seen), None)
            if alt:
                title = alt
            else:
                n = 2
                while "%s·%d" % (base, n) in seen:
                    n += 1
                title = "%s·%d" % (base, n)
        seen.add(title)
        out.append((title, lines))
    return out


COVER_DIR = None   # main() 里初始化

FAMILY_KICKER_CN = {"lobby": "LOBBY", "adjutant": "ADJUTANT", "lounge": "LOUNGE",
                    "behavior": "INTERACTION", "darkzone": "DARK ZONE"}


def _make_cover(vol_label, kicker, title, foot):
    """按卷生成封面(缓存在 out/books/covers/);失败返回 None 不影响出书。"""
    if COVER_DIR is None:
        return None
    try:
        import gf2_cover as GC
    except Exception:
        return None
    path = os.path.join(COVER_DIR, safe_name("%s_%s" % (kicker, vol_label)) + ".jpg")
    if not os.path.exists(path):
        got = GC.make_cover(path, kicker, title, "", foot)
        if not got:
            return None
    return path if os.path.exists(path) else None


def write_volume(out_dir, vol_label, sections, epub=True, cover_spec=None):
    sections = unique_titles(sections)
    txt = ["# %s" % vol_label]
    for title, lines in sections:
        txt.append(section_txt(title, lines))
    p = os.path.join(out_dir, safe_name(vol_label) + ".txt")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("\n".join(txt))
    if epub:
        cover = None
        if cover_spec:
            cover = _make_cover(vol_label, *cover_spec)
        write_epub(os.path.join(out_dir, "epub", safe_name(vol_label) + ".epub"),
                   vol_label, [(t, l) for t, l in sections], cover_png=cover)
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="out/corpus.json")
    ap.add_argument("--out", default="out/books")
    ap.add_argument("--no-epub", action="store_true")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    global COVER_DIR
    COVER_DIR = os.path.join(args.out, "covers")
    os.makedirs(COVER_DIR, exist_ok=True)
    # 防相册扫描(limbus 踩过:封面全进相册)
    open(os.path.join(COVER_DIR, ".nomedia"), "w").close()
    c = json.load(open(args.corpus, encoding="utf-8"))
    vols = []

    # ---- 演出剧情:前缀聚类 ----
    clusters = defaultdict(list)
    for g in c["avg3d"]["groups"]:
        if is_roster(g["lines"]):
            continue
        if any(p in (g["lines"][0]["text"] if g["lines"] else "") for p in PLACEHOLDER):
            continue
        clusters[str(g["group"])[:3]].append(g)
    for prefix, gs in sorted(clusters.items(), key=lambda x: int(x[0])):
        secs = [(group_title(g["lines"]), g["lines"]) for g in gs]
        label = "演出剧情 %s(组%s-%d)" % (prefix, prefix, len(gs))
        vols.append(write_volume(args.out, label, secs, not args.no_epub,
                                 cover_spec=("MAIN STORY", "演出剧情", "组 %s · %d 节" % (prefix, len(gs)))))

    # ---- 宿舍对话:按角色(头像) ----
    by_avatar = defaultdict(list)
    for g in c["dialogue"]["groups"]:
        av = next((l["avatar"] for l in g["lines"] if l.get("avatar")), "")
        if any(p in l["text"] for l in g["lines"][:1] for p in PLACEHOLDER):
            continue
        by_avatar[av or "未知"].append(g)
    for av, gs in sorted(by_avatar.items()):
        name = re.sub(r"^Avatar_Head_|SR\d+$|SSR\d+$", "", av) if av != "未知" else "未知"
        secs = [(group_title(g["lines"]), g["lines"]) for g in gs]
        vols.append(write_volume(args.out, "宿舍对话 %s(%d 组)" % (name, len(gs)), secs, not args.no_epub,
                                 cover_spec=("DORMITORY", name, "%s · %d 节" % (name, len(gs)))))

    # ---- 公会战 ----
    by_ch = defaultdict(list)
    for s in c["guildwar"]["stories"]:
        by_ch[s["chapter_seq"] or 0].append(s)
    for ch, ss in sorted(by_ch.items()):
        secs = [(s["title"] or ("篇 %d" % s["id"]), s["lines"]) for s in ss]
        vols.append(write_volume(args.out, "公会战剧情 第%d期(%d 篇)" % (ch, len(ss)), secs, not args.no_epub,
                                 cover_spec=("GUILD WAR", "第 %d 期" % ch, "%d 篇 · 多分支" % len(ss))))

    # ---- 信件/报道/日志(T6):每封一节 ----
    emails = c.get("email", [])
    if emails:
        secs = []
        for e in emails:
            first = e["paras"][0]
            title = (first[:18] + "…") if len(first) > 18 else first
            secs.append((title, [{"speaker": None, "text": p} for p in e["paras"]]))
        vols.append(write_volume(args.out, "信件与报道(%d 篇)" % len(secs), secs,
                                 not args.no_epub,
                                 cover_spec=("ARCHIVE", "信件与报道", "%d 篇 · 长文档案" % len(secs))))

    # ---- 支线家族(T1):每族一卷,按角色分节 ----
    FAM_LABEL = {"lobby": "大厅闲聊", "adjutant": "副官对话", "lounge": "休息室对话",
                 "behavior": "互动对话", "darkzone": "暗区对话"}
    for fam, gs in c.get("simple", {}).items():
        if not gs:
            continue
        secs = [(g["group"], g["lines"]) for g in gs]
        cname = FAM_LABEL.get(fam, fam)
        label = "%s(%d 节)" % (cname, len(secs))
        vols.append(write_volume(args.out, label, secs, not args.no_epub,
                                 cover_spec=(FAMILY_KICKER_CN.get(fam, "STORY"), cname, "%d 节" % len(secs))))

    print("成卷 %d,输出目录 %s" % (len(vols), args.out))


if __name__ == "__main__":
    main()
