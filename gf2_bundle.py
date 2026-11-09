#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GF2 AssetBundle 解包:解密(XOR,密钥来自 nijinekoyo/GF2AssetBundleDecryption 公开源码)
+ UnityPy 列出内容 / 导出 TextAsset。

算法(与 Go 源码一致):
  1) FileKey = FileData[0:16] XOR Key(Key = "UnityFS\\0\\0\\0\\0\\x075.x." 的字节)
  2) FileData[0:0x8000] 逐字节 XOR FileKey[i % 16]

用法:
  python3 gf2_bundle.py --probe <bundle...>          # 解出对象清单/TextAsset 预览
  python3 gf2_bundle.py --extract <bundle> --out dir # 导出全部 TextAsset 到 dir
"""
import argparse
import os
import sys

KEY = bytes([0x55, 0x6E, 0x69, 0x74, 0x79, 0x46, 0x53, 0x00,
             0x00, 0x00, 0x00, 0x07, 0x35, 0x2E, 0x78, 0x2E])


def decrypt(blob):
    """把加密 bundle 还原成明文;已是明文(以 UnityFS 开头)则原样返回。"""
    if blob[:8].startswith(b"UnityFS") or blob[:7].startswith(b"UnityWeb"):
        return blob
    if len(blob) < 16 + 0x8000:
        raise ValueError("文件太小,不像 bundle: %d bytes" % len(blob))
    file_key = bytes(blob[i] ^ KEY[i] for i in range(16))
    head = bytearray(blob)
    n = min(0x8000 * 1, len(head))   # Go 源码:min(0x1000*8, len)
    fb = bytearray(blob[:n])
    for i in range(n):
        fb[i] ^= file_key[i % 16]
    head[:n] = fb
    if not bytes(head[:8]).startswith(b"UnityFS"):
        raise ValueError("解密后仍非 UnityFS,头=%r" % bytes(head[:16]))
    return bytes(head)


def load_env(path):
    import UnityPy
    with open(path, "rb") as fh:
        blob = fh.read()
    plain = decrypt(blob)
    return UnityPy.load(plain)


def probe(paths):
    for p in paths:
        print("══ %s (%d KB)" % (os.path.basename(p), os.path.getsize(p) // 1024))
        try:
            env = load_env(p)
        except Exception as e:
            print("   解包失败: %s: %s" % (type(e).__name__, e))
            continue
        kinds = {}
        text_assets = []
        for obj in env.objects:
            kinds[obj.type.name] = kinds.get(obj.type.name, 0) + 1
            if obj.type.name == "TextAsset":
                try:
                    d = obj.read()
                    text_assets.append((getattr(d, "m_Name", "?"), d.m_Script))
                except Exception:
                    pass
        print("   对象: %s" % kinds)
        for name, script in text_assets[:5]:
            body = script if isinstance(script, str) else str(script)
            print("   TextAsset %-40s %d 字: %r" % (name, len(body), body[:120]))


def extract(path, out):
    os.makedirs(out, exist_ok=True)
    env = load_env(path)
    n = 0
    for obj in env.objects:
        if obj.type.name == "TextAsset":
            d = obj.read()
            name = getattr(d, "m_Name", "asset_%d" % n)
            script = d.m_Script
            body = script if isinstance(script, str) else str(script)
            safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in name)[:80]
            with open(os.path.join(out, safe + ".txt"), "w", encoding="utf-8") as fh:
                fh.write(body)
            n += 1
    print("导出 TextAsset %d 个 -> %s" % (n, out))


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--probe", nargs="+")
    g.add_argument("--extract")
    ap.add_argument("--out", default="out/bundle_text")
    args = ap.parse_args()
    if args.probe:
        probe(args.probe)
    else:
        extract(args.extract, args.out)


if __name__ == "__main__":
    main()
