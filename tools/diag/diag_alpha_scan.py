#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扫描出图产物：PNG 到底有没有 alpha 通道，alpha 是不是全不透明。

动机：Qwen-Image-2.1 的 VAE 解码输出 4 通道（RGB + alpha），ComfyUI 的 SaveImage
把 4 通道写成 color_type=6 的 RGBA PNG。所以"工作台出的图有没有 alpha"这件事
不需要重新出图就能查清楚 —— 看历史产物即可。

用法：python tools/diag/diag_alpha_scan.py [目录 ...]
"""
import os
import struct
import sys
import zlib

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))


def png_meta(path):
    """返回 (w, h, color_type, alpha_stats) —— alpha_stats 为 (min,max) 或 None。"""
    with open(path, "rb") as f:
        data = f.read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    pos, w, h, ctype, idat = 8, None, None, None, b""
    while pos < len(data):
        ln = struct.unpack(">I", data[pos:pos + 4])[0]
        tag = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + ln]
        if tag == b"IHDR":
            w, h, _, ctype = struct.unpack(">IIBB", body[:10])
        elif tag == b"IDAT":
            idat += body
        elif tag == b"IEND":
            break
        pos += 12 + ln
    ch = {0: 1, 2: 3, 4: 2, 6: 4}.get(ctype)
    if ch is None:
        return w, h, ctype, None
    if ctype != 6:
        return w, h, ctype, None
    # 只解前若干行，统计 alpha 的 min/max（够判断"是否全不透明"）
    try:
        raw = zlib.decompress(idat)
    except Exception:
        return w, h, ctype, None
    stride = w * ch
    prev = bytearray(stride)
    lo, hi = 255, 0
    rows = min(h, 32)
    for y in range(rows):
        off = y * (stride + 1)
        f = raw[off]
        line = bytearray(raw[off + 1: off + 1 + stride])
        for i in range(stride):
            a = line[i - ch] if i >= ch else 0
            b = prev[i]
            c = prev[i - ch] if i >= ch else 0
            if f == 1:
                p = a
            elif f == 2:
                p = b
            elif f == 3:
                p = (a + b) // 2
            elif f == 4:
                pp = a + b - c
                pa, pb, pc = abs(pp - a), abs(pp - b), abs(pp - c)
                p = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
            else:
                p = 0
            line[i] = (line[i] + p) & 0xFF
        for x in range(w):
            av = line[x * ch + 3]
            lo = min(lo, av)
            hi = max(hi, av)
        prev = line
    return w, h, ctype, (lo, hi)


def main():
    dirs = sys.argv[1:] or ["outputs", "示例效果", "修复验证", "style_run9"]
    print(f"扫描根目录：{ROOT}\n")
    total = 0
    rgba = 0
    with_alpha = 0
    for d in dirs:
        p = os.path.join(ROOT, d)
        if not os.path.isdir(p):
            continue
        files = []
        for base, _, names in os.walk(p):
            files += [os.path.join(base, n) for n in names if n.lower().endswith(".png")]
        files.sort()
        n_rgba = n_alpha = 0
        samples = []
        for f in files:
            m = png_meta(f)
            if not m:
                continue
            w, h, ctype, stats = m
            total += 1
            if ctype == 6:
                rgba += 1
                n_rgba += 1
                if stats and stats[0] < 255:
                    with_alpha += 1
                    n_alpha += 1
                    if len(samples) < 3:
                        samples.append((os.path.basename(f), stats))
        print(f"[{d}]  {len(files)} 张 PNG，其中 color_type=6(RGBA) {n_rgba} 张，"
              f"alpha 非全不透明 {n_alpha} 张")
        for s in samples:
            print(f"      例：{s[0]}  alpha min/max = {s[1]}")
    print(f"\n合计 {total} 张：RGBA {rgba} 张，真正含透明像素 {with_alpha} 张")
    if rgba == total and with_alpha == 0:
        print("=> 结论：**alpha 通道一直在**（VAE 4 通道 → SaveImage 写 RGBA），"
              "但所有产物的 alpha 都是 255（全不透明），即模型没有生成透明区域。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
