#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gf2-story-tool 单元测试。不依赖游戏数据，纯构造样例。
覆盖:protobuf wire 解码、长度头跳过、说话人抽取、名单判别、EPUB 封装。
跑法:python3 tests/test_gf2.py
"""
import os
import sys
import zipfile
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gf2_table import parse_fields, read_varint  # noqa: E402
from gf2_extract import clean_text, unpack_packed, lang_ref  # noqa: E402
from gf2_books import (  # noqa: E402
    safe_name, is_roster, group_title, section_txt, section_xhtml, write_epub,
)

FAIL = []


def check(name, cond, detail=""):
    if cond:
        print("  ok   %s" % name)
    else:
        print("  FAIL %s  %s" % (name, detail))
        FAIL.append(name)


# ---------- protobuf 构造工具 ----------

def enc_varint(v):
    out = bytearray()
    while True:
        b = v & 0x7F
        v >>= 7
        if v:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def tag(fno, wt):
    return enc_varint((fno << 3) | wt)


def enc_ld(fno, payload):
    return tag(fno, 2) + enc_varint(len(payload)) + payload


def enc_int(fno, v):
    return tag(fno, 0) + enc_varint(v)


# ---------- 测试 ----------

def test_varint():
    check("0 编码", enc_varint(0) == b"\x00")
    check("127 单字节", enc_varint(127) == b"\x7f")
    check("128 两字节", enc_varint(128) == b"\x80\x01")
    v, i = read_varint(b"\x80\x01\xff", 0)
    check("解码 128", v == 128 and i == 2, (v, i))
    check("多字节大数", read_varint(enc_varint(300000), 0)[0] == 300000)


def test_parse_fields_ld():
    body = enc_ld(2, b"hello") + enc_int(1, 42)
    fs = list(parse_fields(body))
    check("两个字段", len(fs) == 2, fs)
    check("字段2是bytes", fs[0][:2] == (2, 2) and fs[0][2] == b"hello", fs[0])
    check("字段1是int", fs[1][:2] == (1, 0) and fs[1][2] == 42, fs[1])


def test_parse_nested():
    """LangPackage 形态: f1{ f1=id, f2="文本" }"""
    inner = enc_int(1, 169402) + enc_ld(2, "你就不能温柔一点吗！".encode())
    body = enc_ld(1, inner)
    (f, w, v), = parse_fields(body)
    fields = {a: c for a, b, c in parse_fields(v)}
    check("嵌套 id", fields[1] == 169402, fields)
    check("嵌套文本", fields[2].decode() == "你就不能温柔一点吗！", fields)


def test_unpack_packed():
    packed = enc_varint(1000301) + enc_varint(1000302) + enc_varint(1000303)
    check("packed 解出 3 个", unpack_packed(packed) == [1000301, 1000302, 1000303])
    check("空 packed", unpack_packed(b"") == [])
    check("坏 packed 返回 None", unpack_packed(b"\x80") is None)


def test_lang_ref():
    check("msg{f1:id} 取 id", lang_ref(enc_int(1, 12543)) == 12543)
    check("非 bytes 返回 None", lang_ref(42) is None)


def test_clean_text_tag_speaker():
    spk, txt = clean_text('<color=#f6de73>闪电：</color>指挥官，同调已经完成。')
    check("标签说话人", spk == "闪电", spk)
    check("标签剥离", txt == "指挥官，同调已经完成。", txt)


def test_clean_text_plain_speaker():
    spk, txt = clean_text("闪电:指挥官，你去哪里了？")
    check("半角冒号说话人", spk == "闪电", spk)
    check("正文不含冒号前缀", txt.startswith("指挥官"), txt)
    spk2, _ = clean_text("可露凯：这样也可以吗？")
    check("全角冒号说话人", spk2 == "可露凯", spk2)


def test_clean_text_no_speaker():
    spk, txt = clean_text("（可露凯的手因为用力而颤抖。）")
    check("旁白无说话人", spk is None, spk)
    check("旁白保留", txt.startswith("（可露凯"), txt)
    spk2, txt2 = clean_text("指挥官，这是我为你做的料理。")
    check("长句不误判说话人", spk2 is None, spk2)
    spk3, txt3 = clean_text("")
    check("空串安全", spk3 is None and txt3 == "")


def test_clean_text_nested_tags():
    spk, txt = clean_text("<b>【提示】</b><size=22>新装采购限时开启</size>")
    check("b/size 剥离", txt == "【提示】新装采购限时开启", txt)
    spk2, txt2 = clean_text("{}：动态名？")
    check("{} 保留为正文", txt2.startswith("{}"), txt2)


def test_is_roster():
    roster = [{"text": n} for n in ["闪电", "克罗丽科", "纳美西丝", "寇尔芙", "莱娜"]]
    check("角色名单判 roster", is_roster(roster))
    prose = [{"text": "指挥官，你去哪里了？"}, {"text": "身上都淋湿了，来，让我帮你擦干。"},
             {"text": "现在怎么样？是不是温暖一些了？"}]
    check("正文不判 roster", not is_roster(prose))
    check("空组判 roster", is_roster([]))


def test_group_title():
    lines = [{"text": "嗯。"}, {"text": "……"}, {"text": "指挥官，同调已经完成，今夜，让我的声音成为你的防线。"}]
    t = group_title(lines)
    check("跳过寒暄取正文", t.startswith("指挥官，同调已经完成"), t)
    check("超长截断", len(group_title([{"text": "长" * 50}])) <= 19)


def test_safe_name():
    check("去斜杠", "/" not in safe_name("演出剧情 100(组100-293)"))
    check("空串兜底", safe_name("   ") == "未命名")
    check("截断 60", len(safe_name("长" * 100)) <= 60)


def test_section_txt():
    lines = [{"speaker": "闪电", "text": "指挥官，你去哪里了？"},
             {"speaker": None, "text": "（雨声渐渐小了。）"}]
    txt = section_txt("测试组", lines)
    check("说话人用「」", "「闪电」指挥官" in txt, txt)
    check("旁白缩进两格", "　　（雨声渐渐小了。）" in txt, repr(txt[-40:]))
    check("组标题在", "◆ 测试组" in txt)


def test_epub_structure():
    secs = [("第一组", [{"speaker": None, "text": "甲。"}]),
            ("第二组", [{"speaker": "闪电", "text": "乙。"}])]
    d = tempfile.mkdtemp()
    p = os.path.join(d, "t.epub")
    write_epub(p, "测试卷", secs)
    z = zipfile.ZipFile(p)
    names = z.namelist()
    check("mimetype 第一个", names[0] == "mimetype", names[0])
    check("mimetype 不压缩", z.getinfo("mimetype").compress_type == 0)
    check("mimetype 内容", z.read("mimetype") == b"application/epub+zip")
    check("zip 完整", z.testzip() is None)
    check("container.xml", "META-INF/container.xml" in names)
    check("opf", "OEBPS/content.opf" in names)
    check("nav", "OEBPS/nav.xhtml" in names)
    check("两章正文", len([n for n in names if n.startswith("OEBPS/c0") and n.endswith(".xhtml")]) == 2, names)
    opf = z.read("OEBPS/content.opf").decode()
    check("EPUB3", 'version="3.0"' in opf)
    nav = z.read("OEBPS/nav.xhtml").decode()
    check("nav 两项", nav.count("<li>") == 2, nav.count("<li>"))
    z.close()


def test_xhtml_escape():
    body = section_xhtml("A&B<C>", [{"speaker": None, "text": "x<y & z"}])
    check("标题转义", "A&amp;B&lt;C&gt;" in body, body[:120])
    check("正文转义", "x&lt;y &amp; z" in body)


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    print("running %d tests" % len(tests))
    for fn in tests:
        print("\n== %s" % fn.__name__)
        try:
            fn()
        except Exception as e:
            check("%s raised" % fn.__name__, False, "%s: %s" % (type(e).__name__, e))
    print("\n%d checks failed" % len(FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
