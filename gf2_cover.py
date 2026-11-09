#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GF2 封面生成:军械风(暗底 + 黄铜 + 军绿点缀 + 瞄准环)。
链路同 limbus-story-tool:SVG → rsvg-convert → magick JPEG q88。

用法:
  python3 gf2_cover.py --out docs/cover-samples     # 出 3 张样图
"""
import argparse
import os
import random
import shutil
import subprocess
from xml.sax.saxutils import escape as esc

COVER_W, COVER_H = 1200, 1800
BG = "#121009"          # 近黑褐
BRASS = "#b08d4f"       # 黄铜
BRASS_DIM = "#7a6136"
OLIVE = "#5a6540"       # 军绿
PAPER = "#e8e2d0"
ROMAN = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI", 7: "VII", 8: "VIII"}

FAMILY_KICKER = {
    "演出剧情": "MAIN STORY",
    "宿舍对话": "DORMITORY",
    "公会战剧情": "GUILD WAR",
    "大厅闲聊": "LOBBY",
    "副官对话": "ADJUTANT",
    "休息室对话": "LOUNGE",
    "互动对话": "INTERACTION",
    "暗区对话": "DARK ZONE",
}


def _text_width(s, size):
    return sum(size * (1.0 if ord(ch) > 0x2E80 else 0.56) for ch in s)


def _fit(s, size, max_w, spacing=0):
    while size > 30 and (_text_width(s, size) + spacing * max(0, len(s) - 1)) > max_w:
        size -= 4
    return size


def _grain(n=2600, seed=11):
    rnd = random.Random(seed)
    out = []
    for _ in range(n):
        out.append('<circle cx="%.0f" cy="%.0f" r="%.1f" fill="#fff" opacity="%.2f"/>'
                   % (rnd.uniform(0, COVER_W), rnd.uniform(0, COVER_H),
                      rnd.choice([0.6, 0.9]), rnd.uniform(0.02, 0.08)))
    return "".join(out)


def _reticle(cx, cy, r):
    """瞄准环:双圆 + 四向刻线,军械风核心装饰。"""
    return (
        '<circle cx="%d" cy="%d" r="%d" fill="none" stroke="%s" stroke-width="1.5" opacity="0.75"/>'
        '<circle cx="%d" cy="%d" r="%d" fill="none" stroke="%s" stroke-width="3" opacity="0.35"/>'
        '<path d="M%d %d h%d M%d %d h%d M%d %d v%d M%d %d v%d" stroke="%s" stroke-width="1.5" opacity="0.75"/>'
        % (cx, cy, r, BRASS, cx, cy, r - 10, BRASS,
           cx - r, cy, 18, cx + r - 18, cy, 18, cx, cy - r, 18, cx, cy + r - 18, 18, BRASS))


def _corner(x, y, sx, sy):
    return ('<path d="M%d %d h%d M%d %d v%d" stroke="%s" stroke-width="2.5" fill="none"/>'
            % (x, y, sx * 46, x, y, sy * 46, BRASS))


def cover_svg(kicker, title, sub, foot1, foot2):
    size = _fit(title, 150, COVER_W - 260)
    if len(title) > 10:
        size = _fit(title, 92, COVER_W - 260)
    k_size = _fit(kicker, 84, COVER_W - 320, spacing=14)
    sub_size = _fit(sub, 28, COVER_W - 320, spacing=8) if sub else 28
    cx = COVER_W // 2
    inner = 84
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">'
        % (COVER_W, COVER_H, COVER_W, COVER_H),
        '<defs><radialGradient id="vig" cx="0.5" cy="0.42" r="0.8">'
        '<stop offset="0.5" stop-color="#000" stop-opacity="0"/>'
        '<stop offset="1" stop-color="#000" stop-opacity="0.88"/></radialGradient>'
        '<linearGradient id="spine" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="%s" stop-opacity="0.10"/>'
        '<stop offset="0.5" stop-color="%s" stop-opacity="0.28"/>'
        '<stop offset="1" stop-color="%s" stop-opacity="0.06"/></linearGradient></defs>'
        % (OLIVE, BRASS_DIM, OLIVE),
        '<rect width="%d" height="%d" fill="%s"/>' % (COVER_W, COVER_H, BG),
        _grain(),
        '<rect width="%d" height="%d" fill="url(#vig)"/>' % (COVER_W, COVER_H),
        # 左侧书脊条
        '<rect x="0" y="0" width="54" height="%d" fill="url(#spine)"/>' % COVER_H,
        '<path d="M54 0 v%d" stroke="%s" stroke-width="1.2" opacity="0.5"/>' % (COVER_H, BRASS),
        # 双线内框
        '<rect x="%d" y="%d" width="%d" height="%d" fill="none" stroke="%s" stroke-width="2.5"/>'
        % (inner, inner, COVER_W - 2 * inner, COVER_H - 2 * inner, BRASS),
        '<rect x="%d" y="%d" width="%d" height="%d" fill="none" stroke="%s" stroke-width="1" '
        'opacity="0.5"/>' % (inner + 12, inner + 12, COVER_W - 2 * inner - 24,
                             COVER_H - 2 * inner - 24, BRASS),
        _corner(inner + 2, inner + 2, 1, 1),
        _corner(COVER_W - inner - 2, inner + 2, -1, 1),
        _corner(inner + 2, COVER_H - inner - 2, 1, -1),
        _corner(COVER_W - inner - 2, COVER_H - inner - 2, -1, -1),
        # 顶部品牌行
        '<text x="%d" y="252" text-anchor="middle" font-family="Noto Serif CJK SC, serif" '
        'font-size="24" letter-spacing="6" fill="%s" opacity="0.9">'
        'GIRLS FRONTLINE 2  : EXILIUM</text>' % (cx, PAPER),
        '<text x="%d" y="292" text-anchor="middle" font-family="Noto Serif CJK SC, serif" '
        'font-size="20" letter-spacing="12" fill="%s" opacity="0.75">少女前线 2 · 追放</text>'
        % (cx, BRASS),
        # 瞄准环(置于 kicker 上方,不与文字重叠)
        _reticle(cx, 560, 104),
        '<text x="%d" y="772" text-anchor="middle" font-family="Noto Serif CJK SC, serif" '
        'font-size="%d" letter-spacing="14" fill="%s">%s</text>'
        % (cx, k_size, PAPER, esc(kicker)),
        '<path d="M%d 822 h200 M%d 822 h200" stroke="%s" stroke-width="1.5" opacity="0.85"/>'
        % (cx - 290, cx + 90, BRASS),
        '<path d="M%d 810 l12 12 l-12 12 l-12 -12 z" fill="%s"/>' % (cx, BRASS),
        '<text x="%d" y="%d" text-anchor="middle" font-family="Noto Serif CJK SC, serif" '
        'font-size="%d" fill="%s">%s</text>'
        % (cx, 962 + size * 0.15, size, PAPER, esc(title)),
    ]
    if sub:
        parts.append('<text x="%d" y="%d" text-anchor="middle" font-family="Noto Serif CJK SC, serif" '
                     'font-size="%d" letter-spacing="8" fill="%s" opacity="0.8">%s</text>'
                     % (cx, 1024 + size * 0.15, sub_size, BRASS, esc(sub.upper())))
    parts += [
        '<text x="%d" y="%d" text-anchor="middle" font-family="Noto Serif CJK SC, serif" '
        'font-size="26" letter-spacing="4" fill="%s" opacity="0.65">%s</text>'
        % (cx, COVER_H - 190, BRASS, esc(foot1)),
        '<text x="%d" y="%d" text-anchor="middle" font-family="Noto Serif CJK SC, serif" '
        'font-size="18" letter-spacing="6" fill="%s" opacity="0.4">%s</text>'
        % (cx, COVER_H - 148, BRASS, esc(foot2)),
        '</svg>',
    ]
    return "\n".join(parts)


def make_cover(path, kicker, title, sub, foot1, foot2="EXILIUM · STORY ARCHIVE · COMMUNITY DATA"):
    exe = shutil.which("rsvg-convert")
    if not exe:
        return None
    svg = cover_svg(kicker, title, sub, foot1, foot2)
    try:
        subprocess.run([exe, "-w", str(COVER_W), "-h", str(COVER_H), "-o", path],
                       input=svg.encode("utf-8"), check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        return None
    jpg = os.path.splitext(path)[0] + ".jpg"
    magick = shutil.which("magick")
    if magick and os.path.exists(path):
        try:
            subprocess.run([magick, path, "-quality", "88", jpg], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return jpg
        except Exception:
            return path
    return path if os.path.exists(path) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/cover-samples")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    # 三张样图对应三类主要卷
    cases = [
        ("演出剧情", "MAIN STORY", "演出剧情", "组 100 · 293 节", "EXILIUM · STORY ARCHIVE"),
        ("宿舍对话", "DORMITORY", "闪电", "闪电 · 22 节", "EXILIUM · DORMITORY TALK"),
        ("公会战剧情", "GUILD WAR", "武装同盟", "第 1 期 · 42 篇", "EXILIUM · GUILD WAR"),
    ]
    for name, kicker, title, foot1, foot2 in cases:
        p = make_cover(os.path.join(args.out, "sample_%s.jpg" % name),
                       kicker, title, "", foot1, foot2)
        print("%-10s -> %s" % (name, p))
    # 生成 .nomedia 防相册扫描(与 limbus 相同教训)
    open(os.path.join(args.out, ".nomedia"), "w").close()


if __name__ == "__main__":
    main()
