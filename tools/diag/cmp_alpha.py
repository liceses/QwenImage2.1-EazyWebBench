#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""逐像素比较两张 PNG 的 alpha（用于判定"取反"假设）。

用法：python tools/diag/cmp_alpha.py <图A> <图B> [每N列采样]
"""
import os
import struct
import sys
import zlib

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = r"D:\applications\comfy-ui\ComfyUI_windows_portable\ComfyUI\output"


def load_alpha(path, rows=None, step=64):
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
    grid = []
    limit = min(h, rows or h)
    for y in range(limit):
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
        grid.append([line[x * ch + (ch - 1)] for x in range(0, w, step)])
        prev = line
    return w, h, ct, grid


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    pa = sys.argv[1] if os.path.isabs(sys.argv[1]) else os.path.join(OUT, sys.argv[1])
    pb = sys.argv[2] if os.path.isabs(sys.argv[2]) else os.path.join(OUT, sys.argv[2])
    step = int(sys.argv[3]) if len(sys.argv) > 3 else 64
    rows = int(sys.argv[4]) if len(sys.argv) > 4 else 200
    wa, ha, ca, ga = load_alpha(pa, rows=rows, step=step)
    wb, hb, cb, gb = load_alpha(pb, rows=rows, step=step)
    print(f"A = {os.path.basename(pa)}  {wa}x{ha} ct={ca}")
    print(f"B = {os.path.basename(pb)}  {wb}x{hb} ct={cb}\n")
    shown = [0, 50, 100, 200, 400, 600, 800]
    for i in shown:
        if i < len(ga) and i < len(gb):
            print(f"  row{i:>4} A: " + " ".join(f"{v:>3}" for v in ga[i]))
            print(f"  row{i:>4} B: " + " ".join(f"{v:>3}" for v in gb[i]))
            print()
    n = min(len(ga), len(gb))
    tot = diff = inv = same = 0
    for i in range(n):
        for j in range(min(len(ga[i]), len(gb[i]))):
            x, y = ga[i][j], gb[i][j]
            tot += 1
            if x == y:
                same += 1
            else:
                diff += 1
            if abs(x + y - 255) <= 3:
                inv += 1
    print(f"采样点总数 {tot}：完全相同 {same}，不同 {diff}，互为反相(和~255) {inv}")
    if inv / max(tot, 1) > 0.9:
        print("=> B 是 A 的反相（alpha 被取反了）")
    elif same / max(tot, 1) > 0.9:
        print("=> 两者一致")
    else:
        print("=> 既不一致也不是简单反相，需要看具体数值")
    return 0


if __name__ == "__main__":
    sys.exit(main())
