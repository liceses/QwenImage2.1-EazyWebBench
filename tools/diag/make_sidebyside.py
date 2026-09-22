#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把两张图（或多张）横向拼成一张对照图，用于交付"看得见"的证据。

用法：python tools/diag/make_sidebyside.py 输出.png 左图.png 右图.png [更多图...]
     可选 --label 只影响打印信息；--sep 分隔条宽度（像素，默认 16）
"""
import os
import struct
import sys
import zlib

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def read_rgba(path):
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
    out = bytearray(w * h * 4)
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
        prev = line
        for x in range(w):
            o = (y * w + x) * 4
            if ch == 4:
                out[o:o + 4] = line[x * 4:x * 4 + 4]
            elif ch == 3:
                out[o] = line[x * 3]
                out[o + 1] = line[x * 3 + 1]
                out[o + 2] = line[x * 3 + 2]
                out[o + 3] = 255
            elif ch == 2:
                out[o] = out[o + 1] = out[o + 2] = line[x * 2]
                out[o + 3] = line[x * 2 + 1]
            else:
                out[o] = out[o + 1] = out[o + 2] = line[x]
                out[o + 3] = 255
    return w, h, out


def write_rgba(path, w, h, rgba):
    stride = w * 4
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw.extend(rgba[y * stride:(y + 1) * stride])

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    png += chunk(b"IEND", b"")
    open(path, "wb").write(png)


def main():
    args = sys.argv[1:]
    sep = 16
    if "--sep" in args:
        i = args.index("--sep")
        sep = int(args[i + 1])
        del args[i:i + 2]
    if len(args) < 3:
        print(__doc__)
        return 1
    out_path, srcs = args[0], args[1:]
    imgs = []
    for p in srcs:
        w, h, rgba = read_rgba(p)
        imgs.append((w, h, rgba))
    W = sum(i[0] for i in imgs) + sep * (len(imgs) - 1)
    H = max(i[1] for i in imgs)
    canvas = bytearray(W * H * 4)
    # 分隔条用深灰，便于一眼区分
    for y in range(H):
        for x in range(W):
            o = (y * W + x) * 4
            canvas[o] = canvas[o + 1] = canvas[o + 2] = 0x20
            canvas[o + 3] = 255
    x0 = 0
    for (w, h, rgba) in imgs:
        for y in range(h):
            src = y * w * 4
            dst = (y * W + x0) * 4
            canvas[dst:dst + w * 4] = rgba[src:src + w * 4]
        x0 += w + sep
    write_rgba(out_path, W, H, canvas)
    print(f"已拼接 {len(imgs)} 张 -> {out_path}  ({W}x{H})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
