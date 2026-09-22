#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""比对两张 PNG 的差异，并按"掩码内 / 掩码外"分开统计。

用途：验证潜空间掩码重绘是否做到"圈外像素级不变"。

用法：python tools/diag/cmp_region_diff.py <原图> <新图> [--box x0,y0,x1,y1]
     --box 指定"应该变化"的区域；不给出则只做整体差异。
"""
import os
import struct
import sys
import zlib

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def read_rgb(path):
    d = open(path, "rb").read()
    pos, w, h, ct, idat = 8, None, None, None, b""
    while pos + 12 <= len(d):
        ln = struct.unpack(">I", d[pos:pos + 4])[0]
        tag = d[pos + 4:pos + 8]
        body = d[pos + 8:pos + 8 + ln]
        if tag == b"IHDR":
            w, h, _, ct = struct.unpack(">IIBB", body[:10])
        elif tag == b"IDAT":
            idat += body
        elif tag == b"IEND":
            break
        pos += 12 + ln
    ch = {0: 1, 2: 3, 4: 2, 6: 4}[ct]
    raw = zlib.decompress(idat)
    stride = w * ch
    prev = bytearray(stride)
    rows = []
    for y in range(h):
        off = y * (stride + 1)
        f = raw[off]
        line = bytearray(raw[off + 1: off + 1 + stride])
        for i in range(stride):
            a = line[i - ch] if i >= ch else 0
            b = prev[i]
            c = prev[i - ch] if i >= ch else 0
            if f == 1:
                pr = a
            elif f == 2:
                pr = b
            elif f == 3:
                pr = (a + b) // 2
            elif f == 4:
                pp = a + b - c
                pa, pb, pc = abs(pp - a), abs(pp - b), abs(pp - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
            else:
                pr = 0
            line[i] = (line[i] + pr) & 0xFF
        rows.append(line)
        prev = line
    return w, h, ch, rows


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2:
        print(__doc__)
        return 1
    box = None
    for a in sys.argv[1:]:
        if a.startswith("--box="):
            box = tuple(int(v) for v in a.split("=", 1)[1].split(","))
    wa, ha, ca, A = read_rgb(args[0])
    wb, hb, cb, B = read_rgb(args[1])
    if (wa, ha) != (wb, hb):
        print(f"尺寸不同：{wa}x{ha} vs {wb}x{hb}")
        return 1
    print(f"A = {os.path.basename(args[0])}  {wa}x{ha} ch={ca}")
    print(f"B = {os.path.basename(args[1])}  {wb}x{hb} ch={cb}")
    if box:
        print(f"掩码白区（应当变化）= {box}")

    stats = {"in": [0, 0], "out": [0, 0]}     # [差异点数, 总数]
    maxdiff_in = maxdiff_out = 0
    for y in range(ha):
        ra, rb = A[y], B[y]
        for x in range(wa):
            dmax = 0
            for k in range(3):
                va = ra[x * ca + k]
                vb = rb[x * cb + k]
                dmax = max(dmax, abs(va - vb))
            region = "out"
            if box and (box[0] <= x < box[2] and box[1] <= y < box[3]):
                region = "in"
            stats[region][1] += 1
            if dmax > 8:                      # 阈值 8，避开压缩噪声
                stats[region][0] += 1
                if region == "in":
                    maxdiff_in = max(maxdiff_in, dmax)
                else:
                    maxdiff_out = max(maxdiff_out, dmax)

    for k, label in (("in", "掩码白区"), ("out", "掩码外")):
        n, tot = stats[k]
        if tot:
            print(f"  {label}: 差异点 {n}/{tot} = {n / tot * 100:.3f}%（最大通道差 {maxdiff_in if k == 'in' else maxdiff_out}）")
    if box and stats["out"][1]:
        ratio = stats["out"][0] / stats["out"][1]
        if ratio < 0.005:
            print("=> ✅ 掩码外基本逐点不变（真正的局部重绘）")
        else:
            print("=> ⚠️ 掩码外也被改动，说明是整图重绘而非像素级局部重绘")
    return 0


if __name__ == "__main__":
    sys.exit(main())
