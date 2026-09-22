#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""确定 ComfyUI / KJNodes 里 mask ↔ alpha 的真实取值约定。

动机：接线透明通道时必须知道"mask 的 1 到底代表什么"。
背景矛盾：同一份 LoadImage 的 MASK（= 参考图 alpha，全透明那张 alpha≈0）
   · 经 JoinImageWithAlpha+SaveImageWithAlpha 写出 → alpha≈0（与参考图一致）
   · 经 MaskToImage+SaveImage 写出           → 灰度 254/255（等于"白"）
两者不可能同时对，必有一处在取反。用**非对称输入**（左半透明/右半不透明）一次判清。

用法：python tools/diag/diag_mask_alpha_convention.py
"""
import json
import os
import struct
import sys
import time
import urllib.request
import uuid
import zlib

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

COMFY = "http://127.0.0.1:8188"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
COMFY_OUT = os.environ.get("QWEN21_COMFY_ROOT",
                           r"D:\applications\comfy-ui\ComfyUI_windows_portable")
COMFY_OUT = os.path.join(COMFY_OUT, "ComfyUI", "output")
HERE = os.path.dirname(os.path.abspath(__file__))


def write_rgba(path, w, h, fn):
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        for x in range(w):
            raw.extend(fn(x, y))

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    open(path, "wb").write(png)


def read_png(path):
    """返回 (w,h,color_type, 左半区均值, 右半区均值) —— 取第 1、最后一列像素。"""
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
    left_vals, right_vals = [], []
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
        # 取 x=1（左，应透明）与 x=w-2（右，应不透明）的"通道值"
        left_vals.append(line[1 * ch + (ch - 1)])
        right_vals.append(line[(w - 2) * ch + (ch - 1)])
        prev = line
    return w, h, ct, round(sum(left_vals) / len(left_vals), 1), round(sum(right_vals) / len(right_vals), 1)


def upload(path, name):
    b = "----conv" + uuid.uuid4().hex
    body = (f"--{b}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{name}\"\r\n"
            "Content-Type: image/png\r\n\r\n").encode()
    body += open(path, "rb").read()
    body += f"\r\n--{b}\r\n".encode()
    body += (f"Content-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n--{b}--\r\n").encode()
    req = urllib.request.Request(COMFY + "/upload/image", data=body,
                                 headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    with OPENER.open(req, timeout=60) as r:
        return json.loads(r.read().decode())


def run(wf, label, limit=300):
    req = urllib.request.Request(COMFY + "/prompt",
                                 data=json.dumps({"prompt": wf, "client_id": str(uuid.uuid4())}).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        res = json.loads(OPENER.open(req, timeout=60).read().decode())
    except urllib.error.HTTPError as e:
        print(f"  [{label}] 提交被拒: {e.read().decode('utf-8', 'replace')[:300]}")
        return []
    pid = res.get("prompt_id")
    for _ in range(limit):
        time.sleep(1)
        h = json.loads(OPENER.open(f"{COMFY}/history/{pid}", timeout=30).read().decode())
        if pid in h:
            break
    e = h.get(pid, {})
    st = (e.get("status") or {})
    print(f"  [{label}] status={st.get('status_str')}")
    for m in st.get("messages") or []:
        if isinstance(m, list) and m[0] == "execution_error":
            d = m[1] or {}
            print(f"       ERR {d.get('node_type')}: {d.get('exception_type')} {d.get('exception_message')}")
    out = []
    for node, o in sorted((e.get("outputs") or {}).items()):
        for im in o.get("images") or []:
            p = os.path.join(COMFY_OUT, im.get("subfolder", ""), im["filename"])
            if os.path.exists(p):
                out.append((im["filename"], read_png(p)))
    return out


def main():
    src = os.path.join(HERE, "_convention_probe.png")
    # 左半：完全不透明(红,alpha=255)   右半：完全透明(alpha=0)
    write_rgba(src, 64, 64,
               lambda x, y: (255, 0, 0, 255) if x < 32 else (0, 0, 0, 0))
    print("探针图：左半 alpha=255（不透明红色），右半 alpha=0（透明）")
    name = upload(src, "dsh_convention_probe.png")["name"]
    print("已上传:", name)

    print("\n=== 基线：原图直接存盘（对照组）===")
    for f, v in run({"1": {"class_type": "LoadImage", "inputs": {"image": name}},
                     "2": {"class_type": "SaveImage",
                           "inputs": {"images": ["1", 0], "filename_prefix": "conv_base"}}},
                    "LoadImage->SaveImage"):
        print(f"    {f}  (w,h,color_type,左值,右值) = {v}")

    print("\n=== 问题 1：MaskToImage 把 mask 画成什么？===")
    print("    （左列应为 '透明区域'，右列应为 '不透明区域'）")
    for f, v in run({"1": {"class_type": "LoadImage", "inputs": {"image": name}},
                     "2": {"class_type": "MaskToImage", "inputs": {"mask": ["1", 1]}},
                     "3": {"class_type": "SaveImage",
                           "inputs": {"images": ["2", 0], "filename_prefix": "conv_masktoimage"}}},
                    "LoadImage.MASK->MaskToImage"):
        print(f"    {f}  = {v}")

    print("\n=== 问题 2：SaveImageWithAlpha 写出的 alpha 用的是 mask 本身还是它的反？===")
    for f, v in run({"1": {"class_type": "LoadImage", "inputs": {"image": name}},
                     "2": {"class_type": "SaveImageWithAlpha",
                           "inputs": {"images": ["1", 0], "mask": ["1", 1],
                                      "filename_prefix": "conv_siawa"}}},
                    "SaveImageWithAlpha"):
        print(f"    {f}  = {v}   (color_type=6 时 左值=alpha@透明区, 右值=alpha@不透明区)")

    print("\n判定标准：探针图左侧是透明区(a=0)、右侧是不透明区(a=255)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
