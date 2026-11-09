#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GF2 Table .bytes 解析器(手机端)。

格式(由 nijinekoyo/GF2AssetBundleDecryption 的 Go 源码确认):
  [4 字节小端 uint32 skip][skip 字节未知头][protobuf 消息体]

LangPackageTable 系列的 proto 结构已知:
  TextMapTable { Data: repeated TextMap }
  TextMap      { Id: int64 (field 1), Content: string (field 2) }

其他表没有公开 schema,用通用 wire-format 解码做黑盒探测。

用法:
  python3 gf2_table.py lang  <Table目录>          # 解全部语言包 -> JSONL
  python3 gf2_table.py probe <Table目录> <表名>   # 黑盒解析任意表,打印结构
"""
import json
import os
import struct
import sys


def read_table(table_dir, name):
    p = os.path.join(table_dir, name)
    with open(p, "rb") as fh:
        blob = fh.read()
    skip = struct.unpack_from("<I", blob, 0)[0]
    body = blob[skip + 4:]
    return body


# ---------- protobuf wire format ----------

def read_varint(buf, i):
    v = 0
    shift = 0
    while True:
        b = buf[i]
        i += 1
        v |= (b & 0x7F) << shift
        if not b & 0x80:
            return v, i
        shift += 7


def parse_fields(buf):
    """通用解码:yield (field_no, wire_type, value)。value: int / bytes / (start,end) for group"""
    i, n = 0, len(buf)
    while i < n:
        try:
            key, i = read_varint(buf, i)
        except IndexError:
            break
        fno, wt = key >> 3, key & 7
        if wt == 0:  # varint
            v, i = read_varint(buf, i)
            yield fno, wt, v
        elif wt == 2:  # length-delimited
            ln, i = read_varint(buf, i)
            yield fno, wt, buf[i:i + ln]
            i += ln
        elif wt == 5:  # 32-bit
            yield fno, wt, struct.unpack_from("<I", buf, i)[0]
            i += 4
        elif wt == 1:  # 64-bit
            yield fno, wt, struct.unpack_from("<Q", buf, i)[0]
            i += 8
        else:  # 3/4 group(已废弃):无法继续,终止
            break


def decode_lang(body):
    """TextMapTable -> list of {id, content}"""
    out = []
    for fno, wt, val in parse_fields(body):
        if fno == 1 and wt == 2:  # Data
            rec = {"id": None, "content": ""}
            for f2, w2, v2 in parse_fields(val):
                if f2 == 1:
                    rec["id"] = v2
                elif f2 == 2:
                    rec["content"] = v2.decode("utf-8", "replace")
            out.append(rec)
    return out


def heuristic(val):
    """对 length-delimited 字段猜类型:合法 utf-8 文本 / 嵌套消息 / 其他"""
    try:
        s = val.decode("utf-8")
        if s and all(31 < ord(c) or c in "\t\n\r" for c in s):
            return ("str", s)
    except UnicodeDecodeError:
        pass
    # 试嵌套消息:能否完整解析且字段号 <= 32
    try:
        fs = list(parse_fields(val))
        if fs and sum(1 for _ in parse_fields(val)) == len(fs) and all(0 < f <= 32 for f, _, _ in fs):
            return ("msg", [(f, w, (heuristic(v) if w == 2 else v)) for f, w, v in fs])
    except Exception:
        pass
    return ("bytes", val.hex()[:24])


def cmd_lang(table_dir, out_path):
    rows = []
    for name in ("LangPackageTableCnBuiltinData.bytes", "LangPackageTableCnData.bytes"):
        body = read_table(table_dir, name)
        part = decode_lang(body)
        print("%-36s %8d 条" % (name, len(part)))
        rows.extend(part)
    with open(out_path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("合计 %d 条 -> %s" % (len(rows), out_path))
    lens = sorted(len(r["content"]) for r in rows)
    if lens:
        print("content 长度: min=%d 中位=%d p95=%d max=%d" % (
            lens[0], lens[len(lens) // 2], lens[int(len(lens) * .95)], lens[-1]))


def cmd_probe(table_dir, name, limit=3):
    body = read_table(table_dir, name)
    print("%s: body %d bytes" % (name, len(body)))
    for fno, wt, val in parse_fields(body):
        if wt == 2:
            kind, v = heuristic(val)
            if kind == "msg":
                flat = json.dumps(v, ensure_ascii=False, default=str)
                print("  f%-2d msg(%dB): %s" % (fno, len(val), flat[:300]))
            else:
                print("  f%-2d %s(%dB): %r" % (fno, kind, len(val), str(v)[:200]))
        else:
            print("  f%-2d wt%d = %s" % (fno, wt, val))
        limit -= 1
        if limit <= 0:
            print("  ...(只列前 3 条)")
            break


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    cmd, table_dir = sys.argv[1], sys.argv[2]
    if cmd == "lang":
        out = sys.argv[3] if len(sys.argv) > 3 else os.path.join(os.path.dirname(table_dir), "lang_cn.jsonl")
        cmd_lang(table_dir, out)
    elif cmd == "probe":
        cmd_probe(table_dir, sys.argv[3] if len(sys.argv) > 3 else "StoryData.bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
